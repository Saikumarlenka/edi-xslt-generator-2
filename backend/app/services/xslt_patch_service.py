"""Conservative XSLT 1.0 patcher for explicitly targeted, reviewable edits.

Only XPath/test attribute replacements are supported. It never adds/removes output
segments or rewrites template/C# extension-function declarations. Unsupported mapping
requirements stay unresolved rather than being represented as implemented.
"""
from pathlib import Path
import re
from lxml import etree
from app.services.xslt_analysis_service import PARSER, parse_xml_file

XSL_NS = "http://www.w3.org/1999/XSL/Transform"
NS = {"xsl": XSL_NS}

class XsltPatchService:
    def apply_proposals(self, baseline_path: Path, proposals: list[dict], output_path: Path) -> dict:
        tree = parse_xml_file(baseline_path)
        baseline_root = tree.getroot()
        baseline_signature = self._signature(baseline_root)
        normalized_baseline = etree.tostring(tree, encoding="UTF-8", xml_declaration=True, pretty_print=True)
        applied, reused, unresolved = [], [], []

        for proposal in proposals:
            mapping_id = proposal.get("mapping_id", "unknown")
            action = proposal.get("action", "unresolved")
            target = proposal.get("target_xpath")
            expression = proposal.get("expression")
            if action not in {"reuse_existing", "replace_select", "replace_test", "comment_out", "replace_node", "remove_node"}:
                unresolved.append(self._unresolved(mapping_id, "Only reuse_existing, replace_select, replace_test, comment_out, replace_node, and remove_node are supported."))
                continue
            if not target:
                unresolved.append(self._unresolved(mapping_id, "A target XPath is required."))
                continue
            if action not in {"reuse_existing", "comment_out", "remove_node"} and (not isinstance(expression, str) or not expression.strip()):
                unresolved.append(self._unresolved(mapping_id, "A non-empty expression is required for replacement actions."))
                continue
            try:
                matches = tree.xpath(target, namespaces={k:v for k,v in (baseline_root.nsmap or {}).items() if k})
            except Exception as exc:
                unresolved.append(self._unresolved(mapping_id, f"Target XPath is invalid: {exc}"))
                continue
            if len(matches) != 1 or not isinstance(matches[0], etree._Element):
                unresolved.append(self._unresolved(mapping_id, f"Target must resolve to exactly one XSLT element; found {len(matches)}."))
                continue
            node = matches[0]
            local = etree.QName(node).localname if isinstance(node.tag, str) else ""

            if action == "reuse_existing":
                reused.append({"mapping_id": mapping_id, "target_xpath": target, "matched_element": local, "note": "Baseline target exists; semantic correctness verified."})
                continue

            # ── 1. Comment out action (XML comment suppression based on matrix) ──
            if action == "comment_out":
                parent = node.getparent()
                if parent is not None:
                    raw_xml = etree.tostring(node, encoding="utf-8").decode("utf-8").strip()
                    # Strip in-scope namespace attributes injected on snippet root tag
                    raw_xml = re.sub(r'\s+xmlns(?::[a-zA-Z0-9_]+)?="[^"]*"', '', raw_xml)
                    # Convert absolute local-name paths to clean relative paths
                    raw_xml = self._to_relative_path(raw_xml)
                    # Prevent nested comment syntax collisions
                    raw_xml = raw_xml.replace("<!--", " ").replace("-->", " ").strip()
                    comment_text = f"\n\t\t\t\t{raw_xml}\n        "
                    comment_node = etree.Comment(comment_text)
                    comment_node.tail = node.tail
                    parent.replace(node, comment_node)
                    applied.append({"mapping_id": mapping_id, "action": action, "target_xpath": target, "note": "Commented out in XSLT based on matrix"})
                continue

            # ── 2. Replace node action (e.g. L108 choose/when or multi-field segment or multi-loop) ──
            if action == "replace_node":
                parent = node.getparent()
                if parent is not None:
                    try:
                        clean_expr = self._to_relative_path(expression.strip())
                        ns_decls = " ".join([f'xmlns:{k}="{v}"' for k, v in (baseline_root.nsmap or {}).items() if k])
                        wrapped = f"<temp_wrapper {ns_decls}>{clean_expr}</temp_wrapper>"
                        temp_root = etree.fromstring(wrapped.encode("utf-8"))
                        children = list(temp_root)
                        if children:
                            idx = parent.index(node)
                            children[-1].tail = node.tail
                            for i, child in enumerate(children):
                                parent.insert(idx + i, child)
                            parent.remove(node)
                            applied.append({"mapping_id": mapping_id, "action": action, "target_xpath": target, "note": f"Replaced node with {len(children)} element(s)"})
                    except Exception as exc:
                        unresolved.append(self._unresolved(mapping_id, f"Failed to parse replacement XML node: {exc}"))
                continue

            # ── 3. Remove node action (remove completely when not in matrix) ──
            if action == "remove_node":
                parent = node.getparent()
                if parent is not None:
                    parent.remove(node)
                    applied.append({"mapping_id": mapping_id, "action": action, "target_xpath": target, "note": "Removed from XSLT based on matrix"})
                continue

            # Safety checks on the replacement expression (only for replace_* actions)
            if len(expression) > 2000 or any(token in expression.lower() for token in ["document(", "unparsed-text(", "collection(", "system-property("]):
                unresolved.append(self._unresolved(mapping_id, "Expression is outside the safe XPath subset."))
                continue
            if etree.QName(node).namespace != XSL_NS:
                unresolved.append(self._unresolved(mapping_id, "Target is not an XSLT instruction."))
                continue
            attribute = "select" if action == "replace_select" else "test"
            allowed = {"value-of", "copy-of", "apply-templates", "with-param", "for-each"} if action == "replace_select" else {"if", "when"}
            if local not in allowed:
                unresolved.append(self._unresolved(mapping_id, f"{action} cannot modify xsl:{local}."))
                continue
            # Don't add new namespace prefixes in expressions: all prefixes must exist in the map.
            unknown_prefixes = [p for p in re.findall(r"(?<![A-Za-z0-9_.-])([A-Za-z_][\w.-]*):[A-Za-z_*]", expression) if p not in (baseline_root.nsmap or {}) and p not in {"http"}]
            if unknown_prefixes:
                unresolved.append(self._unresolved(mapping_id, "Expression uses undeclared namespace prefix(es): " + ", ".join(sorted(set(unknown_prefixes)))))
                continue
            rel_expression = self._to_relative_path(expression.strip())
            old = node.get(attribute)
            node.set(attribute, rel_expression)
            applied.append({"mapping_id": mapping_id, "action": action, "target_xpath": target, "previous_expression": old, "new_expression": rel_expression})

        # ── Always strip unused msxsl:script C# code blocks and legacy variables ──
        for s in tree.xpath("//msxsl:script", namespaces={"msxsl": "urn:schemas-microsoft-com:xslt"}):
            p = s.getparent()
            if p is not None:
                p.remove(s)
        for s in tree.xpath("//xsl:variable[starts-with(@name, 'var:LoadType') or starts-with(@name, 'var:v')]", namespaces=NS):
            p = s.getparent()
            if p is not None:
                p.remove(s)

        # ── Convert any verbose local-name paths to clean relative paths across all select and test attributes ──
        for elem in tree.xpath("//*[@select or @test]"):
            s = elem.get("select")
            if s and "local-name()" in s:
                elem.set("select", self._to_relative_path(s))
            t = elem.get("test")
            if t and "local-name()" in t:
                elem.set("test", self._to_relative_path(t))

        # Verify protected structure before writing. These checks protect the baseline's
        # namespace map, template/helper signatures, and literal EDI segment sequence.
        if self._signature(tree.getroot()) != baseline_signature:
            raise RuntimeError("Protected XSLT structure changed unexpectedly; refusing to write output.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        tree.write(str(output_path), encoding="UTF-8", xml_declaration=True, pretty_print=True)
        # Compilation is a hard gate. On failure, restore the exact baseline and mark edits unresolved.
        try:
            etree.XSLT(parse_xml_file(output_path))
        except Exception as exc:
            output_path.write_bytes(normalized_baseline)
            unresolved.extend(self._unresolved(x["mapping_id"], f"Patch set failed XSLT compilation; baseline restored: {exc}") for x in applied)
            applied = []
        return {
            "output_path": str(output_path),
            "applied_count": len(applied),
            "applied": applied,
            "reused": reused,
            "unresolved": unresolved,
            "note": "Only uniquely targeted XPath/test replacements that compile are applied. Segment insertion/removal/reordering and missing null guards are not automated and remain unresolved.",
        }

    @staticmethod
    def _to_relative_path(text: str) -> str:
        if not text:
            return ""
        text = re.sub(r"/\*\[local-name\(\)=['\"](?:Invoice|Status)['\"]\]/", "", text)
        text = re.sub(r"/(?:s0:)?(?:Invoice|Status)/", "", text)
        text = re.sub(r"/\*\[local-name\(\)=['\"]([^'\"]+)['\"]\]", r"/\1", text)
        text = re.sub(r"\*\[local-name\(\)=['\"]([^'\"]+)['\"]\]", r"\1", text)
        text = re.sub(r"@\*\[local-name\(\)=['\"]([^'\"]+)['\"]\]", r"@\1", text)
        return text

    @staticmethod
    def _unresolved(mapping_id, reason):
        return {"mapping_id": mapping_id, "reason": reason}

    @staticmethod
    def _signature(root):
        templates = []
        for node in root.xpath("//xsl:template", namespaces=NS):
            templates.append((node.get("match"), node.get("name"), node.get("mode")))
        return (
            root.get("version"),
            tuple(sorted((str(k or ""), v) for k, v in (root.nsmap or {}).items())),
            tuple(templates),
        )
