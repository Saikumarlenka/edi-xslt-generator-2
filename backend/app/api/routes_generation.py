"""
Generation routes – two-phase workflow.

Phase 1 (/extract-matrix):  Upload the mapping-matrix DOCX → Gemini extracts
    structured rows → return them for editable preview.
Phase 2 (/generate-xslt):  Accept the (possibly user-edited) mapping JSON →
    run analysis, patch, and validation pipeline.
"""

import json, threading, traceback, logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Form, Query, HTTPException
from app.core.config import DATA_ROOT
from app.services.file_service import save_upload
from app.services.gemini_matrix_reader import GeminiMatrixReaderService
from app.services.python_matrix_reader import PythonMatrixReaderService
from app.services.python_xslt_proposal_service import PythonXsltProposalService
from app.services.xslt_analysis_service import XsltAnalysisService
from app.services.schema_analysis_service import SchemaAnalysisService
from app.services.canonical_path_resolver import CanonicalPathResolver
from app.services.xslt_patch_service import XsltPatchService
from app.services.validation_service import XsltValidationService
from app.services.job_store import new_job, get_job, update
from app.services.report_service import build_report
from app.services.prompt_manager import ANALYSIS_SYSTEM, PATCH_SYSTEM
from app.core.config import settings
from google import genai
from google.genai import types

log = logging.getLogger(__name__)
router = APIRouter()


# ── helpers ──────────────────────────────────────────────────────────────────

def reference_paths(tx):
    d = DATA_ROOT / "references" / tx
    return {
        "matrix": d / "matrix",
        "standard_xslt": d / "standard_xslt",
        "canonical_xsd": d / "canonical_xsd",
        "edi_xsd": d / "edi_xsd",
        "canonical_xml": d / "canonical_xml",
    }


def require_refs(tx):
    paths = reference_paths(tx)
    missing = [
        k for k, v in paths.items()
        if k != "matrix" and not v.exists()
    ]
    if not paths["standard_xslt"].exists():
        missing.append("standard_xslt")
    if missing:
        raise HTTPException(
            400,
            "Missing required reference files: " + ", ".join(sorted(set(missing))),
        )
    return paths


# ── Phase 1: Extract matrix ─────────────────────────────────────────────────

@router.post("/extract-matrix-python")
async def extract_matrix_python(
    transaction: str = Form(...),
    matrix: UploadFile = File(...),
):
    """Explicit endpoint for deterministic Python matrix extraction."""
    return await extract_matrix(transaction=transaction, matrix=matrix, method="python")


@router.post("/extract-matrix-gemini")
async def extract_matrix_gemini(
    transaction: str = Form(...),
    matrix: UploadFile = File(...),
):
    """Explicit endpoint for Gemini AI matrix extraction."""
    return await extract_matrix(transaction=transaction, matrix=matrix, method="gemini")


@router.post("/extract-matrix")
async def extract_matrix(
    transaction: str = Form(...),
    matrix: UploadFile = File(...),
    method: str | None = Form(None),
    m: str | None = Query(None, alias="method"),
):
    """Upload a mapping-matrix DOCX and extract rows with Python or Gemini.

    Defaults to deterministic Python parser. Returns the structured mapping
    immediately (or via polling) so the user can preview and edit.
    """
    if transaction not in ("210", "214"):
        raise HTTPException(400, "transaction must be 210 or 214")

    raw = method or m or "python"
    clean_method = str(raw).lower().strip()
    if clean_method not in ("python", "gemini"):
        clean_method = "python"

    job = new_job(transaction, clean_method)
    folder = Path(job["folder"])

    try:
        matrix_path = await save_upload(matrix, folder / "input", "matrix")
    except Exception:
        raise

    job["artifacts"]["matrix"] = str(matrix_path)
    job["status"] = "running"
    job["stage"] = "matrix_interpretation"
    job["extraction_method"] = clean_method
    job["message"] = (
        "Deterministic Python matrix parser is extracting mapping rows"
        if clean_method == "python"
        else "Gemini is interpreting the matrix document"
    )
    update(job)

    # Run extraction in background thread
    thread = threading.Thread(
        target=_run_extraction,
        args=(job["job_id"], matrix_path, clean_method),
        daemon=True,
    )
    thread.start()

    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "stage": job["stage"],
        "extraction_method": clean_method,
        "message": f"Matrix extraction started ({clean_method} method)",
    }


def _run_extraction(job_id, matrix_path, method="python"):
    """Background: extract mapping rows from the DOCX via Python parser or Gemini."""
    job = get_job(job_id)
    try:
        if method == "gemini":
            spec = GeminiMatrixReaderService().read_matrix(matrix_path, job["transaction"])
        else:
            spec = PythonMatrixReaderService().read_matrix(matrix_path, job["transaction"])

        job["mapping"] = spec.model_dump()
        folder = Path(job["folder"])
        (folder / "mapping.json").write_text(
            json.dumps(job["mapping"], indent=2), encoding="utf-8",
        )
        job["mapping_count"] = len(spec.mappings)
        job["status"] = "extracted"
        job["stage"] = "extracted"
        job["extraction_method"] = method
        job["message"] = (
            f"Extracted {len(spec.mappings)} mapping rows via {method.capitalize()} parser. "
            "Review and edit before generating XSLT."
        )
        update(job)
    except Exception as exc:
        job["status"] = "failed"
        job["stage"] = "failed"
        job["message"] = str(exc)
        job["errors"].append(str(exc))
        update(job)
        log.error("Matrix extraction failed (%s): %s", method, traceback.format_exc())


# ── Phase 2: Generate XSLT from mapping ─────────────────────────────────────

@router.post("/generate-xslt/{job_id}")
async def generate_xslt(job_id: str):
    """Take the current mapping (possibly edited) and run the full pipeline."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if not job.get("mapping"):
        raise HTTPException(409, "No mapping data available. Extract the matrix first.")
    if job["status"] == "running":
        raise HTTPException(409, "Job is already running")

    tx = job["transaction"]
    paths = require_refs(tx)

    job["status"] = "running"
    job["stage"] = "reference_analysis"
    job["message"] = "Starting XSLT generation pipeline"
    job["errors"] = []
    job["warnings"] = []
    update(job)

    thread = threading.Thread(
        target=_run_generation,
        args=(job_id, paths),
        daemon=True,
    )
    thread.start()

    return {
        "job_id": job_id,
        "status": job["status"],
        "stage": job["stage"],
        "message": "XSLT generation started",
    }


def _run_generation(job_id, paths):
    """Background: analyze, patch, validate."""
    job = get_job(job_id)
    folder = Path(job["folder"])
    try:
        # ── Reference analysis ───────────────────────────────────────────
        job["stage"] = "reference_analysis"
        job["message"] = "Analyzing baseline XSLT and schemas"
        update(job)

        xslt_info = XsltAnalysisService().analyze(paths["standard_xslt"])
        canonical_info = SchemaAnalysisService().analyze(paths["canonical_xsd"])
        edi_info = SchemaAnalysisService().analyze(paths["edi_xsd"])
        job["analysis"] = {
            "xslt": xslt_info,
            "canonical_schema": canonical_info,
            "edi_schema": edi_info,
        }
        update(job)

        # ── Mapping analysis (Gemini or Deterministic Python) ────────────
        job["stage"] = "mapping_analysis"
        method = job.get("mapping", {}).get("extraction_method", "python")
        job["message"] = (
            f"Analyzing mappings and preparing conservative patches ({method} model)"
        )
        update(job)

        proposals = []
        if method == "gemini" and settings.gemini_api_key:
            try:
                log.info("Attempting Gemini mapping analysis for proposals...")
                client = genai.Client(api_key=settings.gemini_api_key)
                context = {
                    "transaction": job["transaction"],
                    "mappings": job["mapping"]["mappings"],
                    "baseline_xslt_summary": {
                        "version": xslt_info["version"],
                        "namespaces": xslt_info["namespaces"],
                        "templates": xslt_info["templates"],
                        "helper_templates": xslt_info.get("helper_templates", []),
                        "extension_calls": xslt_info.get("extension_calls", []),
                        "null_guard_audit": xslt_info.get("null_guard_audit", {}),
                        "segment_order": xslt_info.get("segment_order", []),
                        "expressions": xslt_info["expressions"][:500],
                    },
                    "canonical_schema_summary": canonical_info,
                    "edi_schema_summary": edi_info,
                }

                response = client.models.generate_content(
                    model=settings.gemini_model,
                    contents=[
                        ANALYSIS_SYSTEM,
                        "Analyze this JSON evidence. Return JSON array only.\n"
                        + json.dumps(context),
                    ],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1,
                        max_output_tokens=12000,
                    ),
                )
                raw_proposals = json.loads(
                    (response.text or "[]")
                    .strip()
                    .removeprefix("```json")
                    .removesuffix("```")
                    .strip()
                )
                if isinstance(raw_proposals, list):
                    proposals = raw_proposals
                else:
                    log.warning("Gemini mapping analysis did not return a list; using Python generator")
            except Exception as exc:
                log.warning(
                    "Gemini proposal generation failed (%s); falling back to Python proposal generator",
                    exc,
                )
                job["warnings"].append(
                    f"Gemini proposal analysis encountered an issue ({exc}); used deterministic Python rule engine."
                )

        if not proposals:
            # Deterministic Python proposal generator
            log.info("Using deterministic Python proposal generator...")
            proposals = PythonXsltProposalService().generate_proposals(
                paths["standard_xslt"],
                job["mapping"]["mappings"],
                job["transaction"],
            )

        job["proposals"] = proposals
        (folder / "proposals.json").write_text(
            json.dumps(proposals, indent=2), encoding="utf-8",
        )
        update(job)

        # ── Patch ────────────────────────────────────────────────────────
        job["stage"] = "patch_review"
        job["message"] = "Creating conservative baseline-preserving XSLT artifact"
        update(job)

        out = folder / f"generated_{job['transaction']}.xslt"
        patch_result = XsltPatchService().apply_proposals(
            paths["standard_xslt"], proposals, out,
        )
        job["artifacts"]["xslt"] = str(out)
        job["patch_result"] = patch_result

        # ── Validation ───────────────────────────────────────────────────
        job["stage"] = "validation"
        job["message"] = "Validating generated XSLT, schema, sequence, and X12 structure"
        update(job)

        validation = XsltValidationService().validate(
            out,
            paths["canonical_xml"],
            paths["edi_xsd"],
            paths["canonical_xsd"],
            paths["standard_xslt"],
            job["transaction"],
        )
        job["validation"] = validation

        # ── Status update on each mapping ────────────────────────────────
        applied_ids = {p.get("mapping_id") for p in patch_result.get("applied", [])}
        reused_ids = {p.get("mapping_id") for p in patch_result.get("reused", [])}
        unresolved_ids = {p.get("mapping_id") for p in patch_result.get("unresolved", [])}

        for m in job["mapping"]["mappings"]:
            notes = m.get("related_notes")
            if not isinstance(notes, list):
                m["related_notes"] = notes = []

            mid = m.get("mapping_id")
            if mid in reused_ids and validation.get("passed"):
                m["implementation_status"] = "implemented_with_warnings"
                notes.append(
                    "Gemini identified a baseline target for reuse. "
                    "Confirm semantic equivalence to the matrix and inspect the test output."
                )
            elif mid in applied_ids and validation.get("passed"):
                m["implementation_status"] = "implemented_with_warnings"
                notes.append(
                    "A constrained XPath/test replacement was applied; "
                    "review all validation results before use."
                )
            elif m.get("ambiguities"):
                m["implementation_status"] = "requires_user_clarification"
            else:
                m["implementation_status"] = "unresolved"
                if mid in unresolved_ids:
                    notes.append(
                        "Patch not applied: see patch_result.unresolved for the reason."
                    )

        if patch_result.get("applied_count", 0) == 0:
            job["warnings"].append(
                "No safe XSLT changes were applied. The output may be "
                "the unchanged baseline; unresolved matrix rows are not "
                "considered implemented."
            )
        if not validation.get("passed"):
            job["warnings"].append(
                "One or more validation checks failed. Do not use this "
                "output in production until corrected."
            )

        has_issues = (
            job["warnings"]
            or not validation.get("passed")
            or any(
                m.get("implementation_status") in {"unresolved", "requires_user_clarification"}
                for m in job["mapping"]["mappings"]
            )
        )
        job["status"] = "completed_with_warnings" if has_issues else "completed"
        job["stage"] = "completed"
        job["message"] = (
            "Analysis finished. Review patch coverage, X12 checks, "
            "null-guard audit, and unresolved rows."
        )
        update(job)

    except Exception as exc:
        job["status"] = "failed"
        job["stage"] = "failed"
        job["message"] = str(exc)
        job["errors"].append(str(exc))
        update(job)
        log.error("XSLT generation failed: %s", traceback.format_exc())


# ── Legacy combined endpoint (kept for backwards compat) ─────────────────────

@router.post("/generate")
async def generate(transaction: str = Form(...), matrix: UploadFile = File(...)):
    """Legacy one-shot endpoint. Redirects to the two-phase workflow internally."""
    if transaction not in ("210", "214"):
        raise HTTPException(400, "transaction must be 210 or 214")
    paths = require_refs(transaction)
    job = new_job(transaction)
    folder = Path(job["folder"])
    try:
        matrix_path = await save_upload(matrix, folder / "input", "matrix")
    except Exception:
        raise
    job["artifacts"]["matrix"] = str(matrix_path)
    job["status"] = "running"
    job["stage"] = "matrix_interpretation"
    job["message"] = "Submitted to background worker"
    update(job)

    def _legacy_run():
        _run_extraction(job["job_id"], matrix_path)
        j = get_job(job["job_id"])
        if j and j["status"] == "extracted":
            _run_generation(job["job_id"], paths)

    thread = threading.Thread(target=_legacy_run, daemon=True)
    thread.start()
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "stage": job["stage"],
        "message": "Generation started",
    }


# ── Job query endpoints ─────────────────────────────────────────────────────

@router.get("/jobs/{job_id}")
def job_status(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return {
        k: job.get(k)
        for k in [
            "job_id", "transaction", "status", "stage", "message",
            "errors", "warnings", "mapping_count", "created_at",
        ]
    }


@router.get("/jobs/{job_id}/mapping")
def job_mapping(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if not job.get("mapping"):
        raise HTTPException(409, "Mapping specification is not ready")
    return job["mapping"]


@router.put("/jobs/{job_id}/mapping")
async def update_mapping(job_id: str, body: dict):
    """Save user-edited mapping data back to the job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if job.get("status") == "running":
        raise HTTPException(409, "Cannot update mapping while job is running")

    mappings = body.get("mappings")
    if not isinstance(mappings, list):
        raise HTTPException(400, "Request body must contain a 'mappings' array")

    job["mapping"]["mappings"] = mappings
    job["mapping_count"] = len(mappings)

    # Sync review points status
    if "review_points" in job["mapping"] and isinstance(job["mapping"]["review_points"], list):
        mapping_by_id = {m.get("mapping_id"): m for m in mappings if isinstance(m, dict)}
        for rp in job["mapping"]["review_points"]:
            mid = rp.get("mapping_id")
            if mid in mapping_by_id:
                m = mapping_by_id[mid]
                cur_path = m.get("source_canonical_path", "")
                sug_path = rp.get("suggested_canonical_path", "")
                mat_text = rp.get("source_document_reference", "")
                if cur_path == sug_path:
                    rp["status"] = "applied"
                elif cur_path == mat_text:
                    rp["status"] = "reverted"
                else:
                    rp["status"] = "customized"
                rp["source_canonical_path"] = cur_path

    folder = Path(job["folder"])
    (folder / "mapping.json").write_text(
        json.dumps(job["mapping"], indent=2), encoding="utf-8",
    )
    update(job)

    return {
        "updated": len(mappings),
        "message": "Mapping data saved successfully",
    }


@router.post("/jobs/{job_id}/resolve")
def resolve_mapping(job_id: str, body: dict):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    if not job.get("mapping"):
        raise HTTPException(409, "Mapping specification is not ready")
    clarifications = body.get("clarifications", {})
    for m in job["mapping"]["mappings"]:
        if m["mapping_id"] in clarifications:
            notes = m.get("related_notes")
            if not isinstance(notes, list):
                m["related_notes"] = notes = []
            notes.append("User clarification: " + str(clarifications[m["mapping_id"]]))
            m["ambiguities"] = []
            m["implementation_status"] = "unresolved"
    update(job)
    return {"updated": len(clarifications)}


@router.get("/jobs/{job_id}/xslt")
def job_xslt(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    path = job.get("artifacts", {}).get("xslt")
    if not path or not Path(path).exists():
        raise HTTPException(409, "Generated XSLT is not ready")
    return {"content": Path(path).read_text(encoding="utf-8"), "filename": Path(path).name}


@router.post("/jobs/{job_id}/validate")
def rerun_validation(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    xslt = job.get("artifacts", {}).get("xslt")
    if not xslt:
        raise HTTPException(409, "Generated XSLT is not ready")
    paths = reference_paths(job["transaction"])
    job["validation"] = XsltValidationService().validate(
        Path(xslt),
        paths["canonical_xml"] if paths["canonical_xml"].exists() else None,
        paths["edi_xsd"] if paths["edi_xsd"].exists() else None,
        paths["canonical_xsd"] if paths["canonical_xsd"].exists() else None,
        paths["standard_xslt"] if paths["standard_xslt"].exists() else None,
        job["transaction"],
    )
    update(job)
    return job["validation"]


@router.get("/jobs/{job_id}/report")
def job_report(job_id: str):
    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    return build_report(job)


@router.get("/jobs/{job_id}/download")
def job_download(job_id: str):
    from fastapi.responses import FileResponse
    import zipfile

    job = get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    folder = Path(job["folder"])
    bundle = folder / "artifacts.zip"
    with zipfile.ZipFile(bundle, "w", zipfile.ZIP_DEFLATED) as z:
        for key in ["xslt", "matrix"]:
            p = job.get("artifacts", {}).get(key)
            if p and Path(p).exists():
                z.write(p, Path(p).name)
        for name in ["mapping.json", "proposals.json"]:
            p = folder / name
            if p.exists():
                z.write(p, name)
        report = folder / "validation_report.json"
        report.write_text(
            json.dumps(build_report(job), indent=2), encoding="utf-8",
        )
        z.write(report, report.name)
    return FileResponse(
        bundle,
        filename=f"edi_{job['transaction']}_job_{job_id[:8]}.zip",
        media_type="application/zip",
    )
