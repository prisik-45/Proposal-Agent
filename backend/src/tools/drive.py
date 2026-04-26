from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from src.config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_CLIENT_SECRET_FILE,
    GOOGLE_DRIVE_FOLDER_ID,
    GOOGLE_OAUTH_HOST,
    GOOGLE_OAUTH_PORT,
    GOOGLE_OAUTH_TOKEN_FILE,
)

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def _flow_from_env_or_file() -> InstalledAppFlow:
    if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
        local_redirect = f"http://{GOOGLE_OAUTH_HOST}:{GOOGLE_OAUTH_PORT}/"
        local_redirect_127 = f"http://127.0.0.1:{GOOGLE_OAUTH_PORT}/"
        client_config = {
            "installed": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [local_redirect, local_redirect_127],
            }
        }
        return InstalledAppFlow.from_client_config(client_config, SCOPES)

    secret_path = Path(GOOGLE_CLIENT_SECRET_FILE)
    if not secret_path.exists():
        raise FileNotFoundError(
            "Google OAuth credentials missing. Set GOOGLE_CLIENT_ID and "
            "GOOGLE_CLIENT_SECRET in .env or provide GOOGLE_CLIENT_SECRET_FILE."
        )
    return InstalledAppFlow.from_client_secrets_file(str(secret_path), SCOPES)


def _get_credentials() -> Credentials:
    creds = None
    token_path = Path(GOOGLE_OAUTH_TOKEN_FILE)

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            import os
            # Vercel bypass: Do not try to pop up a browser auth flow in serverless.
            if "VERCEL" in os.environ or os.environ.get("VERCEL_ENV"):
                raise RuntimeError("Google Drive Token expired. Cannot re-auth via browser on serverless.")
            
            flow = _flow_from_env_or_file()
            creds = flow.run_local_server(host=GOOGLE_OAUTH_HOST, port=GOOGLE_OAUTH_PORT)

        # In serverless, writing to arbitrary files is blocked, wrap in try/except or catch Vercel config
        try:
            token_path.write_text(creds.to_json(), encoding="utf-8")
        except OSError:
            pass # Ignore read-only file system on VERCEL

    return creds


def upload_pdf_public(pdf_path: str) -> tuple[str, str]:
    creds = _get_credentials()
    service = build("drive", "v3", credentials=creds)

    file_metadata = {"name": Path(pdf_path).name}
    if GOOGLE_DRIVE_FOLDER_ID:
        file_metadata["parents"] = [GOOGLE_DRIVE_FOLDER_ID]

    media = MediaFileUpload(pdf_path, mimetype="application/pdf")
    created = (
        service.files()
        .create(body=file_metadata, media_body=media, fields="id, name")
        .execute()
    )
    file_id = created["id"]

    service.permissions().create(
        fileId=file_id,
        body={"type": "anyone", "role": "reader"},
    ).execute()

    public_link = f"https://drive.google.com/file/d/{file_id}/view"
    return file_id, public_link
