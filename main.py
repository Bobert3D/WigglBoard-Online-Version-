import os
import random
import httpx
import base64
import asyncio
import time as time_module
from urllib.parse import quote_plus, unquote_plus, urlparse
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from typing import List
from typing import List, Optional
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, Response

# 1. LOAD ENVIRONMENT VARIABLES
load_dotenv()

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "default_admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "default_password")

# 2. INITIALIZE APP WITH DOCS AND REDOCS ENABLED
app = FastAPI(
    title="Fetch 404 Engine",
    description="Y'alls fav dog pic(or gif) & quote API!",
    version="1.3.0",
    docs_url="/docs",
    redoc_url="/redocs"
)

# 3. DEFINE API SECURITY (HTTP Basic Auth)
security = HTTPBasic()

def authenticate_api(credentials: HTTPBasicCredentials = Depends(security)):
    """Validates incoming HTTP Basic Auth credentials."""
    if credentials.username != ADMIN_USERNAME or credentials.password != ADMIN_PASSWORD:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API credentials provided",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


USER_SUBMITTED_QUOTES = []
USER_FEEDBACK = []
BACKUP_DEV_QUOTES = [
    {"en": "Any fool can write code that a computer can understand. Good programmers write code that humans can understand.", "author": "Martin Fowler"},
    {"en": "First, solve the problem. Then, write the code.", "author": "John Johnson"},
    {"en": "To err is human, but to really foul things up you need a computer.", "author": "Paul R. Ehrlich"}
]
pythonic_quotes = {
    "debugging": "If debugging is the process of removing bugs, then programming must be the process of putting them in.",
    "documentation": "Documentation is like sex: when it is good, it is very, very good; and when it is bad, it is better than nothing.",
    "developers": "A Pythonista's life is just a series of try... except blocks until we die.",
    "coffee": "Programmer: A machine that turns coffee into code.",
    "future_self": "When I wrote this code, only God and I understood what I did. Now only God knows.",
    "temporary_fix": "Nothing is as permanent as a temporary solution that works."
}

class DogGeneratorResponse(BaseModel):
    image_element: str
    en: str
    author: str
    theme: str

class CustomQuoteInput(BaseModel):
    quote_text: str
    author_name: str

class FeedbackInput(BaseModel):
    username: str
    stars: int = Field(..., ge=1, le=5)
    comment: str


# === CORE REUSABLE LOGIC (Bypasses Auth internally, Fixes Fallback Image) ===
async def _get_dog_card_data() -> dict:
    """Shared core helper function to fetch dynamic dog media and tech quotes."""
    # FIXED: Replaced 'https://dog.ceo' site link with a direct image link fallback
    active_visual = "https://dog.ceo/api/breeds/image/random"
    selected_quote = random.choice(BACKUP_DEV_QUOTES)
    theme_source = "Coding Wisdom (Local Asset)"
    
    async with httpx.AsyncClient() as client:
        # 1. Fetch a dynamic external random dog media link
        try:
            dog_req = await client.get("https://random.dog/woof.json", timeout=4.0)
            if dog_req.status_code == 200:
                url_candidate = dog_req.json().get("url", "")
                if url_candidate:
                    active_visual = url_candidate
                    theme_source = "Live Doggo Gateway"
        except Exception:
            pass
        # 2. If random.dog did not return a usable media URL, try dog.ceo which
        # returns a JSON payload with a direct image URL in the `message` field.
        if not active_visual or active_visual.endswith('/woof.json'):
            try:
                dog_ceo = await client.get("https://dog.ceo/api/breeds/image/random", timeout=4.0)
                if dog_ceo.status_code == 200:
                    msg = dog_ceo.json().get("message", "")
                    if msg:
                        active_visual = msg
                        theme_source = "Dog CEO (Fallback)"
            except Exception:
                # leave the original fallback if all else fails
                pass
        # 2. Fetch live technical logic quote streams
        try:
            quote_req = await client.get("https://vercel.app", timeout=4.0)
            if quote_req.status_code == 200:
                data = quote_req.json()
                if "text" in data:
                    selected_quote = {"en": data.get("text"), "author": data.get("author", "Unknown")}
                else:
                    selected_quote = {"en": data.get("en"), "author": data.get("author", "Unknown")}
                theme_source = "Programming & Tech Logic"
        except Exception:
            pass

    return {
        "image_element": active_visual,
        "en": selected_quote.get("en", "Code works, but no statement returned."),
        "author": selected_quote.get("author", "Anonymous Coder"),
        "theme": theme_source
    }


# === Image proxy cache (in-memory) ===
IMAGE_CACHE_TTL = int(os.getenv("IMAGE_CACHE_TTL", "300"))  # seconds
IMAGE_CACHE_MAX_ENTRIES = int(os.getenv("IMAGE_CACHE_MAX_ENTRIES", "200"))
_image_cache: dict = {}
_image_cache_lock = asyncio.Lock()


# === ENDPOINT 1: Landing Page (Public) ===
@app.get("/", response_class=HTMLResponse, tags=["Interface"])
def home_page():
    return HTMLResponse(content="""
    <html>
    <head><title>Fetch 404</title></head>
    <body style="font-family:sans-serif; text-align:center; padding:50px; background:#77A789;">
    <h1>Fetch 404 Center!</h1>
    <p>Your interactive engine for cute doggos is up and fetching.</p>
    <a href="/view" style="padding:10px 20px; background:#A77795; color:#77A789; text-decoration:none; border-radius:5px; margin:5px; display:inline-block; font-weight:bold;">Open Card Viewer</a>
    </body>
    </html>
    """, status_code=200)


# === ENDPOINT 2: Data Generator API (Secured via Auth) ===
@app.get("/generate", response_model=DogGeneratorResponse, tags=["Core Services"], dependencies=[Depends(authenticate_api)])
async def generate_dog_card():
    return await _get_dog_card_data()


# === ENDPOINT 3: Frontend Layout Viewer (Public Page) ===
@app.get("/view", response_class=HTMLResponse, tags=["Interface"])
async def view_dog_card_visual():
        # Calls raw helper function to avoid browser login prompts for regular visitors
        data = await _get_dog_card_data()
        dog_media_url = data['image_element']
        quote_text = data['en']
        quote_author = data['author']
        current_theme = data['theme']

        # Use the proxy URL as the primary image source so the browser
        # requests `/image-proxy?url=...` from our server.
        proxy_src = f"/image-proxy?url={quote_plus(dog_media_url)}"

        # Prepare a base64 fallback (B) by attempting a short server-side fetch.
        # If successful we embed a small data URI which will be used if the
        # proxied request fails in the browser (onerror handler).
        data_uri: Optional[str] = None
        try:
                async with httpx.AsyncClient() as client:
                        img_resp = await client.get(dog_media_url, timeout=3.0)
                        if img_resp.status_code == 200:
                                content_type = img_resp.headers.get("content-type", "image/jpeg")
                                encoded = base64.b64encode(img_resp.content).decode("ascii")
                                data_uri = f"data:{content_type};base64,{encoded}"
        except Exception:
                data_uri = None

        # If no data_uri was produced, use a minimal transparent GIF as fallback.
        if not data_uri:
                transparent_gif_b64 = (
                        "R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw=="
                )
                data_uri = f"data:image/gif;base64,{transparent_gif_b64}"

        html_layout = """
        <html>
        <head><title>Fetch 404 - Card Viewer</title></head>
        <body style="font-family:sans-serif; text-align:center; padding:30px; background:#f5f5f5;">
            <h1>Fetch 404 - Card Viewer</h1>
            <div style="max-width:600px; margin:0 auto; background:#fff; padding:20px; box-shadow:0 2px 8px rgba(0,0,0,0.1);">
                <img id="dog-img" src="__PROXY_SRC__" alt="random dog" style="max-width:100%; height:auto; border-radius:8px;" onerror="this.onerror=null;this.src='__DATA_URI__';"/>
                <blockquote style="margin-top:15px; font-style:italic; color:#333;">"__QUOTE_TEXT__"</blockquote>
                <div style="text-align:right; font-weight:600;">— __QUOTE_AUTHOR__</div>
                <div style="margin-top:10px; font-size:12px; color:#666;">Theme: __CURRENT_THEME__</div>
            </div>

            <!-- Feedback Sidebar Toggle -->
            <button id="feedback-toggle" style="position:fixed; right:18px; bottom:18px; padding:12px 16px; background:#A77795; color:white; border:none; border-radius:8px; box-shadow:0 2px 6px rgba(0,0,0,0.15); cursor:pointer;">Feedback</button>

            <!-- Sidebar -->
            <div id="feedback-sidebar" style="position:fixed; right:0; top:0; height:100%; width:360px; max-width:90%; transform:translateX(110%); transition:transform .25s ease; background:#ffffff; box-shadow:-4px 0 20px rgba(0,0,0,0.12); padding:18px; overflow:auto; z-index:9999;">
                <h3 style="margin-top:0">Send Feedback / Report Error</h3>
                <p style="font-size:13px; color:#444">Send a short message, star rating, and paste any error trace below.</p>
                <label style="display:block; margin-top:8px">Username</label>
                <input id="fb-username" type="text" placeholder="your handle" style="width:100%; padding:8px; border:1px solid #ddd; border-radius:6px" />
                <label style="display:block; margin-top:8px">Stars</label>
                <select id="fb-stars" style="width:100%; padding:8px; border:1px solid #ddd; border-radius:6px">
                    <option value="5">5 — Excellent</option>
                    <option value="4">4 — Good</option>
                    <option value="3">3 — Okay</option>
                    <option value="2">2 — Poor</option>
                    <option value="1">1 — Broken</option>
                </select>
                <label style="display:block; margin-top:8px">Comment / Error trace</label>
                <textarea id="fb-comment" rows="6" placeholder="Paste error or add feedback" style="width:100%; padding:8px; border:1px solid #ddd; border-radius:6px"></textarea>
                <div style="display:flex; gap:8px; margin-top:10px">
                    <button id="fb-send" style="flex:1; padding:10px; background:#4CAF50; color:white; border:none; border-radius:6px; cursor:pointer">Send</button>
                    <button id="fb-clear" style="flex:1; padding:10px; background:#eee; color:#333; border:none; border-radius:6px; cursor:pointer">Clear</button>
                </div>
                <div id="fb-msg" style="margin-top:12px; font-size:13px; color:#333"></div>
            </div>

            <script>
                const toggle = document.getElementById('feedback-toggle');
                const sidebar = document.getElementById('feedback-sidebar');
                const sendBtn = document.getElementById('fb-send');
                const clearBtn = document.getElementById('fb-clear');
                const msgEl = document.getElementById('fb-msg');

                toggle.addEventListener('click', ()=>{
                    if(sidebar.style.transform && sidebar.style.transform.startsWith('translateX(0')){
                        sidebar.style.transform = 'translateX(110%)';
                    } else {
                        sidebar.style.transform = 'translateX(0%)';
                    }
                });

                clearBtn.addEventListener('click', ()=>{
                    document.getElementById('fb-username').value='';
                    document.getElementById('fb-comment').value='';
                    document.getElementById('fb-stars').value='5';
                    msgEl.textContent='';
                });

                sendBtn.addEventListener('click', async ()=>{
                    const payload = {
                        username: document.getElementById('fb-username').value || 'anonymous',
                        stars: parseInt(document.getElementById('fb-stars').value||5,10),
                        comment: document.getElementById('fb-comment').value || ''
                    };
                    try {
                        sendBtn.disabled=true; msgEl.textContent='Sending...';
                        const res = await fetch('/feedback', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(payload)});
                        if(res.ok){ msgEl.textContent='Thanks — feedback received.'; document.getElementById('fb-comment').value=''; }
                        else { msgEl.textContent='Failed to send feedback.'; }
                    } catch(e){ msgEl.textContent='Network error sending feedback.'; }
                    sendBtn.disabled=false;
                });

                // Optional: capture console errors and suggest to paste into the box.
                window.addEventListener('error', function(e){
                    const cur = document.getElementById('fb-comment');
                    cur.value = '[Auto-captured error] ' + e.message + '\n' + (e.filename||'') + ':' + (e.lineno||'') + '\n' + cur.value;
                    sidebar.style.transform = 'translateX(0%)';
                });
            </script>
        </body>
        </html>
        """

        html_layout = html_layout.replace('__PROXY_SRC__', proxy_src).replace('__DATA_URI__', data_uri).replace('__QUOTE_TEXT__', quote_text).replace('__QUOTE_AUTHOR__', quote_author).replace('__CURRENT_THEME__', current_theme)

        return HTMLResponse(content=html_layout, status_code=200)


@app.post('/feedback')
def submit_feedback(feedback: FeedbackInput):
    USER_FEEDBACK.append({
        'username': feedback.username,
        'stars': feedback.stars,
        'comment': feedback.comment,
        'received_at': time_module.time()
    })
    return {'status':'ok'}


@app.get('/admin/feedback', dependencies=[Depends(authenticate_api)])
def get_all_feedback():
    return USER_FEEDBACK


# === ENDPOINT 4: Custom Quotes Operations (Secured via Auth) ===
@app.get("/custom-quotes", response_model=List[dict], dependencies=[Depends(authenticate_api)])
def view_all_user_quotes():
    return USER_SUBMITTED_QUOTES

@app.post("/custom-quotes", dependencies=[Depends(authenticate_api)])
def add_custom_quote(user_input: CustomQuoteInput):
    USER_SUBMITTED_QUOTES.append({"en": user_input.quote_text, "author": user_input.author_name})
    return {"status": "Success"}


# === IMAGE PROXY ===
@app.get("/image-proxy")
async def image_proxy(url: str):
    """Proxy an external image URL through the server.

    Usage: `/image-proxy?url=<encoded image url>`
    """
    # Basic validation
    try:
        raw_url = unquote_plus(url)
    except Exception:
        raw_url = url

    parsed = urlparse(raw_url)
    if parsed.scheme not in ("http", "https"):
        return Response(status_code=400, content=b"Invalid URL scheme")

    # Check cache first
    now = time_module.time()
    async with _image_cache_lock:
        entry = _image_cache.get(raw_url)
        if entry and entry["expiry"] > now:
            # refresh last_access
            entry["last_access"] = now
            return Response(content=entry["content"], media_type=entry["content_type"])

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(raw_url, timeout=10.0)
            if resp.status_code != 200:
                return Response(status_code=502, content=b"Upstream fetch failed")
            content_type = resp.headers.get("content-type", "application/octet-stream")
            content = resp.content

            # Store in cache
            expiry = now + IMAGE_CACHE_TTL
            cache_entry = {"content": content, "content_type": content_type, "expiry": expiry, "last_access": now, "inserted": now}
            async with _image_cache_lock:
                _image_cache[raw_url] = cache_entry
                # Evict if over limit (simple oldest-inserted eviction)
                if len(_image_cache) > IMAGE_CACHE_MAX_ENTRIES:
                    # find oldest inserted
                    oldest = min(_image_cache.items(), key=lambda kv: kv[1].get("inserted", now))[0]
                    _image_cache.pop(oldest, None)

            return Response(content=content, media_type=content_type)
    except Exception:
        return Response(status_code=502, content=b"Upstream fetch error")

