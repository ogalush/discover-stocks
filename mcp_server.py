"""
discover-stocks MCP Server

MCP Python SDK 2.x
Transport: streamable-http or stdio
"""

from datetime import date
from typing import Any
import os

from mcp.server.mcpserver import MCPServer
from utils.db import get_connection


# MCP Server
mcp = MCPServer(
    name="discover-stocks",
    instructions=(
        "discover-stocksの投票データを取得するMCPサーバーです。"
        "銘柄の投票状況やランキングを取得できます。"
    ),
    version="0.1.0",
)


# Utility
def validate_date(value: str) -> str:
    """YYYY-MM-DD形式の日付を検証する。"""

    try:
        date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"Invalid date: {value}. Expected YYYY-MM-DD."
        ) from exc

    return value


@mcp.tool()
def get_vote_dates():
    """
    投票日一覧を取得する。

    Returns:
        list[str]: 投票日一覧 (YYYY-MM-DD)
    """
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT DISTINCT vote_date FROM vote ORDER BY vote_date")
    vote_dates = [row[0] for row in c.fetchall()]

    conn.close()

    return vote_dates


@mcp.tool()
def get_vote_result(selected_date: str):
    """
    指定日の銘柄投票ランキングを取得する。

    Args:
        selected_date: 対象日 (YYYY-MM-DD)
    """

    selected_date_str = validate_date(selected_date)

    conn = get_connection()
    c = conn.cursor()

    # 投票数の合計を取得
    c.execute(
        """
        SELECT COUNT(*) as total_votes
        FROM vote
        WHERE vote_date = ?
        """,
        (selected_date_str,)
    )
    result = c.fetchone()
    total_votes = result[0] if result is not None else 0


    # 投票ボタンが押された回数を取得（created_atが同じものを1回としてカウント）
    c.execute(
        """
        SELECT COUNT(DISTINCT created_at) as vote_sessions
        FROM vote
        WHERE vote_date = ?
        """,
        (selected_date_str,)
    )
    vote_sessions_result = c.fetchone()
    vote_sessions = vote_sessions_result[0] if vote_sessions_result is not None else 0


    # voteテーブルから、対象日の各銘柄の投票数を集計（多い順）
    c.execute(
        """
        SELECT v.stock_code, COUNT(*) as vote_count, m.stock_name
        FROM vote v
        LEFT JOIN stock_master m ON v.stock_code = m.stock_code
        WHERE v.vote_date = ?
        GROUP BY v.stock_code
        ORDER BY vote_count DESC
        """,
        (selected_date_str,)
    )
    results = c.fetchall()
    conn.close()

    return {
        "vote_date": selected_date_str,
        "total_votes": total_votes,
        "vote_sessions": vote_sessions,
        "vote_results": [
            {
                "stock_code": row[0],
                "stock_name": row[2],
                "vote_count": row[1]
            }
            for row in results
        ]
    }


# Entry Point
if __name__ == "__main__":
    transport = os.getenv("MCP_TRANSPORT", "http")

    if transport == "stdio":
        # Debug / MCP Inspector
        mcp.run(transport="stdio")

    elif transport == "http":
        # Gateway integration
        mcp.run(
            transport="streamable-http",
            host="0.0.0.0",
            port=8001,
        )

    else:
        raise ValueError(
            f"Unsupported MCP_TRANSPORT: {transport}"
        )
