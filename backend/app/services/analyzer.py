"""
Analyzer: programmatic extraction + optional per-component AI analysis.
AI mode uses DeepSeek (OpenAI-compatible, very cheap) in a single batched call.
"""
import json
import re
from datetime import datetime
from queue import Queue
from typing import Any, Dict, List, Optional

from app.config import settings
from app.models import (
    AuthAnalysis, AuthComponent, AuthFlow, AuthMethod,
    AIComponentAnalysis, ScrapeResult, SecurityAnalysis, TechStack,
)


def _build_llm():
    """Return the configured LLM client (Groq > Gemini > OpenAI)."""
    if settings.USE_GROQ:
        from langchain_groq import ChatGroq
        print(f"[Analyzer] AI mode: Groq ({settings.LLM_MODEL})")
        return ChatGroq(
            model=settings.LLM_MODEL,
            api_key=settings.GROQ_API_KEY,
            temperature=settings.LLM_TEMPERATURE,
            max_tokens=settings.MAX_TOKENS,
        )
    if settings.USE_GEMINI:
        from langchain_google_genai import ChatGoogleGenerativeAI
        print(f"[Analyzer] AI mode: Gemini ({settings.LLM_MODEL})")
        return ChatGoogleGenerativeAI(
            model=settings.LLM_MODEL,
            google_api_key=settings.GOOGLE_API_KEY,
            temperature=settings.LLM_TEMPERATURE,
            max_output_tokens=settings.MAX_TOKENS,
        )
    from langchain_openai import ChatOpenAI
    print(f"[Analyzer] AI mode: OpenAI ({settings.LLM_MODEL})")
    return ChatOpenAI(
        model=settings.LLM_MODEL,
        api_key=settings.OPENAI_API_KEY,
        temperature=settings.LLM_TEMPERATURE,
        max_tokens=settings.MAX_TOKENS,
    )


async def _ai_analyze_components(
    url: str,
    components: List[Dict[str, Any]],
    event_queue: Optional[Queue],
) -> List[Dict[str, Any]]:
    """
    Single batched LLM call:
      - Filters false positives (sets accepted=False on bad ones)
      - Provides deep 3-point HTML evidence for accepted components
    Returns the same list with 'ai_analysis' dict on each entry.
    """
    if not components:
        return components

    import uuid as _uuid

    def _progress(msg: str):
        if event_queue:
            event_queue.put({
                "event": "progress",
                "stage": "ai_analysis",
                "timestamp": str(_uuid.uuid4()),
                "data": {"message": msg},
            })

    _progress(f"AI reviewing {len(components)} detected components for false positives...")

    # Compact payload — send enough HTML context without blowing token budget
    compact = []
    for i, c in enumerate(components):
        compact.append({
            "index":   i,
            "type":    c.get("component_type", ""),
            "purpose": c.get("purpose", ""),
            "snippet": c.get("html_snippet", "")[:500],   # 500 chars of HTML context
        })

    prompt = f"""You are a senior web authentication engineer performing a two-step review of HTML components extracted from: {url}

STEP 1 — FILTER (reduce false positives):
Decide whether each component is GENUINELY authentication-related.

ACCEPT if the component directly involves: credential collection, identity verification, session initiation, OAuth/SSO flows, passkey authentication, account creation.
REJECT if the component is: a newsletter signup, search bar, cookie consent, footer support link, general marketing CTA ("Get Started", "Try for free"), contact form, or anything unrelated to logging in or creating an account.

STEP 2 — ANALYZE (accepted components only):
Provide a deep, developer-focused analysis referencing SPECIFIC HTML attributes, element types, class names, data attributes, form actions, or structural patterns found in the snippet.

Respond with ONLY a valid JSON array — same length and order as the input. Each element must be EXACTLY one of these two shapes:

If ACCEPTED:
{{
  "index": <number>,
  "accepted": true,
  "category": "<concise label e.g. 'Google OAuth Button', 'Email/Password Login Form', 'Passkey Trigger'>",
  "provider": "<identity provider name or null>",
  "summary": "<one sentence describing the component's role in the auth flow>",
  "html_evidence": [
    "<Point 1: cite a specific attribute, tag, class, or structure and explain what it reveals about auth intent>",
    "<Point 2: another distinct HTML-level signal — different from Point 1>",
    "<Point 3: a third HTML-specific observation — e.g. form method, CSRF token, data-disable-with, button type, aria role, etc.>"
  ]
}}

If REJECTED:
{{
  "index": <number>,
  "accepted": false,
  "category": "<what this actually is>",
  "provider": null,
  "summary": "",
  "html_evidence": [],
  "rejection_reason": "<2-3 sentences citing specific HTML attributes or content that prove this is NOT an auth component>"
}}

Components to review:
{json.dumps(compact, indent=2)}"""

    try:
        llm = _build_llm()
        from langchain_core.messages import HumanMessage

        _progress("Waiting for AI response...")
        response = await llm.ainvoke([HumanMessage(content=prompt)])
        raw = response.content.strip()

        # Strip markdown fences
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"\s*```\s*$", "", raw, flags=re.MULTILINE)

        ai_results: List[Dict] = json.loads(raw)
        ai_by_index = {item["index"]: item for item in ai_results}

        accepted_count = sum(1 for r in ai_results if r.get("accepted", True))
        rejected_count = len(ai_results) - accepted_count
        _progress(f"AI review complete — {accepted_count} confirmed, {rejected_count} flagged as false positives")

        for i, comp in enumerate(components):
            ai = ai_by_index.get(i, {})
            accepted = ai.get("accepted", True)
            comp["ai_analysis"] = {
                "accepted":         accepted,
                "category":         ai.get("category", comp.get("component_type", "").replace("_", " ").title()),
                "provider":         ai.get("provider"),
                "summary":          ai.get("summary", ""),
                "html_evidence":    ai.get("html_evidence", []),
                "rejection_reason": ai.get("rejection_reason") if not accepted else None,
            }

    except Exception as e:
        print(f"[Analyzer] AI analysis failed: {e}")
        import traceback; traceback.print_exc()
        _progress("AI analysis encountered an error — showing programmatic results only")
        for comp in components:
            comp["ai_analysis"] = {
                "accepted":      True,
                "category":      comp.get("component_type", "").replace("_", " ").title(),
                "provider":      None,
                "summary":       "Identified via programmatic pattern matching.",
                "html_evidence": [],
                "rejection_reason": None,
            }

    return components


class AIAnalyzer:
    def __init__(self, event_queue: Optional[Queue] = None, job_id: Optional[str] = None):
        self.event_queue = event_queue
        self.job_id = job_id

    async def analyze_progressive(
        self,
        url: str,
        scrape_data: ScrapeResult,
        ai_mode: bool = False,
    ) -> AuthAnalysis:
        print(f"[Analyzer] Scout analysis completed (LLM disabled, skipped)")
        return await self._comprehensive_analysis(url, scrape_data, ai_mode=ai_mode)

    async def _comprehensive_analysis(
        self,
        url: str,
        scrape_data: ScrapeResult,
        ai_mode: bool = False,
    ) -> AuthAnalysis:
        print(f"[Analyzer] Starting {'AI-enhanced' if ai_mode else 'standard'} analysis for {url}")

        try:
            from app.services.html_extractor import (
                analyze_security,
                extract_auth_components,
                extract_auth_methods,
                extract_tech_stack,
            )

            print("[Analyzer] Extracting components programmatically...")

            all_components: List[Dict] = []
            all_methods:    List[Dict] = []

            print("[Analyzer] Extracting from initial page...")
            initial_components = extract_auth_components(scrape_data.initial_html)
            initial_methods    = extract_auth_methods(scrape_data.initial_html, initial_components)
            all_components.extend(initial_components)
            all_methods.extend(initial_methods)
            print(f"[Analyzer] Initial page: {len(initial_components)} components")

            if scrape_data.triggered_states:
                triggered_html = scrape_data.triggered_states[0].get("html_after")
                if triggered_html:
                    print("[Analyzer] Extracting from triggered page...")
                    trig_components = extract_auth_components(triggered_html)
                    trig_methods    = extract_auth_methods(triggered_html, trig_components)
                    all_components.extend(trig_components)
                    all_methods.extend(trig_methods)
                    print(f"[Analyzer] Triggered page: {len(trig_components)} components")

            # Deduplicate components
            seen_snippets: set = set()
            components: List[Dict] = []
            for comp in all_components:
                snippet = comp.get("html_snippet", "")
                if snippet not in seen_snippets:
                    seen_snippets.add(snippet)
                    components.append(comp)

            # Deduplicate methods
            seen_methods: set = set()
            methods: List[Dict] = []
            for method in all_methods:
                key = f"{method.get('method_type', '')}_{method.get('provider', '')}"
                if key not in seen_methods:
                    seen_methods.add(key)
                    methods.append(method)

            stack    = extract_tech_stack(scrape_data.initial_html)
            security = analyze_security(url, scrape_data.initial_html)

            print(f"[Analyzer] Found {len(components)} components, {len(methods)} methods")

            # Optional AI enrichment — single batched LLM call
            if ai_mode and components:
                print("[Analyzer] Running AI-enhanced per-component analysis...")
                components = await _ai_analyze_components(url, components, self.event_queue)
                print("[Analyzer] AI analysis complete")
            else:
                print("[Analyzer] AI mode off — programmatic extraction only")

            # Build auth flow summary
            if components:
                has_oauth  = any(c.get("component_type") == "oauth_button" for c in components)
                has_form   = any("form" in c.get("component_type", "") for c in components)
                flow_steps = ["User navigates to the login page"]
                if has_oauth:
                    flow_steps.append("Chooses a social / OAuth provider")
                if has_form:
                    flow_steps.append("Fills in credentials and submits")
                flow_steps.append("Redirected or authenticated")
                flow_type = "dedicated_page"
            else:
                flow_steps = ["No authentication flow detected"]
                flow_type  = "unknown"

            return AuthAnalysis(
                url=url,
                components_found=len(components) > 0,
                components=[AuthComponent(**c) for c in components],
                auth_methods=[AuthMethod(**m) for m in methods],
                auth_flow=AuthFlow(steps=flow_steps, flow_type=flow_type),
                detected_stack=TechStack(**stack),
                security=SecurityAnalysis(**security),
                overall_confidence=0.82 if ai_mode and components else (0.75 if components else 0.4),
                timestamp=datetime.now(),
            )

        except Exception as e:
            print(f"[Analyzer] Error: {e}")
            import traceback; traceback.print_exc()
            return self._fallback(url, scrape_data)

    def _fallback(self, url: str, scrape_data: ScrapeResult) -> AuthAnalysis:
        from app.services.html_extractor import (
            analyze_security, extract_auth_components,
            extract_auth_methods, extract_tech_stack,
        )
        components = extract_auth_components(scrape_data.initial_html)
        methods    = extract_auth_methods(scrape_data.initial_html, components)
        stack      = extract_tech_stack(scrape_data.initial_html)
        security   = analyze_security(url, scrape_data.initial_html)
        return AuthAnalysis(
            url=url,
            components_found=len(components) > 0,
            components=[AuthComponent(**c) for c in components],
            auth_methods=[AuthMethod(**m) for m in methods],
            auth_flow=AuthFlow(steps=["Analysis completed"], flow_type="unknown"),
            detected_stack=TechStack(**stack),
            security=SecurityAnalysis(**security),
            overall_confidence=0.6,
            timestamp=datetime.now(),
        )
