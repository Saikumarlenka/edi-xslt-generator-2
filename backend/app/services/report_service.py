from datetime import datetime, timezone

def build_report(job: dict) -> dict:
    spec=job.get("mapping") or {}
    mappings=spec.get("mappings", [])
    statuses={s:sum(1 for m in mappings if m.get("implementation_status")==s) for s in ["implemented_and_validated","implemented_with_warnings","constant_value","excluded_crossed_out","unresolved","failed_validation","requires_user_clarification"]}
    return {"job_id":job["job_id"],"transaction":job["transaction"],"generated_at":datetime.now(timezone.utc).isoformat(),"mapping_count":len(mappings),"coverage":statuses,"validation":job.get("validation",{}),"patch_result":job.get("patch_result",{}),"warnings":job.get("warnings",[]),"errors":job.get("errors",[]),"limitations":["Only unique XPath/test replacements and verified reuse targets are handled automatically; new segment/template insertion and null-guard insertion remain unresolved.","lxml/libxslt does not reproduce the full BizTalk runtime or every proprietary C# extension function.","Official Stedi validation is not connected; current X12 checks are local structural checks only.","Schema validation is only valid when the supplied XSD namespace and document root namespace are compatible."]}
