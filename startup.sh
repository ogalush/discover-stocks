
#!/bin/bash

set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_DIR"

# MCP Server
echo "[START] MCP Server"
env MCP_TRANSPORT=http python3 mcp_server.py &
MCP_PID=$!

# Streamlit
echo "[START] Streamlit"
python3 -m streamlit run app.py --server.headless=true &
STREAMLIT_PID=$!

# Gateway
echo "[START] Gateway"
python3 gateway.py &
GATEWAY_PID=$!

echo "[INFO] All processes started"
echo "[INFO] MCP PID: ${MCP_PID:?}"
echo "[INFO] Streamlit PID: ${STREAMLIT_PID:?}"
echo "[INFO] Gateway PID: ${GATEWAY_PID:?}"

cleanup() {
    echo "[STOP] Stopping all processes..."

    kill "${GATEWAY_PID:?}" "${MCP_PID:?}" "${STREAMLIT_PID:?}" 2>/dev/null || true

    wait "${GATEWAY_PID:?}" 2>/dev/null || true
    wait "${MCP_PID:?}" 2>/dev/null || true
    wait "${STREAMLIT_PID:?}" 2>/dev/null || true
}

trap cleanup SIGTERM SIGINT

# Monitor processes
while true; do
    for PID in "${GATEWAY_PID:?}" "${MCP_PID:?}" "${STREAMLIT_PID:?}"; do
        if ! kill -0 "$PID" 2>/dev/null; then
            echo "[ERROR] Process ${PID:?} exited"
            cleanup
            exit 1
        fi
    done

    sleep 1
done
