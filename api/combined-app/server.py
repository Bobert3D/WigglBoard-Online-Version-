import time
from fastapi import status
from fastapi.responses import JSONResponse
# Import your untouched app directly from main.py
from main import app 

client_request_history = {}

@app.middleware("http")
async def proxy_rate_limiter(request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    current_time = time.time()

    # Clear old timestamps (sliding window)
    if client_ip in client_request_history:
        client_request_history[client_ip] = [
            ts for ts in client_request_history[client_ip] if ts > current_time - 60
        ]
    else:
        client_request_history[client_ip] = []

    # Enforce limit (60 requests per minute)
    if len(client_request_history[client_ip]) >= 60:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Too many requests from this IP."}
        )

    client_request_history[client_ip].append(current_time)
    return await call_next(request)
