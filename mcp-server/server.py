"""MCP server for the Personal Expense Tracker.

This is a thin wrapper around the FastAPI backend: every tool just makes an
HTTP call to the backend's REST API. We don't talk to the database directly,
so all the same validation and per-user isolation rules from the backend
still apply here.

Each tool takes the caller's own JWT `token` (the same token the frontend
gets back from /auth/login, /auth/signup, or /auth/google) as an explicit
argument, and sends it as the Authorization header. That token is what the
backend uses to figure out which user is calling and to make sure a tool
call can only ever read or change that one user's expenses. This matches
how MCP servers are normally run - one server process per user/agent
session, not shared across everyone.

Run locally with:
    python server.py
"""

import os

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv()

# URL of the FastAPI backend this MCP server calls.
API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")

mcp = FastMCP("expense-tracker")


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


@mcp.tool()
def add_expense(token: str, amount: float, category: str, date: str, description: str = "") -> dict:
    """Add a new expense for the authenticated user.

    Args:
        token: the user's JWT access token (from login/signup/google auth)
        amount: expense amount, e.g. 12.50
        category: category name, e.g. "Food", "Transport"
        date: expense date in YYYY-MM-DD format
        description: optional free-text note
    """
    response = httpx.post(
        f"{API_BASE_URL}/expenses",
        headers=_auth_headers(token),
        json={"amount": amount, "category": category, "date": date, "description": description},
    )
    response.raise_for_status()
    return response.json()


@mcp.tool()
def list_expenses(token: str, month: str = "") -> list:
    """List the authenticated user's expenses.

    Args:
        token: the user's JWT access token
        month: optional month filter in YYYY-MM format; leave blank for all expenses
    """
    params = {"month": month} if month else {}
    response = httpx.get(f"{API_BASE_URL}/expenses", headers=_auth_headers(token), params=params)
    response.raise_for_status()
    return response.json()


@mcp.tool()
def update_expense(
    token: str, expense_id: int, amount: float, category: str, date: str, description: str = ""
) -> dict:
    """Update an existing expense that belongs to the authenticated user.

    Args:
        token: the user's JWT access token
        expense_id: id of the expense to update
        amount: new amount
        category: new category
        date: new date in YYYY-MM-DD format
        description: new description (optional)
    """
    response = httpx.put(
        f"{API_BASE_URL}/expenses/{expense_id}",
        headers=_auth_headers(token),
        json={"amount": amount, "category": category, "date": date, "description": description},
    )
    response.raise_for_status()
    return response.json()


@mcp.tool()
def delete_expense(token: str, expense_id: int) -> dict:
    """Delete an expense that belongs to the authenticated user.

    Args:
        token: the user's JWT access token
        expense_id: id of the expense to delete
    """
    response = httpx.delete(f"{API_BASE_URL}/expenses/{expense_id}", headers=_auth_headers(token))
    response.raise_for_status()
    return response.json()


@mcp.tool()
def get_monthly_summary(token: str, month: str) -> dict:
    """Get the total spent and a per-category breakdown for one month.

    Args:
        token: the user's JWT access token
        month: month to summarize, in YYYY-MM format
    """
    response = httpx.get(
        f"{API_BASE_URL}/expenses/summary", headers=_auth_headers(token), params={"month": month}
    )
    response.raise_for_status()
    return response.json()


@mcp.resource("expenses://{token}/{month}")
def monthly_expenses_resource(token: str, month: str) -> str:
    """Expose a user's expenses for one month (YYYY-MM) as a readable
    resource, e.g. expenses://<jwt-token>/2026-08

    Note: this puts the token in the resource URI for simplicity. Treat
    these URIs the same way you'd treat the token itself - don't log or
    share them.
    """
    response = httpx.get(
        f"{API_BASE_URL}/expenses", headers=_auth_headers(token), params={"month": month}
    )
    response.raise_for_status()
    return response.text


if __name__ == "__main__":
    mcp.run()
