"""FastAPI backend — wraps agent.py + executor.py for the HTML frontend."""
import json
import io
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

from agent import parse_instruction
from executor import execute_steps, ExecutionError
from recorder import save_sequence, load_sequence, list_sequences, delete_sequence
from knowledge import build_vectorstore

DATA_DIR = Path(__file__).parent / "data"
OUTPUT_DIR = Path(__file__).parent / "output"
STEPS_DIR = Path(__file__).parent / "steps"

for d in [DATA_DIR, OUTPUT_DIR, STEPS_DIR]:
    d.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="ExcelHelper Agent API")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

# Ensure KB is available
try:
    build_vectorstore(force=False)
except Exception:
    pass  # will build on first request if needed

# ── in-memory state per session ─────────────────────────────

history_store: list[dict] = []  # chat history for multi-turn


# ── endpoints ───────────────────────────────────────────────

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a CSV/Excel file, store it, return schema info."""
    file_path = DATA_DIR / file.filename
    content = await file.read()
    file_path.write_bytes(content)

    if file.filename.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(content), encoding="utf-8-sig")
    else:
        df = pd.read_excel(io.BytesIO(content))

    schema = []
    for col in df.columns:
        samples = ", ".join(df[col].dropna().head(3).astype(str).tolist())
        schema.append({"name": col, "dtype": str(df[col].dtype), "samples": samples})

    return {
        "file_name": file.filename,
        "rows": len(df),
        "cols": len(df.columns),
        "schema": schema,
        "file_path": str(file_path),
    }


@app.post("/api/parse")
async def parse_instruction_endpoint(body: dict):
    """Natural language → parsed steps (with RAG + Deepseek)."""
    user_message = body.get("message", "")
    schema_info = body.get("schema_info", "")
    extra_schemas = body.get("extra_schemas", [])  # schemas of other uploaded files
    global history_store
    history = body.get("history", history_store)

    if not user_message:
        raise HTTPException(400, "message is required")

    # include extra file schemas so LLM knows column names of merge targets
    full_schema = schema_info
    if extra_schemas:
        for es in extra_schemas:
            cols = ", ".join(f"{c['name']}({c['dtype']})" for c in es.get("schema", []))
            full_schema += f"\n[其他已上传文件 {es['name']} 的列: {cols}]"

    try:
        steps, raw_response = parse_instruction(
            user_message=user_message,
            schema_info=full_schema,
            history=history,
        )
    except Exception as e:
        raise HTTPException(500, f"Parse error: {e}")

    # update history
    history_store.append({"user": user_message, "assistant": raw_response})
    if len(history_store) > 6:
        history_store = history_store[-6:]

    return {"steps": steps, "raw_response": raw_response}


@app.post("/api/execute")
async def execute_steps_endpoint(body: dict):
    """Execute a list of steps on uploaded data."""
    steps = body.get("steps", [])
    file_path = body.get("file_path", "")

    if not steps:
        raise HTTPException(400, "steps is required")
    if not file_path:
        raise HTTPException(400, "file_path is required")

    try:
        df, output_path = execute_steps(steps, file_path)
    except ExecutionError as e:
        raise HTTPException(400, str(e))

    # convert result to JSON-friendly format
    result_data = df.fillna("").to_dict(orient="records")
    headers = list(df.columns)
    output_name = Path(output_path).name if output_path else ""

    return {
        "rows": len(df),
        "cols": len(df.columns),
        "headers": headers,
        "data": result_data[:500],  # limit preview
        "output_file": output_name,
    }


@app.get("/api/download/{file_name}")
async def download_file(file_name: str):
    """Download a generated Excel file."""
    file_path = OUTPUT_DIR / file_name
    if not file_path.exists():
        raise HTTPException(404, "file not found")
    return FileResponse(str(file_path), filename=file_name)


@app.get("/api/sequences")
async def get_sequences():
    """List all saved step sequences."""
    seqs = list_sequences()
    return {"sequences": seqs}


@app.post("/api/sequences/save")
async def save_sequence_endpoint(body: dict):
    """Save a step sequence."""
    name = body.get("name", "")
    steps = body.get("steps", [])
    if not name:
        raise HTTPException(400, "name is required")
    if not steps:
        raise HTTPException(400, "steps is required")
    save_sequence(name, steps)
    return {"ok": True, "name": name}


@app.post("/api/sequences/load")
async def load_sequence_endpoint(body: dict):
    """Load a step sequence by name."""
    name = body.get("name", "")
    if not name:
        raise HTTPException(400, "name is required")
    try:
        steps = load_sequence(name)
    except FileNotFoundError:
        raise HTTPException(404, f"sequence not found: {name}")
    return {"steps": steps}


@app.post("/api/sequences/delete")
async def delete_sequence_endpoint(body: dict):
    """Delete a step sequence."""
    name = body.get("name", "")
    if not name:
        raise HTTPException(400, "name is required")
    delete_sequence(name)
    return {"ok": True}


@app.get("/")
async def index():
    html_path = Path(__file__).parent / "excel_agent.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/api/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765)
