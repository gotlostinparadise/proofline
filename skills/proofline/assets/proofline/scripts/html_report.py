#!/usr/bin/env python3
"""Shared helpers for self-contained Proofline HTML artifacts."""

from __future__ import annotations

from html import escape
import re
from typing import Any


def render_html_document(
    *,
    title: str,
    heading: str,
    report_kind: str,
    summary_items: list[tuple[str, str]] | None = None,
    sections: list[dict[str, Any]] | None = None,
) -> str:
    """Render a small, self-contained HTML report with escaped text content."""

    section_html = "\n".join(_render_section(section) for section in sections or [])
    summary_html = _render_summary(summary_items or [])
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{escape(title)}</title>\n"
        "<style>\n"
        ":root{--bg:#faf9f5;--paper:#fff;--ink:#141413;--muted:#66635c;--line:#d1cfc5;--soft:#f0eee6;--accent:#b85c3e;--ok:#5f7f49;--bad:#b85c3e;--mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;--sans:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;--serif:ui-serif,Georgia,serif;}"
        "*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--sans);line-height:1.55;padding:48px 28px 96px;}"
        "main{max-width:1040px;margin:0 auto}header{margin-bottom:32px}h1{font-family:var(--serif);font-weight:500;font-size:40px;line-height:1.12;margin:0 0 10px}h2{font-family:var(--serif);font-weight:500;font-size:24px;margin:0 0 14px}"
        ".eyebrow{font:12px var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin-bottom:10px}.summary{display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;margin:24px 0 34px}.summary div,section{background:var(--paper);border:1px solid var(--line);border-radius:8px;padding:18px}.k{font:11px var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-bottom:4px}.v{font-weight:650}section{margin:18px 0}ul{margin:0;padding-left:20px}li{margin:6px 0}code,pre{font-family:var(--mono)}table{width:100%;border-collapse:collapse;font-size:14px}th,td{border-bottom:1px solid var(--line);padding:9px 8px;text-align:left;vertical-align:top}th{font:11px var(--mono);letter-spacing:.06em;text-transform:uppercase;color:var(--muted);background:var(--soft)}.status-pass,.covered{color:var(--ok);font-weight:700}.status-fail,.missing{color:var(--bad);font-weight:700}.muted{color:var(--muted)}\n"
        "</style>\n"
        "</head>\n"
        f'<body data-proofline-report="{escape(report_kind, quote=True)}">\n'
        "<main>\n"
        "<header>\n"
        '<div class="eyebrow">Proofline artifact</div>\n'
        f"<h1>{escape(heading)}</h1>\n"
        "</header>\n"
        f"{summary_html}\n"
        f"{section_html}\n"
        "</main>\n"
        "</body>\n"
        "</html>\n"
    )


def render_table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body_rows = []
    for row in rows:
        body_rows.append("<tr>" + "".join(f"<td>{escape(str(cell))}</td>" for cell in row) + "</tr>")
    return "<table><thead><tr>" + head + "</tr></thead><tbody>" + "".join(body_rows) + "</tbody></table>"


def render_status_text(status: str) -> str:
    cls = "status-pass" if status.upper() in {"PASS", "COVERED", "PRESENT"} else "status-fail"
    return f'<span class="{cls}">{escape(status)}</span>'


def slugify(value: str) -> str:
    lowered = value.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    return slug or "section"


def _render_summary(items: list[tuple[str, str]]) -> str:
    if not items:
        return ""
    cells = []
    for key, value in items:
        cells.append(
            "<div>"
            f'<div class="k">{escape(key)}</div>'
            f'<div class="v">{escape(value)}</div>'
            "</div>"
        )
    return '<div class="summary">' + "".join(cells) + "</div>"


def _render_section(section: dict[str, Any]) -> str:
    section_id = str(section.get("id") or slugify(str(section.get("title") or "section")))
    title = str(section.get("title") or section_id)
    body = section.get("body_html")
    if body is None:
        if isinstance(section.get("items"), list):
            body = _render_items([str(item) for item in section["items"]])
        elif isinstance(section.get("table"), dict):
            table = section["table"]
            body = render_table(
                [str(header) for header in table.get("headers", [])],
                [[str(cell) for cell in row] for row in table.get("rows", [])],
            )
        else:
            body = ""
    return (
        f'<section id="{escape(section_id, quote=True)}" data-proofline-section="{escape(section_id, quote=True)}">\n'
        f"<h2>{escape(title)}</h2>\n"
        f"{body}\n"
        "</section>"
    )


def _render_items(items: list[str]) -> str:
    if not items:
        return '<p class="muted">None.</p>'
    return "<ul>" + "".join(f"<li>{escape(item)}</li>" for item in items) + "</ul>"
