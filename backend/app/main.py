from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.routes_health import router as health_router
from app.api.routes_reference_files import router as references_router
from app.api.routes_generation import router as generation_router

app=FastAPI(title="EDI XSLT Generator",version="0.1.0",description="AI-assisted EDI 210/214 XSLT analysis and validation")
app.add_middleware(CORSMiddleware,allow_origins=[settings.frontend_origin],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
app.include_router(health_router,prefix="/api",tags=["health"])
app.include_router(references_router,prefix="/api",tags=["reference-files"])
app.include_router(generation_router,prefix="/api",tags=["generation"])
@app.get("/")
def root(): return {"name":"EDI XSLT Generator","docs":"/docs","health":"/api/health"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.backend_host, port=settings.backend_port, reload=True)
