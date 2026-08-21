from __future__ import annotations

import os
import shutil
import sys
import tempfile
from pathlib import Path

import vertexai
from google.cloud.aiplatform_v1.types.env_var import SecretRef
from vertexai import agent_engines


PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "sherpa-20260813")
LOCATION = os.getenv("SHERPA_AGENT_ENGINE_LOCATION", "europe-west1")
STAGING_BUCKET = os.environ["SHERPA_GCS_BUCKET"]
RELAY_URL = os.environ["SHERPA_REMOTE_TOOL_URL"].rstrip("/")
SERVICE_ACCOUNT = os.environ["SHERPA_AGENT_SERVICE_ACCOUNT"]
RESOURCE_NAME = os.getenv("SHERPA_AGENT_ENGINE_RESOURCE", "").strip()
ROOT = Path(__file__).resolve().parents[1]

os.environ["SHERPA_REMOTE_TOOL_URL"] = RELAY_URL
os.environ.setdefault("SHERPA_INTERNAL_SECRET", "resolved-by-secret-manager")
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

from backend.agents.sherpa_agent import sherpa_app


vertexai.init(
    project=PROJECT,
    location=LOCATION,
    staging_bucket=f"gs://{STAGING_BUCKET}",
    api_transport="rest",
)
application = agent_engines.AdkApp(
    agent=sherpa_app.root_agent,
    app_name="sherpa",
    enable_tracing=True,
)
deploy = agent_engines.update if RESOURCE_NAME else agent_engines.create
args = (RESOURCE_NAME,) if RESOURCE_NAME else (application,)
kwargs = {
    "display_name": "Sherpa Agent",
    "description": "Sherpa ADK task execution agent with device-local tools",
    "requirements": str(ROOT / "backend" / "requirements.txt"),
    "env_vars": {
        "SHERPA_REMOTE_TOOL_URL": RELAY_URL,
        "SHERPA_INTERNAL_SECRET": SecretRef(
            secret="sherpa-internal-secret",
            version="latest",
        ),
        "SHERPA_INSTALLATION_ID": "default",
        "SHERPA_MODEL_LOCATION": "global",
        "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
    },
    "service_account": SERVICE_ACCOUNT,
    "min_instances": 1,
    "max_instances": 2,
    "container_concurrency": 4,
    "resource_limits": {"cpu": "2", "memory": "4Gi"},
}
if RESOURCE_NAME:
    kwargs["agent_engine"] = application
with tempfile.TemporaryDirectory(prefix="sherpa-agent-engine-") as build_dir:
    package_root = Path(build_dir)
    shutil.copytree(
        ROOT / "backend",
        package_root / "backend",
        ignore=shutil.ignore_patterns(
            ".venv",
            "venv",
            "__pycache__",
            "*.pyc",
            ".env",
            ".env.*",
            "storage",
        ),
    )
    os.chdir(package_root)
    kwargs["extra_packages"] = ["backend"]
    try:
        remote = deploy(*args, **kwargs)
        print(remote.resource_name)
    except Exception as error:
        if "effectiveIdentity" not in str(error):
            raise
        if RESOURCE_NAME:
            print(RESOURCE_NAME)
        else:
            matches = list(agent_engines.list(filter='display_name="Sherpa Agent"'))
            if not matches:
                raise
            print(max(matches, key=lambda item: item.update_time).resource_name)
