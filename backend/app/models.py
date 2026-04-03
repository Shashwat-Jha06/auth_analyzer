from pydantic import BaseModel, HttpUrl, Field
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime

# Request Models
class AnalysisRequest(BaseModel):
    url: HttpUrl
    mode: Literal["deep"] = "deep"
    ai_mode: bool = False   # When True, run per-component AI analysis

# Response Models
class AnalysisResponse(BaseModel):
    job_id: str
    status: str
    message: str
    stream_url: str

# Auth Component Models
class AIComponentAnalysis(BaseModel):
    accepted: bool = Field(default=True, description="True = confirmed auth component, False = AI flagged as false positive")
    category: str = Field(description="Short category label e.g. 'Google OAuth Button', 'Email/Password Login Form'")
    provider: Optional[str] = Field(default=None, description="Identity provider e.g. Google, Apple")
    summary: str = Field(default="", description="One-sentence description")
    html_evidence: List[str] = Field(default_factory=list, description="3 specific HTML-level points proving auth relevance")
    rejection_reason: Optional[str] = Field(default=None, description="Why rejected — cites specific HTML attributes")

class AuthComponent(BaseModel):
    html_snippet: str = Field(description="The HTML code snippet")
    component_type: str = Field(description="Type: form, oauth_button, input_field, etc.")
    purpose: str = Field(description="Purpose of this component")
    selector: Optional[str] = Field(default=None, description="CSS selector if available")
    confidence: float = Field(description="Confidence score 0-1")
    ai_analysis: Optional[AIComponentAnalysis] = Field(default=None, description="AI explanation (AI Enhanced mode only)")

class AuthMethod(BaseModel):
    method_type: str = Field(description="email/password, oauth, magic_link, sso, etc.")
    provider: Optional[str] = Field(default=None, description="Provider name if OAuth/SSO")
    detected_by: str = Field(description="How was this detected")

class AuthFlow(BaseModel):
    steps: List[str] = Field(description="Sequential steps in auth flow")
    flow_type: str = Field(description="modal, dedicated_page, inline, etc.")
    diagram: Optional[str] = Field(default=None, description="Mermaid diagram of flow")

class TechStack(BaseModel):
    framework: Optional[str] = Field(default=None, description="Frontend framework")
    auth_library: Optional[str] = Field(default=None, description="Auth library/service")
    backend: Optional[str] = Field(default=None, description="Backend technology")
    confidence: float = Field(description="Overall detection confidence")
    evidence: List[str] = Field(description="Evidence for detections")

class SecurityAnalysis(BaseModel):
    https_enabled: bool
    password_requirements: Optional[str] = None
    two_factor_available: bool
    security_notes: List[str]
    score: float = Field(description="Security score 0-10")

# Complete Analysis Result
class AuthAnalysis(BaseModel):
    url: str
    components_found: bool
    components: List[AuthComponent]
    auth_methods: List[AuthMethod]
    auth_flow: AuthFlow
    detected_stack: TechStack
    security: SecurityAnalysis
    overall_confidence: float
    timestamp: datetime

# Job Status Models
class JobStatus(BaseModel):
    job_id: str
    status: Literal["pending", "processing", "completed", "failed"]
    progress: int = Field(default=0, ge=0, le=100)
    stage: Optional[str] = None
    result: Optional[AuthAnalysis] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

# Streaming Event Models
class StreamEvent(BaseModel):
    event: str
    stage: Optional[str] = None
    timestamp: str
    data: Dict[str, Any]

# Scraping Models
class TriggerAction(BaseModel):
    action_type: str  # click, navigate, hover
    selector: Optional[str] = None
    url: Optional[str] = None
    description: str

class ScrapeResult(BaseModel):
    initial_html: str
    triggered_states: List[Dict[str, Any]]
    network_requests: List[str]
    page_title: str
    final_url: str
