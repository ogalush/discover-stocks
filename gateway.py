"""
Reverse proxy gateway for discover-stocks MCP Server and Streamlit frontend.
"""
import asyncio
import os

from aiohttp import web, ClientSession, ClientTimeout, WSMsgType
from multidict import CIMultiDict


# --------------------------------------------------
# Configuration
# --------------------------------------------------
GATEWAY_PORT = int(os.environ.get("PORT", "8000"))

STREAMLIT_URL = "https://127.0.0.1:443"
MCP_URL = "http://127.0.0.1:8001/mcp"

# Streamlit uses a self-signed certificate.
STREAMLIT_SSL_VERIFY = False


# --------------------------------------------------
# HTTP header handling
# --------------------------------------------------

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
}


def filter_headers(headers):
    """Remove hop-by-hop headers and headers nominated by Connection."""
    excluded = set(HOP_BY_HOP_HEADERS)

    connection = headers.get("Connection", "")
    for item in connection.split(","):
        if item.strip():
            excluded.add(item.strip().lower())

    result = CIMultiDict()

    for key, value in headers.items():
        if key.lower() not in excluded and key.lower() != "host":
            result.add(key, value)

    return result


def forwarded_headers(request):
    """Prepare headers for the upstream server."""
    headers = filter_headers(request.headers)

    client_ip = request.remote or ""

    existing_forwarded = request.headers.get("X-Forwarded-For")
    if existing_forwarded:
        client_ip = f"{existing_forwarded}, {client_ip}"

    headers["X-Forwarded-For"] = client_ip
    headers["X-Forwarded-Host"] = request.headers.get("Host", "")

    # App Service may already provide this header.
    proto = request.headers.get(
        "X-Forwarded-Proto",
        request.scheme,
    )
    headers["X-Forwarded-Proto"] = proto

    return headers


# --------------------------------------------------
# WebSocket proxy (Streamlit)
# --------------------------------------------------
async def proxy_websocket(request, upstream_url):
    headers = forwarded_headers(request)

    protocols = [
        p.strip()
        for p in request.headers.get("Sec-WebSocket-Protocol", "").split(",")
        if p.strip()
    ]

    # protocols引数で渡すため、通常ヘッダーからは除外
    headers.popall("Sec-WebSocket-Protocol", None)

    downstream = web.WebSocketResponse(
        heartbeat=30,
        max_msg_size=0, ## データベース管理 -> エクスポートで WebSocket 4MB制限があるため解除
    )
    await downstream.prepare(request)

    try:
        async with request.app["session"].ws_connect(
            upstream_url,
            headers=headers,
            protocols=protocols,
            ssl=STREAMLIT_SSL_VERIFY,
            heartbeat=30,
            max_msg_size=0,  ## データベース管理 -> エクスポートで WebSocket 4MB制限があるため解除

        ) as upstream:
            async def relay(source, destination):
                async for msg in source:
                    if msg.type == WSMsgType.TEXT:
                        await destination.send_str(msg.data)

                    elif msg.type == WSMsgType.BINARY:
                        await destination.send_bytes(msg.data)

                    elif msg.type == WSMsgType.PING:
                        await destination.ping(msg.data)

                    elif msg.type == WSMsgType.PONG:
                        await destination.pong(msg.data)

                    elif msg.type in (
                        WSMsgType.CLOSE,
                        WSMsgType.CLOSED,
                        WSMsgType.ERROR,
                    ):
                        break

            tasks = [
                asyncio.create_task(
                    relay(downstream, upstream)
                ),
                asyncio.create_task(
                    relay(upstream, downstream)
                ),
            ]

            done, pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED,
            )

            for task in pending:
                task.cancel()

            await asyncio.gather(
                *pending,
                return_exceptions=True,
            )

            await upstream.close()

    except Exception:
        # The connection may already have been closed by the client.
        pass

    finally:
        await downstream.close()

    return downstream


# --------------------------------------------------
# HTTP reverse proxy
# --------------------------------------------------
async def proxy_http(request, upstream_url, ssl=None):
    headers = forwarded_headers(request)

    try:
        async with request.app["session"].request(
            method=request.method,
            url=upstream_url,
            headers=headers,
            data=request.content,
            allow_redirects=False,
            ssl=ssl,
        ) as upstream:

            response_headers = filter_headers(
                upstream.headers
            )

            downstream = web.StreamResponse(
                status=upstream.status,
                reason=upstream.reason,
                headers=response_headers,
            )

            await downstream.prepare(request)

            async for chunk in upstream.content.iter_chunked(
                64 * 1024
            ):
                await downstream.write(chunk)

            await downstream.write_eof()

            return downstream

    except Exception as exc:
        print(f"Proxy error: {exc}")

        return web.Response(
            status=502,
            text="Bad Gateway",
        )


# --------------------------------------------------
# Routing
# --------------------------------------------------
async def handle_mcp(request):
    """Forward MCP Streamable HTTP requests."""
    upstream_url = MCP_URL + (
        f"?{request.query_string}"
        if request.query_string
        else ""
    )

    return await proxy_http(
        request,
        upstream_url,
        ssl=None,
    )


async def handle_streamlit(request):
    """Forward all non-MCP requests to Streamlit."""
    upstream_url = STREAMLIT_URL + str(request.rel_url)

    if request.headers.get("Upgrade", "").lower() == "websocket":
        return await proxy_websocket(
            request,
            upstream_url,
        )

    return await proxy_http(
        request,
        upstream_url,
        ssl=STREAMLIT_SSL_VERIFY,
    )


# --------------------------------------------------
# Application lifecycle
# --------------------------------------------------
async def on_startup(app):
    timeout = ClientTimeout(
        total=None,
        connect=30,
        sock_read=None,
    )

    app["session"] = ClientSession(
        timeout=timeout,
        auto_decompress=False,
    )


async def on_cleanup(app):
    await app["session"].close()


def create_app():
    app = web.Application()

    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    # MCP endpoint
    app.router.add_route("*", "/mcp", handle_mcp)

    # Streamlit: everything else
    app.router.add_route("*", "/{path:.*}", handle_streamlit)

    return app


if __name__ == "__main__":
    web.run_app(
        create_app(),
        host="0.0.0.0",
        port=GATEWAY_PORT,
    )
