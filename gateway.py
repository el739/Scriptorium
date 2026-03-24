"""
LLM Gateway - 将 chat/completions 请求转发到 API 供应商，支持流式与非流式传输，并记录完整日志。
"""

import json
import logging
import os
import time
import uuid
from datetime import datetime
from typing import AsyncGenerator

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, Response, StreamingResponse

# ──────────────────────────────────────────────
# 配置（也可通过环境变量覆盖）
# ──────────────────────────────────────────────
UPSTREAM_BASE_URL = os.getenv("UPSTREAM_BASE_URL", "https://api.openai.com")
UPSTREAM_API_KEY  = os.getenv("UPSTREAM_API_KEY", "")   # 可留空，由客户端传入
LOG_DIR           = os.getenv("LOG_DIR", "logs")
LOG_LEVEL         = os.getenv("LOG_LEVEL", "INFO")
REQUEST_TIMEOUT   = float(os.getenv("REQUEST_TIMEOUT", "600"))

# ──────────────────────────────────────────────
# 日志设置
# ──────────────────────────────────────────────
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(LOG_DIR, "gateway.log"), encoding="utf-8"),
    ],
)
logger = logging.getLogger("llm_gateway")


def _log_to_file(request_id: str, direction: str, data: dict | str):
    """将请求/响应详情写入单独的 JSONL 文件，便于检索。"""
    log_file = os.path.join(LOG_DIR, "traffic.jsonl")
    record = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "request_id": request_id,
        "direction": direction,   # "REQUEST" | "RESPONSE" | "RESPONSE_STREAM"
        "data": data,
    }
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ──────────────────────────────────────────────
# FastAPI 应用
# ──────────────────────────────────────────────
app = FastAPI(title="LLM Gateway", version="1.0.0")


def _build_upstream_headers(original_headers: dict) -> dict:
    """构造转发给上游的请求头。"""
    headers = {
        "Content-Type": "application/json",
    }
    # 优先使用网关自己配置的 key，否则透传客户端传来的 Authorization
    if UPSTREAM_API_KEY:
        headers["Authorization"] = f"Bearer {UPSTREAM_API_KEY}"
    elif "authorization" in original_headers:
        headers["Authorization"] = original_headers["authorization"]

    return headers


# ──────────────────────────────────────────────
# 核心路由：POST /v1/chat/completions
# ──────────────────────────────────────────────
@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    request_id = str(uuid.uuid4())[:8]
    start_ts   = time.time()

    # ---------- 解析请求体 ----------
    try:
        body = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON body: {exc}")

    is_stream = body.get("stream", False)

    # ---------- 记录请求 ----------
    logger.info(
        "[%s] ← CLIENT  model=%s stream=%s messages=%d",
        request_id,
        body.get("model", "?"),
        is_stream,
        len(body.get("messages", [])),
    )
    _log_to_file(request_id, "REQUEST", body)

    # ---------- 构造上游请求 ----------
    upstream_url = f"{UPSTREAM_BASE_URL.rstrip('/')}/v1/chat/completions"
    headers      = _build_upstream_headers(dict(request.headers))

    # ── 流式模式 ──────────────────────────────
    if is_stream:
        return await _handle_stream_request(
            request_id=request_id,
            upstream_url=upstream_url,
            headers=headers,
            body=body,
            start_ts=start_ts,
        )

    # ── 非流式模式 ────────────────────────────
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            resp = await client.post(upstream_url, json=body, headers=headers)
    except httpx.TimeoutException:
        logger.error("[%s] ✗ Upstream timeout after %.1fs", request_id, REQUEST_TIMEOUT)
        raise HTTPException(status_code=504, detail="Upstream API timeout")
    except httpx.RequestError as exc:
        logger.error("[%s] ✗ Upstream connection error: %s", request_id, exc)
        raise HTTPException(status_code=502, detail=f"Upstream connection error: {exc}")

    elapsed = time.time() - start_ts

    try:
        resp_body = resp.json()
    except Exception:
        resp_body = resp.text

    # 记录响应
    usage = resp_body.get("usage", {}) if isinstance(resp_body, dict) else {}
    logger.info(
        "[%s] → CLIENT  status=%d elapsed=%.2fs prompt_tokens=%s completion_tokens=%s",
        request_id,
        resp.status_code,
        elapsed,
        usage.get("prompt_tokens", "?"),
        usage.get("completion_tokens", "?"),
    )
    _log_to_file(
        request_id,
        "RESPONSE",
        {
            "status_code": resp.status_code,
            "elapsed_s": round(elapsed, 3),
            "headers": dict(resp.headers),
            "body": resp_body,
        },
    )

    if isinstance(resp_body, (dict, list)):
        return JSONResponse(
            content=resp_body,
            status_code=resp.status_code,
            headers={"X-Request-ID": request_id},
        )

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type"),
        headers={"X-Request-ID": request_id},
    )


async def _handle_stream_request(
    request_id: str,
    upstream_url: str,
    headers: dict,
    body: dict,
    start_ts: float,
):
    """建立上游流式连接；若上游非 200，直接透传错误状态与错误体。"""
    client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT)
    upstream_request = client.build_request("POST", upstream_url, json=body, headers=headers)

    try:
        resp = await client.send(upstream_request, stream=True)
    except httpx.TimeoutException:
        await client.aclose()
        logger.error("[%s] ✗ Upstream stream timeout after %.1fs", request_id, REQUEST_TIMEOUT)
        raise HTTPException(status_code=504, detail="Upstream API timeout")
    except httpx.RequestError as exc:
        await client.aclose()
        logger.error("[%s] ✗ Upstream stream connection error: %s", request_id, exc)
        raise HTTPException(status_code=502, detail=f"Upstream connection error: {exc}")

    if resp.status_code != 200:
        error_body_bytes = await resp.aread()
        await resp.aclose()
        await client.aclose()

        elapsed = time.time() - start_ts
        logger.error(
            "[%s] ✗ Upstream error status=%d elapsed=%.2fs",
            request_id,
            resp.status_code,
            elapsed,
        )

        try:
            error_body = json.loads(error_body_bytes)
            is_json = True
        except Exception:
            error_body = error_body_bytes.decode(errors="replace")
            is_json = False

        _log_to_file(
            request_id,
            "RESPONSE",
            {
                "status_code": resp.status_code,
                "elapsed_s": round(elapsed, 3),
                "body": error_body,
            },
        )

        if is_json:
            return JSONResponse(
                content=error_body,
                status_code=resp.status_code,
                headers={"X-Request-ID": request_id},
            )
        return Response(
            content=error_body_bytes,
            status_code=resp.status_code,
            media_type=resp.headers.get("content-type"),
            headers={"X-Request-ID": request_id},
        )

    return StreamingResponse(
        _stream_upstream(
            request_id=request_id,
            resp=resp,
            client=client,
            start_ts=start_ts,
        ),
        status_code=resp.status_code,
        media_type="text/event-stream",
        headers={
            "X-Request-ID": request_id,
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


async def _stream_upstream(
    request_id: str,
    resp: httpx.Response,
    client: httpx.AsyncClient,
    start_ts: float,
) -> AsyncGenerator[bytes, None]:
    """向上游发起流式请求，逐行转发 SSE 数据，同时收集完整内容用于日志。"""
    collected_chunks: list[str] = []
    status_code = resp.status_code

    try:
        async for line in resp.aiter_lines():
            if not line:
                yield b"\n"
                continue

            # 收集原始行，便于日志
            collected_chunks.append(line)

            # 原样转发给客户端（每行只补一个换行，避免额外空行）
            yield (line + "\n").encode()

    except httpx.TimeoutException:
        elapsed = time.time() - start_ts
        logger.error("[%s] ✗ Stream timeout after %.1fs", request_id, elapsed)
        error_payload = json.dumps({"error": {"message": "Upstream stream timeout", "type": "gateway_error"}})
        yield f"data: {error_payload}\n\n".encode()
        return
    except httpx.RequestError as exc:
        logger.error("[%s] ✗ Stream connection error: %s", request_id, exc)
        error_payload = json.dumps({"error": {"message": str(exc), "type": "gateway_error"}})
        yield f"data: {error_payload}\n\n".encode()
        return
    finally:
        await resp.aclose()
        await client.aclose()

    elapsed = time.time() - start_ts

    # ── 解析 SSE chunks，提取可读内容用于日志 ──
    full_content = ""
    finish_reason = None
    prompt_tokens = completion_tokens = None

    for raw_line in collected_chunks:
        if not raw_line.startswith("data:"):
            continue
        data_str = raw_line[5:].strip()
        if data_str == "[DONE]":
            continue
        try:
            chunk = json.loads(data_str)
            # 累积文本
            for choice in chunk.get("choices", []):
                delta = choice.get("delta", {})
                if not isinstance(delta, dict):
                    delta = {}

                content_piece = delta.get("content")
                if isinstance(content_piece, str):
                    full_content += content_piece
                elif isinstance(content_piece, list):
                    # 兼容多模态/结构化 delta，尽量提取文本用于日志
                    for item in content_piece:
                        if isinstance(item, str):
                            full_content += item
                        elif isinstance(item, dict):
                            text = item.get("text")
                            if isinstance(text, str):
                                full_content += text

                if choice.get("finish_reason"):
                    finish_reason = choice["finish_reason"]
            # 部分供应商在最后一个 chunk 返回 usage
            if "usage" in chunk:
                u = chunk["usage"]
                if isinstance(u, dict):
                    prompt_tokens     = u.get("prompt_tokens")
                    completion_tokens = u.get("completion_tokens")
        except json.JSONDecodeError:
            pass

    logger.info(
        "[%s] → CLIENT  status=%d elapsed=%.2fs finish=%s prompt_tokens=%s completion_tokens=%s chars=%d",
        request_id,
        status_code,
        elapsed,
        finish_reason or "?",
        prompt_tokens or "?",
        completion_tokens or "?",
        len(full_content),
    )
    _log_to_file(
        request_id,
        "RESPONSE_STREAM",
        {
            "status_code": status_code,
            "elapsed_s": round(elapsed, 3),
            "finish_reason": finish_reason,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "full_content": full_content,
            "raw_chunks": collected_chunks,
        },
    )


# ──────────────────────────────────────────────
# 健康检查
# ──────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "upstream": UPSTREAM_BASE_URL}


# ──────────────────────────────────────────────
# 入口
# ──────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "gateway:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8080")),
        reload=False,
    )
