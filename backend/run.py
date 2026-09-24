"""
FarmerAssist Backend Server Entry Point — the same command everywhere: `python run.py`

Local (ENVIRONMENT=development): 127.0.0.1:8000 with auto-reload.
Hosting (ENVIRONMENT=production, Render / Railway set PORT): binds 0.0.0.0:$PORT, one worker (fits 512 MB),
trusts the platform proxy's X-Forwarded-* headers. Configured here in Python so no shell quoting is involved.
"""
import os

import uvicorn

if __name__ == "__main__":
    production = os.getenv("ENVIRONMENT", "development") == "production"
    uvicorn.run(
        "app.main:app",
        host=os.getenv("HOST") or ("0.0.0.0" if production else "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        reload=not production,
        workers=1,
        proxy_headers=production,
        forwarded_allow_ips="*" if production else None,
        log_level="info",
    )
