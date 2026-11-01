import json, uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import RLock
from app.core.config import DATA_ROOT

LOCK=RLock(); JOBS={}

def new_job(transaction: str, method: str = "python") -> dict:
    job_id=str(uuid.uuid4()); folder=DATA_ROOT/"jobs"/job_id; folder.mkdir(parents=True, exist_ok=True)
    msg = (
        "Deterministic Python matrix parser is extracting mapping rows"
        if method == "python"
        else "Gemini is interpreting the matrix document"
    )
    job={"job_id":job_id,"transaction":transaction,"status":"queued","stage":"queued","extraction_method":method,"message":msg,"errors":[],"warnings":[],"created_at":datetime.now(timezone.utc).isoformat(),"folder":str(folder),"mapping":None,"analysis":None,"proposals":[],"validation":{},"artifacts":{}}
    with LOCK: JOBS[job_id]=job; persist(job)
    return job

def persist(job):
    path=Path(job["folder"])/"job.json"; safe={k:v for k,v in job.items() if k!="folder"}
    path.write_text(json.dumps(safe,indent=2,default=str),encoding="utf-8")

def get_job(job_id: str):
    with LOCK:
        if job_id in JOBS: return JOBS[job_id]
        folder=DATA_ROOT/"jobs"/job_id; path=folder/"job.json"
        if path.exists():
            job=json.loads(path.read_text(encoding="utf-8")); job["folder"]=str(folder); JOBS[job_id]=job; return job
    return None

def update(job):
    with LOCK: persist(job)
