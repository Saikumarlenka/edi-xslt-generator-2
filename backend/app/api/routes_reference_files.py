from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
from app.core.config import DATA_ROOT
from app.services.file_service import save_upload
router=APIRouter()
KINDS={"matrix":"matrix","standard_xslt":"xslt","canonical_xsd":"xsd","edi_xsd":"xsd","canonical_xml":"xml","sample_xslt":"sample_xslt"}
def tx_dir(transaction):
    if transaction not in ("210","214"): raise HTTPException(400,"Transaction must be 210 or 214")
    return DATA_ROOT/"references"/transaction
@router.get("/reference-files/{transaction}")
def list_reference_files(transaction: str):
    d=tx_dir(transaction); result={k:None for k in KINDS}; result["sample_xslt"]=[]
    for key,kind in KINDS.items():
        p=d/key
        if key=="sample_xslt": result[key]=[{"name":f.name,"size":f.stat().st_size} for f in p.glob("*") if f.is_file()] if p.exists() else []
        elif p.exists() and p.is_file(): result[key]={"name":p.name,"size":p.stat().st_size}
    return {"transaction":transaction,"files":result,"ready":all(result[k] for k in ["standard_xslt","canonical_xsd","edi_xsd","canonical_xml"])}
@router.post("/reference-files/{transaction}")
async def upload_reference_file(transaction: str, kind: str, file: UploadFile=File(...)):
    if kind not in KINDS: raise HTTPException(400,f"kind must be one of {', '.join(KINDS)}")
    base=tx_dir(transaction); base.mkdir(parents=True,exist_ok=True)
    if kind=="sample_xslt": dest=base/kind
    else: dest=base
    saved=await save_upload(file,dest,KINDS[kind])
    if kind!="sample_xslt":
        canonical=base/kind
        if saved != canonical:
            canonical.unlink(missing_ok=True)
            saved.replace(canonical)
            saved=canonical
    return {"kind":kind,"name":saved.name,"size":saved.stat().st_size,"message":"Reference file uploaded"}
