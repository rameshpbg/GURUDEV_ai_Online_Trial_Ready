"""GURUDEV.ai — temporary HTTPS cloud deployment with required HTTP Basic authentication.

NOTE: Appropriate for test data only; ephemeral storage, no persistent backup,
no research data confidentiality assurance or multi-user isolation.
"""
from __future__ import annotations
import base64
import os
import secrets
from fastapi import Request
from fastapi.responses import PlainTextResponse, JSONResponse
from gurudev_ai.companion.server import create_app
from gurudev_ai.companion import store

app = create_app()

@app.middleware('http')
async def protect_cloud(request: Request, call_next):
    # Required credentials are *never* taken from client requests or stored in source.
    if request.url.path == '/health':
        return await call_next(request)
    username = os.environ.get('GURUDEV_ONLINE_USER', '')
    password = os.environ.get('GURUDEV_ONLINE_PASSWORD', '')
    if not username or not password or len(password) < 12:
        return PlainTextResponse('GURUDEV.ai configuration error: add cloud credentials in the host dashboard.', status_code=503)
    token = request.headers.get('authorization','')
    verified = False
    if token.startswith('Basic '):
        try:
            raw = base64.b64decode(token[6:], validate=True).decode('utf-8')
            user, provided_password = raw.split(':', 1)
            verified = secrets.compare_digest(user, username) and secrets.compare_digest(provided_password,password)
        except (ValueError, UnicodeDecodeError, IndexError):
            verified = False
    if not verified:
        return PlainTextResponse('Authentication required',status_code=401,headers={'WWW-Authenticate':'Basic realm="GURUDEV.ai Private Research Preview"'})
    response = await call_next(request)
    response.headers['Cache-Control'] = 'no-store'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['Referrer-Policy'] = 'no-referrer'
    response.headers['X-Frame-Options'] = 'DENY'
    return response

@app.get('/health')
def health():
    # No user/research data in public health response.
    return {'status':'ok','product':'GURUDEV.ai'}

@app.get('/api/backup')
def backup(project: str='Rice'):
    if not 1 <= len(project) <= 100:
        return JSONResponse({'error':'Invalid project name'}, status_code=422)
    with store.connect() as conn:
        return {'format':'GURUDEV.ai cloud trial backup v1', 'project':project,
                'tasks':store.list_tasks(conn,project,limit=10000),
                'observations':store.list_observations(conn,project,limit=10000)}
