"""
Programmatic HTML extraction — finds all auth-related elements.
No LLM. Uses a tiered signal system:
  - Definitive signals  → element included immediately
  - Contextual signals  → included only when auth action word is also present
This keeps recall high (few misses) and precision high (few false positives).
"""
from bs4 import BeautifulSoup, Tag
from typing import List, Dict, Any, Optional
import re


# ---------------------------------------------------------------------------
# Provider definitions
# ---------------------------------------------------------------------------

# Each entry: provider key -> (display name, name tokens, OAuth-specific href patterns)
# href patterns are SPECIFIC OAuth paths — NOT just the domain.
OAUTH_PROVIDERS: Dict[str, Dict] = {
    "google": {
        "display": "Google",
        "tokens":  ["google"],
        "hrefs":   [
            r"accounts\.google\.com",
            r"/auth/google",
            r"/login/google",
            r"/oauth/google",
            r"gsi/client",
            r"google_oauth",
            r"provider=google",
            r"/sessions/social/google",   # GitHub
            r"users/auth/google",         # Devise / Rails
            r"oauth2/google",
        ],
    },
    "github": {
        "display": "GitHub",
        "tokens":  ["github"],
        "hrefs":   [
            r"github\.com/login/oauth",
            r"/auth/github",
            r"/users/auth/github",
            r"/login/github",
            r"/sessions/social/github",
            r"oauth2/github",
        ],
    },
    "facebook": {
        "display": "Facebook",
        "tokens":  ["facebook", "fb"],
        "hrefs":   [
            r"facebook\.com/v\d+/dialog/oauth",
            r"facebook\.com/login",
            r"/auth/facebook",
            r"/login/facebook",
            r"/sessions/social/facebook",
            r"users/auth/facebook",
        ],
    },
    "twitter": {
        "display": "Twitter / X",
        "tokens":  ["twitter", r"\bx\b"],
        "hrefs":   [
            r"twitter\.com/oauth",
            r"twitter\.com/i/oauth",
            r"/auth/twitter",
            r"/login/twitter",
            r"/sessions/social/twitter",
        ],
    },
    "microsoft": {
        "display": "Microsoft",
        "tokens":  ["microsoft"],
        "hrefs":   [
            r"login\.microsoftonline\.com",
            r"login\.live\.com",
            r"/auth/microsoft",
            r"/auth/azure",
            r"msal",
            r"/sessions/social/microsoft",
            r"users/auth/microsoft",
        ],
    },
    "apple": {
        "display": "Apple",
        "tokens":  ["apple"],
        "hrefs":   [
            r"appleid\.apple\.com",
            r"/auth/apple",
            r"/sign-in-with-apple",
            r"apple_oauth",
            r"provider=apple",
            r"/sessions/social/apple",    # GitHub
            r"users/auth/apple",
            r"oauth2/apple",
        ],
    },
    "linkedin": {
        "display": "LinkedIn",
        "tokens":  ["linkedin"],
        "hrefs":   [
            r"linkedin\.com/oauth",
            r"/auth/linkedin",
            r"/login/linkedin",
            r"/sessions/social/linkedin",
        ],
    },
    "discord": {
        "display": "Discord",
        "tokens":  ["discord"],
        "hrefs":   [
            r"discord\.com/oauth2",
            r"discord\.com/api/oauth2",
            r"/auth/discord",
            r"/sessions/social/discord",
        ],
    },
    "slack": {
        "display": "Slack",
        "tokens":  ["slack"],
        "hrefs":   [
            r"slack\.com/oauth",
            r"slack\.com/openid",
            r"/auth/slack",
            r"/sessions/social/slack",
        ],
    },
    "reddit": {
        "display": "Reddit",
        "tokens":  ["reddit"],
        "hrefs":   [
            r"reddit\.com/api/v1/authorize",
            r"/auth/reddit",
            r"/sessions/social/reddit",
        ],
    },
    "amazon": {
        "display": "Amazon",
        "tokens":  ["amazon"],
        "hrefs":   [
            r"amazon\.com/ap/oa",
            r"login\.amazon\.com",
            r"/auth/amazon",
        ],
    },
    "okta": {
        "display": "Okta",
        "tokens":  ["okta"],
        "hrefs":   [
            r"okta\.com/oauth2",
            r"\.okta\.com",
            r"/auth/okta",
        ],
    },
    "spotify": {
        "display": "Spotify",
        "tokens":  ["spotify"],
        "hrefs":   [
            r"accounts\.spotify\.com",
            r"/auth/spotify",
        ],
    },
    "twitch": {
        "display": "Twitch",
        "tokens":  ["twitch"],
        "hrefs":   [
            r"id\.twitch\.tv/oauth2",
            r"/auth/twitch",
        ],
    },
    "gitlab": {
        "display": "GitLab",
        "tokens":  ["gitlab"],
        "hrefs":   [
            r"gitlab\.com/oauth",
            r"/auth/gitlab",
            r"/users/auth/gitlab",
        ],
    },
    "bitbucket": {
        "display": "Bitbucket",
        "tokens":  ["bitbucket"],
        "hrefs":   [
            r"bitbucket\.org/site/oauth2",
            r"/auth/bitbucket",
        ],
    },
}

# Words that confirm auth intent on a button/link (second-pass filter)
AUTH_INTENT_WORDS = [
    "sign in", "signin", "sign-in", "log in", "login", "log-in",
    "continue with", "continue", "connect with", "connect",
    "authorize", "authenticate", "oauth", "auth",
    "continuing",    # data-disable-with="Continuing with Google..."
    "via", "using",  # "Login via Google", "Sign in using Apple"
]

# Regex: "Continue/Sign in/Log in/... with <Provider>"
# Captures the provider name so we can identify it even if not in our known list.
WITH_PROVIDER_RE = re.compile(
    r"\b(?:continue|sign[\s\-]?in|log[\s\-]?in|sign[\s\-]?up|log[\s\-]?up|"
    r"login|register|connect|link|use|proceed)\s+with\s+([A-Za-z][A-Za-z0-9\s\.\-]{1,30})",
    re.I,
)

# Phrases that are NOT providers — filters out "Continue with your email", etc.
NOT_A_PROVIDER = re.compile(
    r"^(your|an?\s|the\s|email|phone|password|otp|sms|code|username|account"
    r"|passkey|magic|link|us|me|this|that|more|less|all|one)",
    re.I,
)

# URL patterns that are definitively OAuth initiation endpoints
# (used to detect OAuth forms by their action attribute)
OAUTH_ACTION_PATTERN = re.compile(
    r"/sessions/social/|/users/auth/|/auth/[a-z]+$|/login/oauth|"
    r"/oauth2?/(?:authorize|callback|google|apple|github|facebook|microsoft|twitter|"
    r"linkedin|discord|slack|reddit|spotify|twitch|gitlab|bitbucket)|"
    r"accounts\.google\.com|appleid\.apple\.com|login\.microsoftonline\.com|"
    r"facebook\.com/v\d+/dialog/oauth|twitter\.com/oauth|discord\.com/oauth2",
    re.I,
)

# URL patterns for forms that are NOT login forms even though they contain /session
SOCIAL_INITIATE_PATTERN = re.compile(r"/sessions/social/|/users/auth/", re.I)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _elem_signals(elem: Tag) -> str:
    """
    Collect text signals from the element itself (NOT its parent form).
    Includes: visible text, key data-attrs, aria-label, img alt, child aria-labels.
    Deliberately excludes raw href to avoid matching support/docs links.
    """
    parts = [
        " ".join(elem.stripped_strings),
        " ".join(elem.get("class", [])),
        elem.get("data-social-service", ""),
        elem.get("data-provider", ""),
        elem.get("data-auth-provider", ""),
        elem.get("data-disable-with", ""),   # "Continuing with Google..."
        elem.get("aria-label", ""),
        elem.get("title", ""),
        " ".join(i.get("alt", "") for i in elem.find_all("img")),
        " ".join(c.get("aria-label", "") for c in elem.find_all(True)),
    ]
    return " ".join(p for p in parts if p).lower()


def _parent_form_action(elem: Tag) -> str:
    form = elem.find_parent("form")
    return (form.get("action", "") if form else "").lower()


def _elem_href(elem: Tag) -> str:
    return elem.get("href", "").lower()


def _has_auth_intent(signals: str, visible: str) -> bool:
    """Return True if the element text / signals suggest auth intent."""
    return any(w in signals for w in AUTH_INTENT_WORDS) or len(visible) <= 40


# ---------------------------------------------------------------------------
# Main extraction functions
# ---------------------------------------------------------------------------

def extract_auth_components(html: str) -> List[Dict[str, Any]]:
    soup = BeautifulSoup(html, "lxml")
    components: List[Dict[str, Any]] = []

    html_lower_debug = html.lower()
    provider_hits = [p for p in ["google", "apple", "github", "microsoft", "facebook"] if p in html_lower_debug]
    print(f"[Extractor] HTML size: {len(html):,} chars | providers in HTML: {provider_hits or 'none'}")

    # Non-text input types that should never trigger auth detection
    NON_TEXT_TYPES = {"checkbox", "radio", "hidden", "submit", "button",
                      "file", "image", "reset", "range", "color"}

    # Form actions / ids that are clearly not auth
    NON_AUTH_FORM = re.compile(
        r"feedback|search|comment|subscribe|newsletter|contact|report|survey|upload|checkout|payment|cart",
        re.I
    )

    # Patterns that explicitly indicate login vs signup in form action/id
    LOGIN_FORM_PATTERN  = re.compile(r"/login|/signin|/sign-in|/auth|/session|/sso|/saml", re.I)
    SIGNUP_FORM_PATTERN = re.compile(r"/signup|/sign-up|/register|/join|/create.?account|/new.?account", re.I)

    # ------------------------------------------------------------------
    # 1. Forms — classified as login or signup based on content + action
    # ------------------------------------------------------------------
    for form in soup.find_all("form"):
        action   = form.get("action", "")
        form_id  = form.get("id", "")
        form_cls = " ".join(form.get("class", []))
        context  = f"{action} {form_id} {form_cls}"

        # Skip social/OAuth initiation forms — handled in OAuth pass
        if OAUTH_ACTION_PATTERN.search(action):
            continue

        # Skip forms clearly unrelated to auth
        if NON_AUTH_FORM.search(context):
            continue

        has_pw = bool(form.find("input", {"type": "password"}))

        # username/login name — must be a real text input
        has_user = False
        for inp in form.find_all("input", attrs={"name": re.compile(r"^(user|username|login|email|account)$", re.I)}):
            if inp.get("type", "text").lower() not in NON_TEXT_TYPES:
                has_user = True
                break

        # Determine form type
        is_login_action  = bool(LOGIN_FORM_PATTERN.search(action))
        is_signup_action = bool(SIGNUP_FORM_PATTERN.search(action))

        # A form is a LOGIN form if:
        #   - it has a password field (strongest signal)
        #   - OR its action explicitly points to a login endpoint
        if has_pw or is_login_action:
            components.append({
                "html_snippet":   str(form)[:800],
                "component_type": "login_form",
                "purpose":        "Login / authentication form",
                "confidence":     0.97 if has_pw else 0.85,
            })
        # A form is a SIGNUP form if:
        #   - action points to signup endpoint AND it has an email/user input
        elif is_signup_action and (bool(form.find("input", {"type": "email"})) or has_user):
            components.append({
                "html_snippet":   str(form)[:800],
                "component_type": "signup_form",
                "purpose":        "Sign-up / registration form",
                "confidence":     0.85,
            })
    print(f"[Extractor]   login_forms: {sum(1 for c in components if c['component_type']=='login_form')}")

    # ------------------------------------------------------------------
    # 2. Password inputs (+ immediate container)
    # ------------------------------------------------------------------
    pw_seen: set = set()
    for inp in soup.find_all("input", {"type": "password"}):
        key = str(inp)
        if key in pw_seen:
            continue
        pw_seen.add(key)
        parent = inp.find_parent(["div", "form", "fieldset", "label"])
        components.append({
            "html_snippet":   str(parent)[:600] if parent else key,
            "component_type": "password_input",
            "purpose":        "Password input field",
            "confidence":     0.98,
        })
    print(f"[Extractor]   password_inputs: {len(pw_seen)}")

    # ------------------------------------------------------------------
    # 3. Email / username inputs
    # ------------------------------------------------------------------
    # Collect all auth-confirmed forms (login + signup) to use as context anchor
    auth_form_elems = set()
    for c in components:
        if c["component_type"] in ("login_form", "signup_form"):
            # Find the actual form element for this snippet
            for form in soup.find_all("form"):
                if str(form)[:200] == c["html_snippet"][:200]:
                    auth_form_elems.add(id(form))
                    break

    em_seen: set = set()
    for inp in (
        soup.find_all("input", {"type": "email"})
        + soup.find_all("input", attrs={"name":         re.compile(r"^(email|user|username|login|account|phone)$", re.I)})
        + soup.find_all("input", attrs={"id":           re.compile(r"^(email|user|username|login|account|phone)$", re.I)})
        + soup.find_all("input", attrs={"autocomplete": re.compile(r"^(email|username)$",                          re.I)})
    ):
        if inp.get("type", "text").lower() in NON_TEXT_TYPES:
            continue

        # Only include if this input is inside an auth-confirmed form,
        # adjacent to a password field, or the form action is an auth endpoint
        parent_form = inp.find_parent("form")
        if parent_form:
            form_action = parent_form.get("action", "")
            has_password_sibling = bool(parent_form.find("input", {"type": "password"}))
            is_auth_action = bool(LOGIN_FORM_PATTERN.search(form_action) or SIGNUP_FORM_PATTERN.search(form_action))
            if not (has_password_sibling or is_auth_action or id(parent_form) in auth_form_elems):
                continue  # email input in an unconfirmed form — skip
        else:
            continue  # standalone email input with no form — skip

        key = str(inp)
        if key in em_seen:
            continue
        em_seen.add(key)
        parent = inp.find_parent(["div", "form", "fieldset", "label"])
        name   = inp.get("name") or inp.get("id") or inp.get("type") or "field"
        components.append({
            "html_snippet":   str(parent)[:600] if parent else key,
            "component_type": "username_email_input",
            "purpose":        f"Email / Username input ({name})",
            "confidence":     0.92,
        })
    print(f"[Extractor]   email/username inputs: {len(em_seen)}")

    # ------------------------------------------------------------------
    # 4. OAuth / social login buttons — two-pass approach
    # ------------------------------------------------------------------
    # Pass A: Forms whose action URL is a known OAuth initiation endpoint.
    #   These are 100% definitive — the form action tells us exactly which
    #   provider and that it's OAuth. We grab the submit button (or the form).
    oauth_seen: set = set()

    for form in soup.find_all("form"):
        form_action = form.get("action", "")
        if not form_action or not OAUTH_ACTION_PATTERN.search(form_action):
            continue
        # Match to a provider
        matched_provider = None
        matched_info = None
        for provider_key, info in OAUTH_PROVIDERS.items():
            fa_lower = form_action.lower()
            if any(re.search(p, fa_lower) for p in info["hrefs"]) or \
               any(re.search(t, fa_lower) for t in info["tokens"]):
                matched_provider = provider_key
                matched_info = info
                break
        if not matched_info:
            continue

        # Use the submit button as the snippet if present; else the form itself
        btn = form.find("button") or form.find("input", {"type": "submit"})
        target = btn if btn else form
        key = str(target)[:300]
        if key in oauth_seen:
            continue
        oauth_seen.add(key)
        components.append({
            "html_snippet":   str(target)[:500],
            "component_type": "oauth_button",
            "purpose":        f"{matched_info['display']} OAuth / social login",
            "confidence":     0.97,
        })

    # Pass B: Standalone OAuth buttons/links not inside a dedicated OAuth form.
    #   Strategy (per user direction): first gather every element that contains
    #   a provider token anywhere (text, attrs, href, class), then filter to
    #   keep only those with clear auth intent. This catches JS-driven OAuth
    #   buttons, links with OAuth hrefs, and data-attribute-driven SSO buttons.
    candidates = (
        soup.find_all(["button", "a"])
        + soup.find_all(attrs={"role": "button"})
        + soup.find_all(attrs={"type": "submit"})
    )

    for elem in candidates:
        # Skip if already covered by Pass A
        if str(elem)[:300] in oauth_seen:
            continue

        signals = _elem_signals(elem)
        href    = _elem_href(elem)
        visible = " ".join(elem.stripped_strings).lower()
        parent_action = _parent_form_action(elem)

        for provider_key, info in OAUTH_PROVIDERS.items():
            tokens = info["tokens"]

            # Step 1 — Does this element mention the provider at all?
            token_in_signals = any(re.search(t, signals) for t in tokens)
            token_in_href    = href and any(re.search(p, href) for p in info["hrefs"])
            token_in_parent  = parent_action and any(re.search(p, parent_action) for p in info["hrefs"])

            if not (token_in_signals or token_in_href or token_in_parent):
                continue   # provider not mentioned at all — skip

            # Step 2 — Confirm auth intent (keep false positives low)
            # Accept if ANY of these hold:
            #  a) href is an OAuth-specific URL for this provider
            #  b) explicit data-social-service / data-provider / data-auth-provider attr
            #  c) provider token in short visible text WITH any auth intent word
            #  d) class contains provider token + social/auth keyword
            explicit_attr = any(
                re.search(t, elem.get(a, "").lower())
                for a in ("data-social-service", "data-provider", "data-auth-provider")
                for t in tokens
            )
            short_text_match = (
                any(re.search(t, visible) for t in tokens)
                and len(visible) <= 60
                and _has_auth_intent(signals, visible)
            )
            cls = " ".join(elem.get("class", [])).lower()
            class_match = (
                any(re.search(t, cls) for t in tokens)
                and any(w in cls for w in ["login", "signin", "auth", "oauth", "social", "sso", "btn"])
            )

            if not (token_in_href or explicit_attr or short_text_match or class_match):
                continue   # provider mentioned but no auth intent — skip (e.g. footer links)

            key = str(elem)[:300]
            if key in oauth_seen:
                break
            oauth_seen.add(key)
            components.append({
                "html_snippet":   str(elem)[:500],
                "component_type": "oauth_button",
                "purpose":        f"{info['display']} OAuth / social login",
                "confidence":     0.93,
            })
            break   # one provider per element

    # Pass C: "X with <Provider>" text pattern — catches any provider,
    # including unknown ones, as long as the button says the magic phrase.
    # Works by scanning ALL button/link visible text regardless of known tokens.
    # This is the deepest DOM scan: strips all nested children's text.
    with_candidates = (
        soup.find_all(["button", "a"])
        + soup.find_all(attrs={"role": "button"})
    )
    for elem in with_candidates:
        if str(elem)[:300] in oauth_seen:
            continue

        # Gather text from: visible text, data-disable-with, aria-label, title
        text_sources = [
            " ".join(elem.stripped_strings),   # recursive — gets all nested spans
            elem.get("data-disable-with", ""),  # "Continuing with Google..."
            elem.get("aria-label", ""),
            elem.get("title", ""),
        ]
        combined = " ".join(s for s in text_sources if s)

        match = WITH_PROVIDER_RE.search(combined)
        if not match:
            continue

        provider_name = match.group(1).strip()
        # Filter out non-provider words ("your email", "an account", etc.)
        if NOT_A_PROVIDER.match(provider_name):
            continue
        # Must be a short, single-or-two-word name (brands are concise)
        if len(provider_name.split()) > 3:
            continue

        # Try to match to a known provider for a nicer display name
        provider_display = provider_name.title()
        for provider_key, info in OAUTH_PROVIDERS.items():
            if any(re.search(t, provider_name.lower()) for t in info["tokens"]):
                provider_display = info["display"]
                break

        key = str(elem)[:300]
        oauth_seen.add(key)
        components.append({
            "html_snippet":   str(elem)[:500],
            "component_type": "oauth_button",
            "purpose":        f"{provider_display} OAuth / social login",
            "confidence":     0.88,
        })

    print(f"[Extractor]   oauth_buttons: {len(oauth_seen)}")

    # ------------------------------------------------------------------
    # 5. Login / signup / submit buttons — tight matching
    # ------------------------------------------------------------------
    LOGIN_KW  = {"log in", "login", "sign in", "signin", "sign-in", "log-in"}
    # Signup keywords kept tight — pure marketing CTAs ("get started", "join now") excluded
    SIGNUP_KW = {"sign up", "signup", "register", "create account", "create an account", "sign-up"}
    btn_seen: set = set()

    for elem in soup.find_all(["button", "a", "input"]):
        text  = elem.get_text(separator=" ", strip=True).lower()
        value = elem.get("value", "").lower()
        aria  = elem.get("aria-label", "").lower()

        # Use the shortest non-empty of text/aria as the label to match
        label = text if text else aria
        if len(label) > 60:
            continue

        is_login  = label in LOGIN_KW  or value in LOGIN_KW  or any(label == kw for kw in LOGIN_KW)
        is_signup = label in SIGNUP_KW or value in SIGNUP_KW

        # Partial match only for short labels
        if not is_login and len(label) <= 25:
            is_login = any(kw in label for kw in LOGIN_KW)
        if not is_signup and len(label) <= 30:
            is_signup = any(kw in label for kw in SIGNUP_KW)

        # Submit button inside a password-bearing form
        is_submit = (
            elem.get("type") == "submit"
            and bool(elem.find_parent("form") and
                     elem.find_parent("form").find("input", {"type": "password"}))
        )

        if not (is_login or is_signup or is_submit):
            continue

        key = str(elem)[:300]
        if key in btn_seen:
            continue
        btn_seen.add(key)

        if is_login:
            ctype, purpose = "login_button", "Login / sign-in button"
        elif is_signup:
            ctype, purpose = "signup_button", "Sign-up / register button"
        else:
            ctype, purpose = "submit_button", "Form submit (inside password form)"

        components.append({
            "html_snippet":   str(elem)[:400],
            "component_type": ctype,
            "purpose":        purpose,
            "confidence":     0.90 if (is_login or is_signup) else 0.75,
        })
    print(f"[Extractor]   login/signup buttons: {len(btn_seen)}")

    # ------------------------------------------------------------------
    # Deduplicate by first 150 chars of snippet
    # ------------------------------------------------------------------
    seen_final: set = set()
    unique: List[Dict[str, Any]] = []
    for comp in components:
        key = comp["html_snippet"][:150]
        if key not in seen_final:
            seen_final.add(key)
            unique.append(comp)

    print(f"[Extractor] Total unique auth components: {len(unique)}")
    return unique[:30]


# ---------------------------------------------------------------------------
# Auth method detection
# ---------------------------------------------------------------------------

def extract_auth_methods(html: str, components: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    if components is None:
        components = []

    comp_html  = "\n".join(c.get("html_snippet", "") for c in components).lower()
    html_lower = html.lower()
    methods:   List[Dict[str, Any]] = []

    # Email + password
    if "type=\"password\"" in html_lower or "type='password'" in html_lower:
        methods.append({
            "method_type": "email_password",
            "provider":    None,
            "detected_by": "Password input found on page",
        })

    # OAuth — only report if an actual oauth_button component was found for this provider.
    # Do NOT scan the full page HTML (too many false positives from nav/footer/docs links).
    for provider_key, info in OAUTH_PROVIDERS.items():
        tokens  = info["tokens"]
        in_comp = any(
            any(re.search(t, c.get("html_snippet", "").lower()) for t in tokens)
            for c in components
            if c.get("component_type") == "oauth_button"
        )
        if in_comp:
            methods.append({
                "method_type": "oauth",
                "provider":    info["display"],
                "detected_by": f"{info['display']} OAuth button found on page",
            })

    # SSO / SAML
    if re.search(r"\bsso\b|saml|single sign.on|enterprise login", comp_html):
        methods.append({
            "method_type": "sso",
            "provider":    None,
            "detected_by": "SSO / SAML element detected",
        })

    # Magic link / passwordless — require very specific phrases to avoid false positives
    if re.search(r"magic\s+link|passwordless\s+login|passwordless\s+sign|sign\s+in\s+with\s+email\s+link|send\s+(you\s+a|a)\s+sign.in\s+link", html_lower):
        methods.append({
            "method_type": "magic_link",
            "provider":    None,
            "detected_by": "Magic link / passwordless login indicator found",
        })

    # OTP / phone
    if re.search(r"\botp\b|one.time.pass|sms.code|phone.number|verification.code", html_lower):
        methods.append({
            "method_type": "otp_sms",
            "provider":    None,
            "detected_by": "OTP / SMS verification input found",
        })

    return methods


# ---------------------------------------------------------------------------
# Tech stack detection
# ---------------------------------------------------------------------------

def extract_tech_stack(html: str) -> Dict[str, Any]:
    html_lower = html.lower()
    evidence: List[str] = []

    framework = None
    for name, signals in [
        ("Next.js",   ["__next", "_next/static", "__nextjs_original_stack_frames"]),
        ("Nuxt.js",   ["__nuxt", "_nuxt/"]),
        ("React",     ["data-reactroot", "_reactfiber", "react.production.min.js",
                        "__react_devtools"]),
        ("Vue.js",    ["data-v-app", "__vue_app__", "vue.global.prod.js"]),
        ("Angular",   ["ng-version=", "ng-app=", "angular.min.js"]),
        ("Svelte",    ["__svelte_chunk", "svelte/internal"]),
        ("Remix",     ["__remixContext", "__remix_manifest"]),
        ("Ember.js",  ["ember.min.js", "data-ember-action"]),
    ]:
        if any(s in html_lower for s in signals):
            framework = name
            evidence.append(f"Framework: {name}")
            break

    auth_library = None
    for name, signals in [
        ("Auth0",         ["auth0.com/auth0-spa", "auth0.js", "cdn.auth0.com"]),
        ("Firebase Auth", ["firebase/auth", "firebaseapp.com", "initializeapp"]),
        ("Clerk",         ["clerk.dev", "clerk.com", "frontendapi.clerk"]),
        ("Supabase",      ["supabase.co", "supabase.js"]),
        ("NextAuth.js",   ["next-auth", "/api/auth/csrf", "/api/auth/session"]),
        ("AWS Cognito",   ["cognito", "amazoncognito.com", "aws-amplify"]),
        ("Okta",          ["okta.com/oauth2", "oktawidget", "okta-auth-js"]),
        ("Keycloak",      ["keycloak.js", "/auth/realms/"]),
        ("Azure AD",      ["login.microsoftonline.com", "msal-browser"]),
        ("WorkOS",        ["workos.com"]),
        ("Stytch",        ["stytch.com"]),
        ("Clerk",         ["clerk.dev"]),
        ("Descope",       ["descope.com"]),
    ]:
        if any(s in html_lower for s in signals):
            auth_library = name
            evidence.append(f"Auth library: {name}")
            break

    return {
        "framework":    framework,
        "auth_library": auth_library,
        "backend":      None,
        "confidence":   0.85 if (framework or auth_library) else 0.3,
        "evidence":     evidence,
    }


# ---------------------------------------------------------------------------
# Security analysis
# ---------------------------------------------------------------------------

def analyze_security(url: str, html: str) -> Dict[str, Any]:
    html_lower = html.lower()
    notes: List[str] = []
    score = 5.0

    https = url.startswith("https")
    if https:
        notes.append("HTTPS enabled")
        score += 2.0
    else:
        notes.append("WARNING: Not using HTTPS")
        score -= 2.0

    if re.search(r"\b2fa\b|two.factor|mfa|multi.factor", html_lower):
        notes.append("2FA / MFA available")
        score += 1.0

    if "passkey" in html_lower or "webauthn" in html_lower:
        notes.append("Passkey / WebAuthn support")
        score += 0.5

    if "recaptcha" in html_lower or "hcaptcha" in html_lower or "turnstile" in html_lower:
        notes.append("CAPTCHA / bot protection present")
        score += 0.5

    if "csrf" in html_lower or "authenticity_token" in html_lower or "csrfmiddlewaretoken" in html_lower:
        notes.append("CSRF protection detected")
        score += 0.5

    return {
        "https_enabled":         https,
        "password_requirements": None,
        "two_factor_available":  bool(re.search(r"\b2fa\b|two.factor|mfa", html_lower)),
        "security_notes":        notes,
        "score":                 round(min(10.0, max(0.0, score)), 1),
    }
