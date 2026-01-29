"""Tests for API Design Guard — real Python files, no mocking."""

from pathlib import Path

from vibesrails.guards_v2.api_design import APIDesignGuard


def _guard():
    return APIDesignGuard()


def _write_and_scan(tmp_path: Path, code: str, filename: str = "api.py"):
    f = tmp_path / filename
    f.write_text(code)
    return _guard().scan(tmp_path)


# ── No input validation (type hints) ────────────────────


def test_route_without_type_hints():
    code = '''
from fastapi import FastAPI
app = FastAPI()

@app.get("/users")
def get_users(limit, offset):
    return []
'''
    issues = _guard().scan_file(Path("api.py"), code)
    assert any("type hints" in i.message for i in issues)


def test_route_with_type_hints_clean():
    code = '''
from fastapi import FastAPI
app = FastAPI()

@app.get("/v1/users")
def get_users(limit: int, offset: int = 0):
    try:
        return []
    except Exception:
        raise
'''
    issues = _guard().scan_file(Path("api.py"), code)
    assert not any("type hints" in i.message for i in issues)


def test_route_no_params_clean():
    code = '''
from fastapi import FastAPI
app = FastAPI()

@app.get("/v1/health")
def health():
    try:
        return {"status": "ok"}
    except Exception:
        raise
'''
    issues = _guard().scan_file(Path("api.py"), code)
    assert not any("type hints" in i.message for i in issues)


# ── No error handling ────────────────────────────────────


def test_route_without_error_handling():
    code = '''
from fastapi import FastAPI
app = FastAPI()

@app.get("/items")
def get_items(q: str):
    return {"q": q}
'''
    issues = _guard().scan_file(Path("api.py"), code)
    assert any("error handling" in i.message for i in issues)


def test_route_with_try_except_clean():
    code = '''
from fastapi import FastAPI
app = FastAPI()

@app.get("/v1/items")
def get_items(q: str):
    try:
        return {"q": q}
    except ValueError:
        raise
'''
    issues = _guard().scan_file(Path("api.py"), code)
    assert not any("error handling" in i.message for i in issues)


def test_route_with_raise_clean():
    code = '''
from fastapi import FastAPI
from fastapi import HTTPException
app = FastAPI()

@app.get("/v1/items")
def get_items(q: str):
    if not q:
        raise HTTPException(status_code=400)
    return {"q": q}
'''
    issues = _guard().scan_file(Path("api.py"), code)
    assert not any("error handling" in i.message for i in issues)


# ── CORS wildcard ────────────────────────────────────────


def test_cors_wildcard_blocked():
    code = '''
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"])
'''
    issues = _guard().scan_file(Path("api.py"), code)
    assert any("CORS" in i.message for i in issues)


def test_cors_specific_origin_clean():
    code = '''
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["https://example.com"])
'''
    issues = _guard().scan_file(Path("api.py"), code)
    assert not any("CORS" in i.message for i in issues)


# ── API versioning ───────────────────────────────────────


def test_route_without_versioning():
    code = '''
from fastapi import FastAPI
app = FastAPI()

@app.get("/users")
def get_users(limit: int = 10):
    try:
        return []
    except Exception:
        raise
'''
    issues = _guard().scan_file(Path("api.py"), code)
    assert any("version prefix" in i.message for i in issues)


def test_route_with_v1_prefix_clean():
    code = '''
from fastapi import FastAPI
app = FastAPI()

@app.get("/v1/users")
def get_users(limit: int = 10):
    try:
        return []
    except Exception:
        raise
'''
    issues = _guard().scan_file(Path("api.py"), code)
    assert not any("version prefix" in i.message for i in issues)


def test_route_with_v2_prefix_clean():
    code = '''
from fastapi import FastAPI
app = FastAPI()

@app.get("/v2/items")
def get_items(q: str):
    try:
        return []
    except Exception:
        raise
'''
    issues = _guard().scan_file(Path("api.py"), code)
    assert not any("version prefix" in i.message for i in issues)


# ── Mixed naming conventions ─────────────────────────────


def test_mixed_naming_detected():
    code = '''
from flask import Flask
app = Flask(__name__)

user_name = "test"
userName = "test"

@app.get("/v1/mix")
def get_mix(q: str):
    try:
        return {}
    except Exception:
        raise
'''
    issues = _guard().scan_file(Path("api.py"), code)
    assert any("Mixed naming" in i.message for i in issues)


def test_consistent_snake_case_clean():
    code = '''
from flask import Flask
app = Flask(__name__)

user_name = "test"
other_var = "test"
'''
    issues = _guard().scan_file(Path("api.py"), code)
    assert not any("Mixed naming" in i.message for i in issues)


# ── No explicit status code ──────────────────────────────


def test_no_status_code_warned():
    code = '''
from fastapi import FastAPI
app = FastAPI()

@app.post("/users")
def create_user(name: str):
    try:
        return {"name": name}
    except Exception:
        raise
'''
    issues = _guard().scan_file(Path("api.py"), code)
    assert any("status code" in i.message for i in issues)


def test_with_json_response_clean():
    code = '''
from fastapi import FastAPI
from fastapi.responses import JSONResponse
app = FastAPI()

@app.post("/v1/users")
def create_user(name: str):
    try:
        return JSONResponse(content={"name": name})
    except Exception:
        raise
'''
    issues = _guard().scan_file(Path("api.py"), code)
    assert not any("status code" in i.message for i in issues)


def test_with_http_exception_clean():
    code = '''
from fastapi import FastAPI, HTTPException
app = FastAPI()

@app.get("/v1/items")
def get_item(item_id: int):
    try:
        return {"id": item_id}
    except ValueError:
        raise HTTPException(status_code=404)
'''
    issues = _guard().scan_file(Path("api.py"), code)
    assert not any("status code" in i.message for i in issues)


# ── Non-API files ignored ───────────────────────────────


def test_non_api_file_ignored():
    code = 'def hello():\n    return "world"\n'
    issues = _guard().scan_file(Path("utils.py"), code)
    assert issues == []


def test_test_file_ignored():
    code = '''
from fastapi import FastAPI
app = FastAPI()

@app.get("/test")
def test_route():
    return {}
'''
    issues = _guard().scan_file(Path("test_api.py"), code)
    assert issues == []


# ── scan() with real files ───────────────────────────────


def test_scan_real_fastapi_file(tmp_path):
    (tmp_path / "api.py").write_text('''
from fastapi import FastAPI
app = FastAPI()

@app.get("/users")
def get_users(limit, offset):
    return []
''')
    issues = _guard().scan(tmp_path)
    assert len(issues) > 0


def test_scan_skips_venv(tmp_path):
    venv = tmp_path / ".venv"
    venv.mkdir()
    (venv / "api.py").write_text('''
from fastapi import FastAPI
app = FastAPI()

@app.get("/users")
def get_users(limit, offset):
    return []
''')
    issues = _guard().scan(tmp_path)
    assert len(issues) == 0


# ── Flask support ────────────────────────────────────────


def test_flask_route_detected():
    code = '''
from flask import Flask
app = Flask(__name__)

@app.route("/health")
def health(request):
    return "ok"
'''
    issues = _guard().scan_file(Path("app.py"), code)
    assert any("version prefix" in i.message for i in issues)


# ── Well-designed API (no issues) ────────────────────────


def test_well_designed_api_clean():
    code = '''
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
app = FastAPI()

@app.get("/v1/users")
def get_users(limit: int = 10, offset: int = 0):
    try:
        return JSONResponse(content=[], status_code=200)
    except Exception:
        raise HTTPException(status_code=500)
'''
    issues = _guard().scan_file(Path("api.py"), code)
    # Should have no type hints, error handling, version, or status code issues
    assert not any("type hints" in i.message for i in issues)
    assert not any("error handling" in i.message for i in issues)
    assert not any("version prefix" in i.message for i in issues)
    assert not any("status code" in i.message for i in issues)
