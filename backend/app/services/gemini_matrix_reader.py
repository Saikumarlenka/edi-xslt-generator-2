
import json
import logging
import re
import time
from pathlib import Path

from google import genai
from google.genai import types

from app.core.config import settings
from app.models.mapping import MappingSpecification
from app.services.prompt_manager import MATRIX_SYSTEM, MATRIX_PROMPT_VERSION

log = logging.getLogger(__name__)

DOCX_MIME_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


def _extract_json(raw: str) -> dict:
    """
    Robustly extract a JSON object from a model response that may contain
    surrounding prose, markdown fences, or partial wrapping text.
    Tries three strategies in order:
      1. Strip markdown fences and parse directly.
      2. Regex-scan for the outermost {...} block.
      3. Raise JSONDecodeError so the caller can retry.
    """
    # Strategy 1: strip common fences and try direct parse
    cleaned = (
        raw.removeprefix("```json")
           .removeprefix("```")
           .removesuffix("```")
           .strip()
    )
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Strategy 2: find the outermost { ... } block
    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    # Strategy 3: fail — let caller retry
    raise json.JSONDecodeError("No valid JSON object found in response", raw, 0)


class GeminiMatrixReaderService:
    def __init__(self):
        self.client = (
            genai.Client(api_key=settings.gemini_api_key)
            if settings.gemini_api_key
            else None
        )

    def read_matrix(
        self, docx_path: Path, transaction: str
    ) -> MappingSpecification:
        if not self.client:
            raise RuntimeError(
                "GEMINI_API_KEY is not configured. "
                "Add it to backend/.env and restart the backend."
            )

        uploaded = None

        try:
            log.info("Uploading matrix document to Gemini Files API...")
            t0 = time.time()
            uploaded = self.client.files.upload(
                file=str(docx_path),
                config={
                    "mime_type": DOCX_MIME_TYPE,
                    "display_name": f"{transaction}_mapping_matrix",
                },
            )
            log.info("Upload complete in %.1fs. Starting extraction...", time.time() - t0)

            prompt = (
                f"{MATRIX_SYSTEM}\n"
                f"Prompt version: {MATRIX_PROMPT_VERSION}. "
                f"Transaction is EDI {transaction}. "
                "Read the uploaded DOCX mapping matrix as the "
                "authoritative source for mapping requirements. "
                "Interpret the mapping rows, table headings, source "
                "and destination fields, conditions, constants, "
                "qualifiers, notes, and exceptions. "
                "Do not invent missing mappings. "
                "Return a single JSON object only — no prose, no markdown fences."
            )

            data = self._generate_with_retry_and_parse(prompt, uploaded, transaction)
            data["transaction"] = transaction
            data["extraction_method"] = "gemini"

            spec = MappingSpecification.model_validate(data)

            if not spec.mappings:
                raise ValueError(
                    "Gemini returned no mapping rows. "
                    "Check the document and retry."
                )

            # Post-process and enrich Gemini mappings with consistent segment, constant, and crossed-out metadata
            self._enrich_spec(spec)

            log.info(
                "Matrix extraction complete: %d mappings extracted (Gemini).",
                len(spec.mappings),
            )
            return spec

        finally:
            if uploaded is not None:
                try:
                    self.client.files.delete(name=uploaded.name)
                except Exception:
                    log.warning(
                        "Could not delete temporary Gemini file; "
                        "inspect Gemini Files storage."
                    )

    def _enrich_spec(self, spec: MappingSpecification):
        """Ensure consistent segment, condition, path, constant, and crossed-out metadata."""
        for m in spec.mappings:
            m.extraction_method = "gemini"
            # 1. Derive destination segment if unknown or missing
            dest_elem = (m.destination_element or "").strip().upper()
            if (not m.destination_segment or m.destination_segment == "unknown") and dest_elem:
                elem_match = re.match(r"^([A-Z][A-Z0-9]{1,3}?)(\d{2})$", dest_elem)
                if elem_match:
                    m.destination_segment = elem_match.group(1)

            rule_text = (m.mapping_rule or "").lower()
            path_text = (m.source_canonical_path or "").lower()

            # 2. Canonical path resolution for CommodityCode and TariffReference
            if dest_elem == "L707" or "commoditycode" in path_text or "commoditycode" in rule_text:
                if "qualifier" in path_text or "qualifier" in rule_text or dest_elem == "L702":
                    m.source_canonical_path = "Detail/LineItem/DescriptionMarksAndNumbers/@CommodityCodeQualifier2"
                else:
                    m.source_canonical_path = "Detail/LineItem/DescriptionMarksAndNumbers/@CommodityCode2"
                m.destination_segment = "L7"
                m.parent_segment = "L7"
                m.parent_path = "Detail/LineItem/DescriptionMarksAndNumbers"
                m.parent_condition = "If commoditycode2 != NULL (on any line item lines)"
                if not m.conditions:
                    m.conditions = ["If commoditycode2 != NULL (on any line item lines)"]

            elif dest_elem == "L701":
                m.source_canonical_path = "position()"
                m.destination_segment = "L7"
                m.parent_segment = "L7"
                m.parent_path = "Detail/LineItem/DescriptionMarksAndNumbers"
                m.parent_condition = "If commoditycode2 != NULL (on any line item lines)"

            elif "tariffdistance" in path_text or "tariffdistance" in rule_text or ("tariff" in rule_text and "distance" in rule_text):
                if "qualifier" in path_text or "qualifier" in rule_text:
                    m.source_canonical_path = "Detail/LineItem/TariffReference/@DistanceQualifier"
                else:
                    m.source_canonical_path = "Detail/LineItem/TariffReference/@TariffDistance"
                m.parent_path = "Detail/LineItem/TariffReference"

            elif "distancequalifier" in path_text or "distancequalifier" in rule_text:
                m.source_canonical_path = "Detail/LineItem/TariffReference/@DistanceQualifier"
                m.parent_path = "Detail/LineItem/TariffReference"

            elif dest_elem == "L108":
                m.destination_segment = "L1"
                m.parent_segment = "LXLoop1"
                m.parent_path = "Detail/LineItem/RateAndCharges"
                m.source_canonical_path = "Detail/LineItem/RateAndCharges/@SpecialChargeOrAllowanceCode"
                m.is_crossed = False

            # Prefix relative paths under LineItem if not already prefixed
            if m.source_canonical_path and not m.source_canonical_path.startswith(("Header/", "Detail/", "Summary/", "Invoice/", "position()")):
                if m.source_canonical_path.startswith(("DescriptionMarksAndNumbers/", "LineItemQuantityAndWeight/", "RateAndCharges/", "TariffReference/")):
                    m.source_canonical_path = f"Detail/LineItem/{m.source_canonical_path}"
                elif m.source_canonical_path.startswith(("BeginningSegmentForCarriersInvoice/", "Currency/", "TransactionSetheader/", "PartyList/", "EquipmentList/")):
                    m.source_canonical_path = f"Header/{m.source_canonical_path}"
                elif m.source_canonical_path.startswith("TotalWeightAndCharges/"):
                    m.source_canonical_path = f"Summary/{m.source_canonical_path}"

            # 3. Check for crossed out / commented out
            # Never mark as crossed out if it's L108 or an IF/THEN condition rule
            rule_has_if_then = bool(re.search(r"\bif\b.*\bthen\b", m.mapping_rule or "", re.I))
            is_l108 = dest_elem == "L108"

            if not is_l108 and not rule_has_if_then:
                notes_text = " ".join([m.default_behavior or ""] + (m.related_notes or [])).lower()
                if any(term in notes_text for term in ("commented out by default", "commented out", "not mapped by default", "strikethrough", "crossed out")):
                    m.is_crossed = True
                    m.implementation_status = "excluded_crossed_out"
            else:
                m.is_crossed = False
                if m.implementation_status == "excluded_crossed_out":
                    m.implementation_status = "unresolved"

            # 4. Check for constant / static value
            # Rule: "if there is no path means it is a constant"
            has_no_path = not m.source_canonical_path or m.source_canonical_path in ("unknown", "none", "not_specified", "")
            notes_for_const = " ".join([m.mapping_rule or "", m.default_behavior or ""] + (m.related_notes or [])).lower()
            is_explicit_constant = any(term in notes_for_const for term in ("hardcoded", "literal", "fixed value")) or bool(m.constants)

            if (has_no_path or is_explicit_constant) and not m.is_crossed and not rule_has_if_then:
                m.is_constant = True
                if not m.constants:
                    quoted = re.findall(r"[\"']([A-Za-z0-9_-]+)[\"']", m.mapping_rule or "")
                    if quoted:
                        m.constants = quoted
                    elif m.source_canonical_path and m.source_canonical_path not in ("unknown", "none"):
                        m.constants = [m.source_canonical_path]
                if m.implementation_status in ("unresolved", "not_specified"):
                    m.implementation_status = "constant_value"
                if has_no_path:
                    m.source_canonical_path = ""

    def _generate_with_retry_and_parse(self, prompt, uploaded, transaction) -> dict:
        """
        Call Gemini with retry logic that handles BOTH API errors (rate limits,
        503s) AND JSON parse failures from malformed model output.
        """
        last_exc = None
        backoff_delays = [5, 10, 20, 40, 80]
        max_attempts = len(backoff_delays) + 1  # 6 total attempts

        for attempt in range(max_attempts):
            t_attempt = time.time()
            try:
                log.info(
                    "Gemini generation attempt %d/%d (model=%s)...",
                    attempt + 1, max_attempts, settings.gemini_model,
                )
                response = self.client.models.generate_content(
                    model=settings.gemini_model,
                    contents=[
                        types.Part.from_uri(
                            file_uri=uploaded.uri,
                            mime_type=DOCX_MIME_TYPE,
                        ),
                        prompt,
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                        max_output_tokens=32000,
                    ),
                )
                elapsed = time.time() - t_attempt
                raw = (response.text or "").strip()
                log.info(
                    "Attempt %d response received in %.1fs (%d chars).",
                    attempt + 1, elapsed, len(raw),
                )

                # Try to parse — if this raises, we retry
                data = _extract_json(raw)
                return data

            except json.JSONDecodeError as exc:
                last_exc = exc
                if attempt == max_attempts - 1:
                    break
                delay = backoff_delays[attempt]
                log.warning(
                    "Attempt %d/%d: Gemini returned non-JSON output. "
                    "Retrying in %ds... (preview: %.120s)",
                    attempt + 1, max_attempts, delay,
                    (response.text or "")[:120] if "response" in dir() else "",
                )
                time.sleep(delay)

            except Exception as exc:
                last_exc = exc
                msg = str(exc).lower()

                retryable = any(
                    term in msg
                    for term in [
                        "429", "rate", "quota", "503",
                        "timeout", "temporar", "unavailable", "overloaded",
                    ]
                )

                elapsed = time.time() - t_attempt
                log.warning(
                    "Attempt %d/%d failed after %.1fs: %s",
                    attempt + 1, max_attempts, elapsed, str(exc)[:200],
                )

                if not retryable or attempt == max_attempts - 1:
                    break

                delay = backoff_delays[attempt]
                log.info("Retrying in %ds...", delay)
                time.sleep(delay)

        # All attempts exhausted — raise an informative error
        msg = str(last_exc or "unknown Gemini error")

        if isinstance(last_exc, json.JSONDecodeError):
            raise RuntimeError(
                "Gemini did not return valid JSON after all retry attempts. "
                "The document may be too large or complex. "
                "Try splitting the matrix into smaller sections."
            ) from last_exc

        if any(term in msg.lower() for term in ["429", "quota", "rate"]):
            raise RuntimeError(
                "Gemini quota/rate limit reached. Wait for quota reset "
                "or check your Google AI Studio limits; completed job "
                "stages are retained."
            ) from last_exc

        if any(term in msg.lower() for term in ["503", "unavailable", "overloaded"]):
            raise RuntimeError(
                "Gemini model is temporarily overloaded (503). "
                "All retry attempts exhausted. "
                "Please wait a few minutes and try again."
            ) from last_exc

        raise RuntimeError(
            f"Gemini matrix interpretation failed: {msg[:500]}"
        ) from last_exc
