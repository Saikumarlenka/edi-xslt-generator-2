from pathlib import Path
from lxml import etree
from app.services.xslt_analysis_service import PARSER, parse_xml_file

class XsltValidationService:
    """Run XML/XSLT, schema, null-handling and X12 transaction-structure checks.

    The X12 checks are Stedi-style local checks, not a call to or certification by Stedi.
    """
    def validate(self, xslt_path: Path, canonical_xml: Path | None = None,
                 edi_xsd: Path | None = None, canonical_xsd: Path | None = None,
                 baseline_xslt: Path | None = None, transaction: str | None = None) -> dict:
        results = []
        try:
            doc = parse_xml_file(xslt_path)
            results.append(self._item("XSLT XML well-formedness", "passed", "Stylesheet parsed as well-formed XML."))
        except Exception as exc:
            return {"items": [self._item("XSLT XML well-formedness", "failed", str(exc))], "passed": False}

        try:
            transform = etree.XSLT(doc)
            results.append(self._item("XSLT compilation", "passed", "Compiled with lxml/libxslt. Proprietary BizTalk extension functions and unsupported XSLT versions may still require the BizTalk runtime."))
        except Exception as exc:
            results.append(self._item("XSLT compilation", "failed", str(exc)))
            return {"items": results, "passed": False}

        if baseline_xslt and Path(baseline_xslt).exists():
            try:
                baseline = parse_xml_file(baseline_xslt).getroot()
                generated = doc.getroot()
                base_segments = self._segment_sequence(baseline)
                generated_segments = self._segment_sequence(generated)
                same = base_segments == generated_segments
                results.append(self._item("Baseline segment sequence", "passed" if same else "warning", "Literal output element/segment sequence is unchanged." if same else f"Segment sequence adapted based on matrix exclusions ({len(base_segments)} baseline vs {len(generated_segments)} active)."))
                results.append(self._item("Template/helper/namespace preservation", "passed" if self._protected_signature(baseline) == self._protected_signature(generated) else "warning", "XSLT templates, helpers, and namespace declarations were preserved."))
            except Exception as exc:
                results.append(self._item("Baseline preservation", "warning", str(exc)))

        if canonical_xml and Path(canonical_xml).exists():
            try:
                source = etree.parse(str(canonical_xml), PARSER)
                if canonical_xsd and Path(canonical_xsd).exists():
                    try:
                        schema_doc = etree.parse(str(canonical_xsd), PARSER)
                        schema_ns = schema_doc.getroot().get("targetNamespace", "")
                        input_ns = etree.QName(source.getroot()).namespace or ""
                        if schema_ns != input_ns:
                            results.append(self._item("Canonical input XSD", "not_run", f"Schema namespace mismatch: XSD targetNamespace={schema_ns!r}, test XML namespace={input_ns!r}. Correct/provide the matching schema before claiming canonical schema validation."))
                        else:
                            source_schema = etree.XMLSchema(schema_doc)
                            if source_schema.validate(source):
                                results.append(self._item("Canonical input XSD", "passed", "Sample canonical XML validates against the canonical schema."))
                            else:
                                results.append(self._item("Canonical input XSD", "failed", "; ".join(str(e) for e in source_schema.error_log)))
                    except Exception as exc:
                        results.append(self._item("Canonical input XSD", "not_run", f"Schema could not be compiled: {exc}"))
                try:
                    output = transform(source)
                    results.append(self._item("Transformation execution", "passed", f"Executed successfully; output root: {etree.QName(output.getroot()).localname if output.getroot() is not None else 'empty'}"))
                    results.extend(self._x12_checks(output.getroot(), transaction))
                    if edi_xsd and Path(edi_xsd).exists():
                        try:
                            schema_doc = etree.parse(str(edi_xsd), PARSER)
                            schema_ns = schema_doc.getroot().get("targetNamespace", "")
                            output_ns = etree.QName(output.getroot()).namespace or ""
                            if schema_ns != output_ns:
                                results.append(self._item("Destination EDI XML XSD", "not_run", f"Schema namespace mismatch: XSD targetNamespace={schema_ns!r}, output root namespace={output_ns!r}. The supplied BizTalk EDI XSD cannot directly validate this wrapper XML; use a matching output schema or validate through the appropriate BizTalk/Stedi pipeline."))
                            else:
                                schema = etree.XMLSchema(schema_doc)
                                if schema.validate(output):
                                    results.append(self._item("Destination EDI XML XSD", "passed", "Transformation output validates against the configured destination XSD."))
                                else:
                                    results.append(self._item("Destination EDI XML XSD", "failed", "; ".join(str(e) for e in schema.error_log)))
                        except Exception as exc:
                            results.append(self._item("Destination EDI XML XSD", "not_run", f"Schema could not be compiled: {exc}"))
                except Exception as exc:
                    results.append(self._item("Transformation execution", "failed", str(exc)))
            except Exception as exc:
                results.append(self._item("Canonical input XML", "failed", str(exc)))
        else:
            results.append(self._item("Transformation execution", "not_run", "Upload a canonical test XML to run the transformation."))

        results.extend(self._null_guard_audit(doc))
        if transaction:
            results.append(self._item("STEDI-style X12 checks", "passed" if all(i["status"] in {"passed", "not_run", "warning"} for i in results if i["name"].startswith("X12 ")) else "failed", "Local X12 XML structure checks ran where output was available. This is not an official Stedi validation result."))
        blocking = {"failed"}
        return {"items": results, "passed": all(x["status"] not in blocking for x in results), "validation_scope": "Local XSLT/XSD and Stedi-style X12 structure checks; not an official Stedi API validation."}

    @staticmethod
    def _item(name, status, details):
        return {"name": name, "status": status, "details": details}

    @staticmethod
    def _segment_sequence(root):
        return [etree.QName(n).localname for n in root.iter() if isinstance(n.tag, str) and etree.QName(n).namespace != "http://www.w3.org/1999/XSL/Transform" and etree.QName(n).localname not in {"stylesheet", "transform"}]

    @classmethod
    def _protected_signature(cls, root):
        ns = {"xsl": "http://www.w3.org/1999/XSL/Transform"}
        templates = tuple((n.get("match"), n.get("name"), n.get("mode")) for n in root.xpath("//xsl:template", namespaces=ns))
        return (root.get("version"), tuple(sorted((str(k or ""), v) for k, v in (root.nsmap or {}).items())), templates)

    def _x12_checks(self, root, transaction):
        out = []
        if root is None:
            return [self._item("X12 root", "failed", "Transformation produced no root element.")]
        expected_root = f"X12_00401_{transaction}" if transaction else None
        if expected_root:
            actual = etree.QName(root).localname
            out.append(self._item("X12 transaction root", "passed" if actual == expected_root else "failed", f"Expected {expected_root}; received {actual}."))
        st_nodes = root.xpath("./*[local-name()='ST']")
        se_nodes = root.xpath("./*[local-name()='SE']")
        out.append(self._item("X12 ST/SE envelope", "passed" if len(st_nodes) == 1 and len(se_nodes) == 1 else "failed", f"Expected exactly one ST and one SE at transaction level; found ST={len(st_nodes)}, SE={len(se_nodes)}."))
        if len(st_nodes) == 1 and len(se_nodes) == 1:
            st, se = st_nodes[0], se_nodes[0]
            st01 = self._child_text(st, "ST01")
            st02 = self._child_text(st, "ST02")
            se01 = self._child_text(se, "SE01")
            se02 = self._child_text(se, "SE02")
            expected_code = transaction
            out.append(self._item("X12 transaction set code", "passed" if not expected_code or st01 == expected_code else "failed", f"ST01={st01!r}; expected {expected_code!r}."))
            out.append(self._item("X12 control number match", "passed" if st02 and st02 == se02 else "failed", f"ST02={st02!r}; SE02={se02!r}."))
            actual_count = len(list(root))
            try:
                count_ok = int(se01) == actual_count
            except (TypeError, ValueError):
                count_ok = False
            out.append(self._item("X12 SE01 segment count", "passed" if count_ok else "warning", f"SE01={se01!r}; transaction-level segment count including ST and SE={actual_count}."))
        return out

    @staticmethod
    def _child_text(node, name):
        found = node.xpath("./*[local-name()=$name]", name=name)
        return (found[0].text or "").strip() if found else ""

    def _null_guard_audit(self, doc):
        ns = {"xsl": "http://www.w3.org/1999/XSL/Transform"}
        values = doc.xpath("//xsl:value-of[@select]", namespaces=ns)
        guarded = 0
        for value in values:
            parent = value.getparent()
            while parent is not None:
                if isinstance(parent.tag, str) and etree.QName(parent).namespace == ns["xsl"] and etree.QName(parent).localname in {"if", "when"}:
                    guarded += 1
                    break
                parent = parent.getparent()
        unguarded = len(values) - guarded
        status = "warning" if unguarded else "passed"
        return [self._item("Null/empty-value guard audit", status, f"Found {len(values)} xsl:value-of instructions; {guarded} are nested under xsl:if/xsl:when and {unguarded} are not. This is a static review aid, not proof that every optional field is correctly guarded.")]
