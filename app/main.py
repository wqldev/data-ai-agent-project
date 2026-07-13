"""FastAPI entry: serve UI + analysis API in one process for Render."""

from __future__ import annotations

import json
import traceback
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .pipeline import LLMConfig, run_analysis_stream, test_llm_connection
from .sales_data import SALES_DATA

ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = ROOT / "static"

app = FastAPI(title="AI Agent 数据分析", version="1.0.0")


class LLMConfigIn(BaseModel):
    api_base: str = Field(..., min_length=1, description="OpenAI 兼容 API 地址")
    api_key: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)


class AnalyzeIn(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    api_base: str
    api_key: str
    model: str


def _cfg(body: LLMConfigIn | AnalyzeIn) -> LLMConfig:
    return LLMConfig(
        api_base=body.api_base.strip(),
        api_key=body.api_key.strip(),
        model=body.model.strip(),
    )


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/sample-data")
async def sample_data() -> dict[str, Any]:
    return SALES_DATA


@app.post("/api/test-connection")
async def test_connection(body: LLMConfigIn) -> dict[str, Any]:
    try:
        return await test_llm_connection(_cfg(body))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail=f"连接失败：{exc}") from exc


@app.post("/api/analyze")
async def analyze(body: AnalyzeIn) -> StreamingResponse:
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="请输入分析问题")

    cfg = _cfg(body)

    async def event_generator():
        try:
            async for event in run_analysis_stream(question, cfg):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:  # noqa: BLE001
            err = {
                "type": "error",
                "message": str(exc),
                "trace": traceback.format_exc(),
            }
            yield f"data: {json.dumps(err, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/")
async def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
