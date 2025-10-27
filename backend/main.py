from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from typing import Optional, List
import asyncio
import logging
from pathlib import Path
import hashlib

from modules.fetcher import DocumentationFetcher
from modules.parser import ContentParser
from modules.translator import TranslationEngine
from modules.builder import StaticSiteBuilder

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Documentation Translation System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

fetcher = DocumentationFetcher()
parser = ContentParser()
translator = TranslationEngine()
builder = StaticSiteBuilder()

processing_status = {}


class FetchRequest(BaseModel):
    url: str
    source_type: str
    max_pages: Optional[int] = 50
    target_path: Optional[str] = None


class TranslateRequest(BaseModel):
    project_id: str
    source_lang: str = "en"
    target_lang: str = "es"


class ParseRequest(BaseModel):
    project_id: str


class BuildRequest(BaseModel):
    project_id: str
    project_name: str
    create_package: bool = True


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Documentation Translation System API",
        "version": "1.0.0",
        "endpoints": {
            "fetch": "/api/fetch",
            "translate": "/api/translate",
            "build": "/api/build",
            "status": "/api/status/{project_id}",
            "languages": "/api/languages",
            "download": "/api/download/{filename}"
        }
    }


@app.get("/api/languages")
async def get_supported_languages():
    """Get list of supported languages"""
    return translator.get_supported_languages()


@app.post("/api/fetch")
async def fetch_documentation(request: FetchRequest, background_tasks: BackgroundTasks):
    """
    Fetch documentation from GitHub or website
    """
    try:
        url_clean = request.url.rstrip('/').replace('.git', '')
        url_hash = hashlib.md5(url_clean.encode()).hexdigest()[:8]
        project_id = f"{url_clean.split('/')[-1].replace('.', '_')}_{url_hash}"
        
        if not project_id or project_id == f"_{url_hash}":
            project_id = f"project_{url_hash}"
        
        processing_status[project_id] = {
            "status": "fetching",
            "progress": 0,
            "message": "Fetching documentation..."
        }
        
        if request.source_type == "github":
            result = await fetcher.fetch_github_repo(request.url, request.target_path)
        elif request.source_type == "website":
            max_pages = request.max_pages if request.max_pages is not None else 50
            result = await fetcher.fetch_website(request.url, max_pages)
        else:
            raise HTTPException(status_code=400, detail="Invalid source type")
        
        if result.get("status") == "success":
            processing_status[project_id] = {
                "status": "fetched",
                "progress": 33,
                "message": f"Fetched {result.get('file_count', result.get('page_count', 0))} files",
                "data": result
            }
            
            return {
                "status": "success",
                "project_id": project_id,
                "result": result
            }
        else:
            processing_status[project_id] = {
                "status": "error",
                "message": result.get("message", "Unknown error")
            }
            raise HTTPException(status_code=500, detail=result.get("message"))
            
    except Exception as e:
        logger.error(f"Fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/parse")
async def parse_documentation(request: ParseRequest):
    """
    Parse fetched documentation
    """
    try:
        project_id = request.project_id
        if project_id not in processing_status:
            raise HTTPException(status_code=404, detail="Project not found")
        
        project_data = processing_status[project_id].get("data")
        if not project_data:
            raise HTTPException(status_code=400, detail="No data to parse")
        
        processing_status[project_id]["status"] = "parsing"
        processing_status[project_id]["message"] = "Parsing documentation..."
        
        files = project_data.get("files", [])
        if not files:
            pages = project_data.get("pages", [])
            files = [{"path": p["file_path"]} for p in pages]
        
        file_paths = [f["path"] for f in files[:50]]
        
        parsed_results = []
        for file_path in file_paths:
            parsed = parser.parse_file(file_path)
            if parsed.get("status") == "success":
                parsed_results.append(parsed)
        
        processing_status[project_id]["parsed_data"] = parsed_results
        processing_status[project_id]["status"] = "parsed"
        processing_status[project_id]["progress"] = 50
        processing_status[project_id]["message"] = f"Parsed {len(parsed_results)} files"
        
        return {
            "status": "success",
            "project_id": project_id,
            "parsed_count": len(parsed_results)
        }
        
    except Exception as e:
        logger.error(f"Parse error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/translate")
async def translate_documentation(request: TranslateRequest):
    """
    Translate parsed documentation
    """
    try:
        if request.project_id not in processing_status:
            raise HTTPException(status_code=404, detail="Project not found")
        
        project_status = processing_status[request.project_id]
        
        if "parsed_data" not in project_status:
            try:
                await parse_documentation(ParseRequest(project_id=request.project_id))
                project_status = processing_status[request.project_id]
            except HTTPException as e:
                raise HTTPException(status_code=e.status_code, detail=f"Parse failed: {e.detail}")
        
        parsed_data = project_status.get("parsed_data", [])
        if not parsed_data:
            raise HTTPException(status_code=400, detail="No parsed data available")
        
        processing_status[request.project_id]["status"] = "translating"
        processing_status[request.project_id]["message"] = f"Translating to {request.target_lang}..."
        
        translated_results = []
        total = len(parsed_data)
        
        for i, parsed_doc in enumerate(parsed_data):
            translated = await translator.translate_document(
                parsed_doc,
                request.source_lang,
                request.target_lang
            )
            translated_results.append(translated)
            
            progress = 50 + int((i + 1) / total * 30)
            processing_status[request.project_id]["progress"] = progress
            processing_status[request.project_id]["message"] = f"Translating... ({i+1}/{total})"
        
        processing_status[request.project_id]["translated_data"] = translated_results
        processing_status[request.project_id]["status"] = "translated"
        processing_status[request.project_id]["progress"] = 80
        processing_status[request.project_id]["target_lang"] = request.target_lang
        processing_status[request.project_id]["message"] = f"Translated {len(translated_results)} documents"
        
        return {
            "status": "success",
            "project_id": request.project_id,
            "translated_count": len(translated_results),
            "target_lang": request.target_lang
        }
        
    except Exception as e:
        logger.error(f"Translation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/build")
async def build_site(request: BuildRequest):
    """
    Build static site from translated documentation
    """
    try:
        if request.project_id not in processing_status:
            raise HTTPException(status_code=404, detail="Project not found")
        
        project_status = processing_status[request.project_id]
        translated_data = project_status.get("translated_data")
        target_lang = project_status.get("target_lang", "es")
        
        if not translated_data:
            raise HTTPException(status_code=400, detail="No translated data available")
        
        processing_status[request.project_id]["status"] = "building"
        processing_status[request.project_id]["message"] = "Building static site..."
        
        build_result = builder.build_site(
            request.project_name,
            translated_data,
            target_lang
        )
        
        if build_result.get("status") != "success":
            raise HTTPException(status_code=500, detail=build_result.get("message"))
        
        package_result = None
        if request.create_package:
            processing_status[request.project_id]["message"] = "Creating downloadable package..."
            package_result = builder.create_downloadable_package(
                build_result["site_dir"],
                request.project_name,
                target_lang
            )
        
        processing_status[request.project_id]["status"] = "completed"
        processing_status[request.project_id]["progress"] = 100
        processing_status[request.project_id]["message"] = "Build completed!"
        processing_status[request.project_id]["build_result"] = build_result
        processing_status[request.project_id]["package_result"] = package_result
        
        return {
            "status": "success",
            "project_id": request.project_id,
            "build_result": build_result,
            "package_result": package_result
        }
        
    except Exception as e:
        logger.error(f"Build error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/status/{project_id}")
async def get_status(project_id: str):
    """Get project processing status"""
    if project_id not in processing_status:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return processing_status[project_id]


@app.get("/api/download/{filename}")
async def download_file(filename: str):
    """Download a generated package"""
    file_path = Path("downloads") / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/zip"
    )


@app.get("/api/projects")
async def list_projects():
    """List all projects"""
    return {
        "status": "success",
        "projects": [
            {
                "project_id": pid,
                "status": data.get("status"),
                "message": data.get("message")
            }
            for pid, data in processing_status.items()
        ]
    }


if FRONTEND_DIR.exists():
    app.mount("/frontend", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")


@app.get("/app")
async def serve_app():
    """Serve the main application"""
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="Frontend not found")
    return FileResponse(str(index_path))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
