# Auth Analyzer

**AI-powered authentication component scanner.** Paste any website URL, and Auth Analyzer uses a real cloud browser to load the page, extracts every login/auth-related component (forms, OAuth buttons, SSO links, passkeys, password inputs), and optionally runs a Groq AI pass to explain each one and filter out false positives.

---

## What It Does

| Feature | Detail |
|---|---|
| **Cloud scraping** | Browserless.io renders the full page with JavaScript before extraction |
| **Component detection** | Finds login forms, signup forms, OAuth buttons (Google, Apple, GitHub, etc.), password inputs, email inputs, SSO, passkeys |
| **AI Enhanced mode** | Groq (Llama 3.3 70B) reviews each component, explains it in depth with 3 HTML-level evidence points, and filters false positives |
| **Rejected components** | Components flagged by AI as false positives appear in a separate collapsible section with reasons |
| **Tech stack detection** | Identifies frontend frameworks (Next.js, React, Vue…) and auth libraries (Auth0, Firebase, Clerk…) |
| **Security analysis** | HTTPS, 2FA/MFA, CSRF, CAPTCHA, passkey support |
| **Download** | Export all components as a styled HTML file or full JSON report |

---

## Using the App

### Home Page

1. **Enter a URL** in the input box — e.g. `https://github.com/login`
2. **Quick examples** — click any of the 5 preset sites (GitLab, GitHub, WordPress, Notion, Shopify) to auto-fill the URL
3. **AI Enhanced toggle** — on by default. Turn it OFF for a faster ~10s programmatic-only scan. Turn it ON to get:
   - Per-component AI explanation
   - 3 HTML-specific evidence points per component
   - False positive filtering with rejected component reasons
4. Click **Analyze** — you'll be taken to the results page

### Results Page

**Left panel — Analysis Progress**
- Live step-by-step log of what's happening (browser launch → scraping → AI review → done)
- Each step shows a pulsing dot while active, green checkmark when complete

**Right panel — Results tabs:**

| Tab | What's inside |
|---|---|
| **Components** | All detected auth components with HTML snippets. Click Expand/Collapse on any card to see full HTML. AI Enhanced cards show category, provider, summary, and 3 HTML evidence points. |
| **Overview** | Component count, auth methods summary, security score |
| **Security** | Score /10, HTTPS status, 2FA detection, security notes |

**Rejected Components section** (AI Enhanced mode only)
- Appears below the component list
- Shows components the pattern matcher detected but AI rejected as false positives
- Each card shows the HTML snippet and AI's reason for rejection

**Download buttons (top right):**
- **Download HTML** — styled HTML file with all components, AI explanations, and rejected section
- **Download JSON** — full raw analysis as JSON

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 14, TypeScript, Tailwind CSS |
| Backend | FastAPI (Python 3.12), Uvicorn |
| Scraping | Browserless.io (cloud headless Chrome) |
| HTML parsing | BeautifulSoup4 + lxml |
| AI | Groq API — Llama 3.3 70B (falls back to Gemini, then OpenAI) |
| LLM framework | LangChain |

---

## Setup

### Prerequisites

- Python 3.10+
- Node.js 18+
- A [Browserless.io](https://browserless.io) token (free tier available)
- A [Groq](https://console.groq.com) API key (free)

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/auth-analyzer.git
cd auth-analyzer
```

### 2. Backend setup

```bash
cd backend

# Create virtual environment
python -m venv venv

# Activate (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure environment variables

Copy the sample env file:

```bash
cp .env.example .env
```

Edit `.env` with your keys (see [API Keys](#api-keys) section below).

### 4. Frontend setup

```bash
cd ../frontend
npm install
```

Create a `.env.local` file:

```bash
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
```

### 5. Run locally

**Terminal 1 — Backend:**
```bash
cd backend
.\venv\Scripts\uvicorn.exe app.main:app --host 0.0.0.0 --port 8000 --reload
# Mac/Linux:
# uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

---

## Environment Variables

### `backend/.env`

```env
# Required — Browserless.io (cloud browser for scraping)
# Get free token at https://browserless.io
BROWSERLESS_TOKEN=your_browserless_token_here

# AI (choose one — Groq is recommended, free)
# Groq: https://console.groq.com
GROQ_API_KEY=gsk_your_groq_key_here

# Fallback AI options (optional)
GOOGLE_API_KEY=your_google_gemini_key_here
# OPENAI_API_KEY=sk-your_openai_key_here

ENVIRONMENT=development
LANGCHAIN_TRACING_V2=false
```

**AI key priority:** Groq → Gemini → OpenAI. Set only the one you want to use.

### `frontend/.env.local`

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
```

In production, set this to your deployed backend URL.

---

## API Keys

### Browserless.io (required for scraping)
1. Go to [browserless.io](https://browserless.io)
2. Sign up for a free account
3. Copy your API token from the dashboard
4. Set as `BROWSERLESS_TOKEN` in `.env`

### Groq (recommended for AI mode — free)
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up (free, no credit card)
3. Create an API key
4. Set as `GROQ_API_KEY` in `.env`
5. Free tier includes Llama 3.3 70B with generous daily limits

### Google Gemini (fallback — optional)
1. Go to [aistudio.google.com](https://aistudio.google.com)
2. Create an API key
3. Set as `GOOGLE_API_KEY` in `.env`

---

## Deployment

### Frontend → Vercel (free)

1. Push this repo to GitHub
2. Go to [vercel.com](https://vercel.com) → Import repository
3. Set **Root Directory** to `auth-analyzer/frontend`
4. Add environment variable:
   ```
   NEXT_PUBLIC_API_URL=https://your-railway-backend.up.railway.app
   ```
5. Deploy

### Backend → Railway (free $5/month credit)

1. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
2. Set **Root Directory** to `auth-analyzer/backend`
3. Add all environment variables from your `.env` file
4. Railway auto-detects Python and uses the `Procfile`
5. Copy the generated URL and update Vercel's `NEXT_PUBLIC_API_URL`

---

## Project Structure

```
auth-analyzer/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, endpoints, background tasks
│   │   ├── config.py                # Settings (API keys, model selection)
│   │   ├── models.py                # Pydantic models
│   │   └── services/
│   │       ├── analyzer.py          # AI analysis orchestration
│   │       ├── browserless_scraper.py  # Cloud browser scraping
│   │       ├── html_extractor.py    # Pattern-based auth component extraction
│   │       └── job_manager.py       # In-memory job state management
│   ├── requirements.txt
│   ├── Procfile                     # For Railway deployment
│   └── .env                        # Your local secrets (not committed)
│
└── frontend/
    ├── app/
    │   ├── page.tsx                 # Home page (URL input, examples, toggle)
    │   └── results/[jobId]/page.tsx # Results page (progress + analysis)
    ├── components/
    │   └── ResultsDisplay.tsx       # Analysis results tabs and component cards
    └── .env.local                   # Frontend env (not committed)
```

---

## How Component Detection Works

Detection happens in two passes:

**Pass 1 — Programmatic (always runs)**
Uses pattern matching on the rendered HTML:
- Login/signup forms identified by `action` URL patterns and password field presence
- OAuth buttons detected via parent form `action` URLs (`/sessions/social/google/initiate`), provider tokens in element signals, and `"Continue with X"` text patterns
- Password inputs, email/username inputs filtered by auth form context
- SSO, passkey, magic link detection via regex patterns

**Pass 2 — AI Filtering (AI Enhanced mode only)**
All detected components are sent to Groq in a single batched prompt. The AI:
1. Filters out false positives (newsletter forms, footer links, search bars, etc.)
2. For accepted components: provides category, provider, summary, and 3 HTML-specific evidence points
3. For rejected components: explains why with citations to specific HTML attributes

---

## License

MIT
