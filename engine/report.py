"""Report generator: renders findings to a static HTML table.

Per PRD v2 §3: single static HTML, no JS charting library.
"""

from typing import List
from engine.models import Finding
import html

RULE_COLORS = {
    "AP-01": "#e74c3c",  # red
    "AP-02": "#f39c12",  # orange
    "AP-03": "#95a5a6",
    "AP-05": "#9b59b6",  # purple
}

COST_COLORS = {
    "FULL_SCAN_DETECTED": "#e74c3c",
    "INDEX_USED": "#27ae60",
    "NOT_EVALUATED": "#95a5a6",
}


def generate_html_report(findings: List[Finding], output_path: str) -> None:
    """Render findings as a static HTML report with a styled table."""

    rows: List[str] = []
    for i, f in enumerate(findings, 1):
        badge_color = RULE_COLORS.get(f.rule_id, "#95a5a6")
        cost_color = COST_COLORS.get(f.cost_signal, "#95a5a6")

        if f.rewrite_sql:
            rewrite_cell = f'<pre class="rewrite">{html.escape(f.rewrite_sql)}</pre>'
        else:
            rewrite_cell = '<span class="na">—</span>'

        rows.append(f"""
        <tr>
            <td>{i}</td>
            <td class="file">{html.escape(f.file)}</td>
            <td>{f.line}</td>
            <td><span class="badge" style="background:{badge_color}">{html.escape(f.rule_id)}</span>
                <br><small>{html.escape(f.rule_name)}</small></td>
            <td class="message">{html.escape(f.message)}</td>
            <td><pre class="snippet">{html.escape(f.snippet)}</pre></td>
            <td>{rewrite_cell}</td>
            <td><span class="cost-badge" style="background:{cost_color}">{html.escape(f.cost_signal)}</span></td>
            <td>{f.confidence:.0%}</td>
        </tr>""")

    rows_html = "".join(rows)

    report_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SQL Anti-Pattern Detection Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
            background: #0f1419;
            color: #e1e8ed;
            padding: 2rem;
        }}
        .header {{
            text-align: center;
            margin-bottom: 2rem;
            padding: 2rem;
            background: linear-gradient(135deg, #1a1f2e 0%, #2d1b42 100%);
            border-radius: 12px;
            border: 1px solid #2a2f3e;
        }}
        h1 {{
            font-size: 1.8rem;
            background: linear-gradient(90deg, #667eea, #764ba2);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }}
        .summary {{
            color: #8899a6;
            font-size: 0.95rem;
        }}
        .summary strong {{
            color: #e1e8ed;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: #15202b;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 24px rgba(0,0,0,0.3);
        }}
        thead {{
            background: linear-gradient(135deg, #1e2d3d 0%, #2a1f3d 100%);
        }}
        th {{
            padding: 1rem 0.75rem;
            text-align: left;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #8899a6;
            border-bottom: 2px solid #2a2f3e;
        }}
        td {{
            padding: 0.75rem;
            border-bottom: 1px solid #1e2d3d;
            font-size: 0.85rem;
            vertical-align: top;
        }}
        tr:hover {{
            background: #1a2836;
        }}
        .file {{
            font-family: 'Cascadia Code', 'Fira Code', monospace;
            color: #667eea;
            font-size: 0.8rem;
        }}
        .message {{
            max-width: 300px;
            line-height: 1.4;
        }}
        .badge {{
            display: inline-block;
            padding: 0.2rem 0.6rem;
            border-radius: 4px;
            color: white;
            font-weight: 600;
            font-size: 0.75rem;
        }}
        .cost-badge {{
            display: inline-block;
            padding: 0.2rem 0.5rem;
            border-radius: 4px;
            color: white;
            font-size: 0.7rem;
            font-weight: 500;
        }}
        pre.snippet, pre.rewrite {{
            background: #0d1117;
            padding: 0.5rem;
            border-radius: 6px;
            font-size: 0.75rem;
            overflow-x: auto;
            max-width: 350px;
            white-space: pre-wrap;
            word-break: break-word;
            font-family: 'Cascadia Code', 'Fira Code', monospace;
            color: #c9d1d9;
            border: 1px solid #21262d;
        }}
        pre.rewrite {{
            border-left: 3px solid #27ae60;
        }}
        .na {{
            color: #4a5568;
        }}
        .footer {{
            text-align: center;
            margin-top: 2rem;
            color: #4a5568;
            font-size: 0.8rem;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>&#x1F50D; SQL Anti-Pattern Detection Report</h1>
        <p class="summary">
            Found <strong>{len(findings)}</strong> anti-pattern(s) across scanned SQL files
        </p>
    </div>
    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>File</th>
                <th>Line</th>
                <th>Rule</th>
                <th>Message</th>
                <th>Snippet</th>
                <th>Suggested Rewrite</th>
                <th>Cost Signal</th>
                <th>Confidence</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>
    <div class="footer">
        Generated by SQL Anti-Pattern Detection Tool (MVP v2)
    </div>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_html)
