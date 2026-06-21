"""
Thin wrapper around the DocuMind FastAPI backend.
Mirrors the original frontend/src/utils/api.js, but using `requests`
instead of `fetch`.
"""
import os
import requests

BASE_URL = os.environ.get("DOCUMIND_API_URL", "http://localhost:8000")


class ApiError(Exception):
    """Raised when the backend returns a non-2xx response."""
    pass


def _headers(token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _handle(res: requests.Response):
    try:
        data = res.json() if res.content else {}
    except ValueError:
        data = {}
    if not res.ok:
        raise ApiError(data.get("detail", f"Request failed ({res.status_code})"))
    return data


# ---- Auth ----------------------------------------------------------------

def register(email: str, username: str, password: str) -> dict:
    res = requests.post(
        f"{BASE_URL}/auth/register",
        json={"email": email, "username": username, "password": password},
        headers=_headers(),
    )
    return _handle(res)


def login(email: str, password: str) -> dict:
    res = requests.post(
        f"{BASE_URL}/auth/login",
        json={"email": email, "password": password},
        headers=_headers(),
    )
    return _handle(res)


# ---- Documents -------------------------------------------------------------

def list_documents(token: str) -> list:
    res = requests.get(f"{BASE_URL}/documents/", headers=_headers(token))
    return _handle(res)


def upload_document(file, token: str) -> dict:
    """`file` is a Streamlit UploadedFile object."""
    files = {"file": (file.name, file.getvalue(), file.type)}
    res = requests.post(
        f"{BASE_URL}/documents/upload",
        files=files,
        headers={"Authorization": f"Bearer {token}"},
    )
    return _handle(res)


def delete_document(doc_id: int, token: str) -> None:
    res = requests.delete(f"{BASE_URL}/documents/{doc_id}", headers=_headers(token))
    if not res.ok:
        _handle(res)


# ---- Chat -------------------------------------------------------------------

def query(question: str, token: str) -> dict:
    res = requests.post(
        f"{BASE_URL}/chat/query",
        json={"question": question},
        headers=_headers(token),
    )
    return _handle(res)


def get_history(token: str) -> list:
    res = requests.get(f"{BASE_URL}/chat/history", headers=_headers(token))
    return _handle(res)


def clear_history(token: str) -> None:
    res = requests.delete(f"{BASE_URL}/chat/history", headers=_headers(token))
    if not res.ok:
        _handle(res)
