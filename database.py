from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import streamlit as st
from supabase import Client, create_client


TABLE_NAME = "color_us_invites"


class SupabaseNotConfigured(RuntimeError):
    pass


def get_client() -> Client:
    url = st.secrets.get("SUPABASE_URL")
    key = st.secrets.get("SUPABASE_ANON_KEY")
    if not url or not key:
        raise SupabaseNotConfigured("Supabase secrets are missing.")
    return create_client(url, key)


def get_bucket_name() -> str:
    return st.secrets.get("SUPABASE_BUCKET", "color-us-photos")


def create_invite(image_bytes: bytes, a_params: dict[str, int]) -> str:
    client = get_client()
    token = uuid4().hex
    image_path = f"invites/{token}/original.jpg"

    client.storage.from_(get_bucket_name()).upload(
        image_path,
        image_bytes,
        file_options={"content-type": "image/jpeg", "upsert": "false"},
    )

    payload = {
        "token": token,
        "image_path": image_path,
        "a_temperature": a_params["temperature"],
        "a_saturation": a_params["saturation"],
        "a_brightness": a_params["brightness"],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    client.table(TABLE_NAME).insert(payload).execute()
    return token


def get_invite(token: str) -> dict[str, Any] | None:
    client = get_client()
    result = client.table(TABLE_NAME).select("*").eq("token", token).limit(1).execute()
    if not result.data:
        return None
    return result.data[0]


def download_original(image_path: str) -> bytes:
    client = get_client()
    data = client.storage.from_(get_bucket_name()).download(image_path)
    if isinstance(data, bytes):
        return data
    return bytes(data)


def app_base_url() -> str:
    return st.secrets.get("APP_BASE_URL", "http://localhost:8501").rstrip("/")
