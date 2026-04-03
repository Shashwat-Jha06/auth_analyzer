from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from typing import Dict
import uuid
import asyncio
import json
import sys
import io

# Force UTF-8 on Windows so Unicode in print() never crashes the server
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding and sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Fix for Windows + Python 3.12 asyncio compatibility
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from app.models import AnalysisRequest, AnalysisResponse, JobStatus
from app.services.job_manager import job_manager
from app.services.browserless_scraper import BrowserlessScraper
# from app.services.scraper import DeepScraper
# from app.services.selenium_scraper import SeleniumScraper
from app.services.analyzer import AIAnalyzer
from app.config import settings

app = FastAPI(
    title="Auth Component Analyzer API",
    description="Deep Mode AI-powered authentication component detection",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production: specify Vercel domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============= ENDPOINTS =============

@app.get("/")
async def root():
    return {
        "message": "Auth Component Analyzer API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT
    }

@app.post("/api/analyze", response_model=AnalysisResponse)
async def analyze_url(request: AnalysisRequest, background_tasks: BackgroundTasks):
    """
    Start deep analysis of a URL for authentication components.
    Returns job_id immediately, processes in background.
    """
    job_id = str(uuid.uuid4())
    url = str(request.url)
    
    # Create job
    job_manager.create_job(job_id, url)
    
    # Start background processing
    background_tasks.add_task(process_analysis, job_id, url, request.ai_mode)
    
    return AnalysisResponse(
        job_id=job_id,
        status="pending",
        message=f"Analysis started for {url}",
        stream_url=f"/api/stream/{job_id}"
    )

@app.get("/api/status/{job_id}", response_model=JobStatus)
async def get_job_status(job_id: str):
    """Get current status of analysis job"""
    job = job_manager.get_job(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job

@app.get("/api/stream/{job_id}")
async def stream_analysis(job_id: str):
    """
    Stream real-time chain-of-thought events via Server-Sent Events (SSE).
    Frontend connects to this endpoint to receive live updates.
    """
    
    async def event_generator():
        queue = job_manager.get_event_queue(job_id)
        if not queue:
            yield f"data: {json.dumps({'error': 'Job not found'})}\n\n"
            return
        
        # Send initial connection event
        yield f"data: {json.dumps({'event': 'connected', 'job_id': job_id})}\n\n"
        
        # Poll queue for events
        timeout_counter = 0
        max_timeout = 300  # 30 seconds (300 * 100ms)
        
        while timeout_counter < max_timeout:
            if not queue.empty():
                event = queue.get()
                yield f"data: {json.dumps(event)}\n\n"
                
                # End stream when complete
                if event.get("event") in ["complete", "error"]:
                    break
                
                timeout_counter = 0  # Reset timeout
            else:
                await asyncio.sleep(0.1)
                timeout_counter += 1
        
        # Send end event
        yield f"data: {json.dumps({'event': 'end'})}\n\n"
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.get("/api/examples")
async def get_examples():
    """
    Return 5 pre-analyzed website examples (core requirement).
    These demonstrate the system capabilities.
    """
    return {
        "examples": [
            {
                "id": "example-github",
                "name": "GitHub",
                "url": "https://github.com/login",
                "components_found": True,
                "preview": "Email/Password + OAuth",
                "auth_methods": ["email_password", "oauth"],
                "description": "Traditional login with social auth - 12 components detected"
            },
            {
                "id": "example-stackoverflow",
                "name": "Stack Overflow",
                "url": "https://stackoverflow.com/users/login",
                "components_found": True,
                "preview": "Email/Password + OAuth (Google, GitHub)",
                "auth_methods": ["email_password", "oauth"],
                "description": "Developer community login with multiple OAuth providers"
            },
            {
                "id": "example-reddit",
                "name": "Reddit",
                "url": "https://www.reddit.com/login/",
                "components_found": True,
                "preview": "Username/Password + OAuth",
                "auth_methods": ["email_password", "oauth"],
                "description": "Social platform with traditional and OAuth login"
            },
            {
                "id": "example-gitlab",
                "name": "GitLab",
                "url": "https://gitlab.com/users/sign_in",
                "components_found": True,
                "preview": "Email/Password + OAuth + SAML",
                "auth_methods": ["email_password", "oauth", "saml"],
                "description": "DevOps platform with enterprise SSO options"
            },
            {
                "id": "example-wordpress",
                "name": "WordPress.com",
                "url": "https://wordpress.com/log-in",
                "components_found": True,
                "preview": "Email/Password + Social Login",
                "auth_methods": ["email_password", "oauth"],
                "description": "CMS platform with email and social authentication"
            }
        ]
    }

# ============= BACKGROUND PROCESSING =============

async def process_analysis(job_id: str, url: str, ai_mode: bool = False):
    """
    Background task that performs complete deep analysis.
    Can take 20-30 seconds without timeout issues.
    """
    event_queue = job_manager.get_event_queue(job_id)
    
    try:
        # Update status
        job_manager.update_job(job_id, {
            "status": "processing",
            "stage": "initializing",
            "progress": 5
        })
        
        # Send event
        if event_queue:
            event_queue.put({
                "event": "progress",
                "stage": "initializing",
                "timestamp": str(uuid.uuid4()),
                "data": {"message": "Starting deep analysis..."}
            })
        
        # Stage 1: Scraping with Playwright
        job_manager.update_job(job_id, {
            "stage": "scraping",
            "progress": 20
        })
        
        if event_queue:
            event_queue.put({
                "event": "progress",
                "stage": "scraping",
                "timestamp": str(uuid.uuid4()),
                "data": {"message": "Launching browser and scraping page..."}
            })
        
        # Playwright has subprocess issues on Windows + Python 3.12
        # Use Browserless as primary scraper
        scrape_result = None

        # Use Browserless scraper (cloud browser, no local driver needed)
        print(f"[DEBUG] Using BrowserlessScraper")
        scraper = BrowserlessScraper(settings.BROWSERLESS_TOKEN)
        scrape_result = await scraper.scrape_with_triggers(url, event_queue=event_queue)

        # # Selenium fallback (local Chrome — disabled)
        # print(f"[DEBUG] Using Selenium scraper")
        # scraper = SeleniumScraper()
        # scrape_result = await scraper.scrape_with_triggers(url, event_queue=event_queue)
        
        # Stage 2: AI Analysis with LangChain
        job_manager.update_job(job_id, {
            "stage": "ai_analysis",
            "progress": 50
        })
        
        if event_queue:
            event_queue.put({
                "event": "progress",
                "stage": "ai_analysis",
                "timestamp": str(uuid.uuid4()),
                "data": {"message": "AI is analyzing authentication components..."}
            })
        
        analyzer = AIAnalyzer(event_queue=event_queue, job_id=job_id)
        analysis_result = await analyzer.analyze_progressive(url, scrape_result, ai_mode=ai_mode)
        
        # Stage 3: Finalize
        job_manager.update_job(job_id, {
            "stage": "finalizing",
            "progress": 95
        })
        
        # Complete job
        job_manager.complete_job(job_id, analysis_result)
        
        # Send completion event
        if event_queue:
            event_queue.put({
                "event": "complete",
                "timestamp": str(uuid.uuid4()),
                "data": {
                    "message": "Analysis complete!",
                    "components_found": analysis_result.components_found
                }
            })
    
    except Exception as e:
        error_message = str(e)
        print(f"[Error] Job {job_id} failed: {error_message}")
        
        job_manager.fail_job(job_id, error_message)
        
        if event_queue:
            event_queue.put({
                "event": "error",
                "timestamp": str(uuid.uuid4()),
                "data": {"error": error_message}
            })

# ============= STARTUP/SHUTDOWN =============

@app.on_event("startup")
async def startup_event():
    print("=" * 50)
    print("Auth Component Analyzer API Starting")
    print(f"Environment: {settings.ENVIRONMENT}")
    print(f"LLM Model: {settings.LLM_MODEL}")
    print("=" * 50)

@app.on_event("shutdown")
async def shutdown_event():
    print("Shutting down API...")
    job_manager.cleanup_old_jobs(max_age_hours=1)
