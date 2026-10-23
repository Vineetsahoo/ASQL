"""Report generator: renders findings and scanned queries to a cinematic Web3 HTML dashboard.

Shares the exact design language, tokens, Three.js WebGL canvas, GSAP animations,
and Chart.js visualizations as the ASQL Web3 documentation.
"""

from typing import List, Optional, Dict
import html
import json
from engine.models import Finding, ScannedQuery
from engine.flagger import RULE_SEVERITY, ALTERNATIVE_SOLUTIONS, mark_sql


RULE_COLORS: Dict[str, str] = {
    "AP-01": "#FF0000",  # Neon Red (SELECT_STAR)
    "AP-02": "#FF5500",  # Orange (NON_SARGABLE_PREDICATE)
    "AP-03": "#FF0055",  # Crimson / Dark Red (CARTESIAN_JOIN)
    "AP-04": "#E60000",  # Vivid Red (LEADING_WILDCARD)
    "AP-05": "#AA00FF",  # Purple (UNNECESSARY_SUBQUERY)
    "AP-06": "#00B0FF",  # Cyan Blue (UNION_WITHOUT_ALL)
}

COST_COLORS: Dict[str, str] = {
    "FULL_SCAN_DETECTED": "#FF0000",
    "INDEX_USED": "#00E676",
    "NOT_EVALUATED": "#888888",
}


def generate_html_report(
    findings: List[Finding],
    output_path: str,
    scanned_queries: Optional[List[ScannedQuery]] = None,
) -> None:
    """Render findings and all scanned queries into a unified Cinematic Web3 HTML dashboard."""

    # Build synthetic scanned queries if not provided
    if scanned_queries is None:
        scanned_queries = []
        # Group findings by file
        by_file: Dict[str, List[Finding]] = {}
        for f in findings:
            by_file.setdefault(f.file, []).append(f)
        
        for file_path, file_findings in by_file.items():
            first_f = file_findings[0]
            sql = first_f.query or first_f.snippet
            scanned_queries.append(ScannedQuery(
                file=file_path,
                status="FLAGGED",
                sql=sql,
                findings=file_findings,
                cost_signal=first_f.cost_signal,
                line_count=len(sql.splitlines()) if sql else 1,
            ))

    total_scanned = len(scanned_queries)
    flagged_queries_count = sum(1 for q in scanned_queries if q.status == "FLAGGED")
    clean_queries_count = sum(1 for q in scanned_queries if q.status == "PASSED")
    warning_queries_count = sum(1 for q in scanned_queries if q.status == "WARNING")
    total_findings_count = len(findings)

    health_score = round((clean_queries_count / total_scanned * 100), 1) if total_scanned > 0 else 100.0

    # Build query cards HTML
    cards_html_list: List[str] = []

    for idx, sq in enumerate(scanned_queries, 1):
        if sq.status == "FLAGGED" and sq.findings:
            # Build flagged violation cards
            for f_idx, f in enumerate(sq.findings):
                badge_color = RULE_COLORS.get(f.rule_id, "#FF0000")
                cost_color = COST_COLORS.get(f.cost_signal, "#888888")
                sev = getattr(f, "severity", None) or RULE_SEVERITY.get(f.rule_id, "HIGH")
                alt_sol = getattr(f, "alternative_solution", None) or ALTERNATIVE_SOLUTIONS.get(f.rule_id, "Refactor query.")

                # Original SQL snippet or marked SQL
                orig_sql = f.query or sq.sql or f.snippet
                marked = mark_sql(orig_sql, [f]) if orig_sql else f.snippet

                if f.rewrite_sql:
                    rewrite_display = f'<pre class="rewrite">{html.escape(f.rewrite_sql)}</pre>'
                else:
                    rewrite_display = '<pre class="rewrite na">-- Automated rewrite not available.\n-- Follow the recommended alternative solution above.</pre>'

                sev_color = "#FF0000" if sev in ("CRITICAL", "HIGH") else "#FF5500" if sev == "MEDIUM" else "#00B0FF"

                card = f"""
            <div class="glass-card violation-card query-card" data-rule="{html.escape(f.rule_id)}" data-status="flagged">
                <div class="card-header">
                    <div class="card-title">
                        <span class="badge" style="background:{badge_color}">{html.escape(f.rule_id)}</span>
                        <small>{html.escape(f.rule_name)}</small>
                        <span class="file-info">{html.escape(f.file)}:{f.line}</span>
                        <span class="sev-badge" style="border: 1px solid {sev_color}; color: {sev_color};">{html.escape(sev)}</span>
                    </div>
                    <div class="card-meta">
                        <span class="cost-badge" style="background:rgba(255,0,0,0.1); border-color:{cost_color}; color:#FFF;">{html.escape(f.cost_signal)}</span>
                        <span class="conf-badge">{f.confidence:.0%}</span>
                    </div>
                </div>
                <div class="card-body">
                    <p class="message">{html.escape(f.message)}</p>
                    <div class="alt-solution-box">
                        <strong>💡 Alternative Solution & Best Practice:</strong>
                        <p>{html.escape(alt_sol)}</p>
                    </div>
                    <div class="code-compare">
                        <div class="code-block snippet-block">
                            <h4>Original Code (Marked Location)</h4>
                            <pre class="snippet">{html.escape(marked)}</pre>
                        </div>
                        <div class="code-block rewrite-block">
                            <h4>Optimized Rewrite / Alternative Solution</h4>
                            {rewrite_display}
                        </div>
                    </div>
                </div>
            </div>"""
                cards_html_list.append(card)

        elif sq.status == "PASSED":
            cost_color = COST_COLORS.get(sq.cost_signal, "#00E676")
            card = f"""
            <div class="glass-card clean-card query-card" data-rule="clean" data-status="clean">
                <div class="card-header">
                    <div class="card-title">
                        <span class="badge pass-badge">PASSED</span>
                        <small>CLEAN QUERY</small>
                        <span class="file-info">{html.escape(sq.file)}</span>
                    </div>
                    <div class="card-meta">
                        <span class="cost-badge" style="background:rgba(0,230,118,0.1); border-color:#00E676; color:#00E676;">{html.escape(sq.cost_signal if sq.cost_signal != "NOT_EVALUATED" else "VERIFIED")}</span>
                        <span class="conf-badge" style="color:#00E676;">100% CLEAN</span>
                    </div>
                </div>
                <div class="card-body">
                    <p class="message" style="color: #00E676 !important;">
                        ✅ Zero anti-patterns detected. This query adheres to standard relational indexing and sargable predicates.
                    </p>
                    <div class="code-compare" style="grid-template-columns: 1fr;">
                        <div class="code-block clean-code-block">
                            <h4>Verified SQL Query</h4>
                            <pre class="snippet clean-snippet">{html.escape(sq.sql)}</pre>
                        </div>
                    </div>
                </div>
            </div>"""
            cards_html_list.append(card)

        else:  # WARNING
            warning_text = sq.warning or "File is empty or contains malformed syntax."
            card = f"""
            <div class="glass-card warning-card query-card" data-rule="warning" data-status="warning">
                <div class="card-header">
                    <div class="card-title">
                        <span class="badge warn-badge">WARNING</span>
                        <small>SKIPPED / SYNTAX NOTICE</small>
                        <span class="file-info">{html.escape(sq.file)}</span>
                    </div>
                    <div class="card-meta">
                        <span class="cost-badge" style="border-color:#f39c12; color:#f39c12;">SYNTAX_NOTICE</span>
                    </div>
                </div>
                <div class="card-body">
                    <p class="message" style="color: #f39c12 !important;">⚠️ {html.escape(warning_text)}</p>
                    {f'<pre class="snippet" style="border-color:#f39c12;">{html.escape(sq.sql)}</pre>' if sq.sql.strip() else ''}
                </div>
            </div>"""
            cards_html_list.append(card)

    cards_html = "\n".join(cards_html_list)

    # Compute rule breakdown dictionary for Chart.js
    rule_counts: Dict[str, int] = {}
    cost_counts: Dict[str, int] = {}
    for f in findings:
        rule_counts[f.rule_id] = rule_counts.get(f.rule_id, 0) + 1
        sig = f.cost_signal.replace(" ", "")
        cost_counts[sig] = cost_counts.get(sig, 0) + 1

    chart_rule_labels = json.dumps(list(rule_counts.keys()))
    chart_rule_data = json.dumps(list(rule_counts.values()))
    chart_cost_labels = json.dumps(list(cost_counts.keys()))
    chart_cost_data = json.dumps(list(cost_counts.values()))

    # Complete HTML page
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ASQL - SQL Anti-Pattern Detection Report</title>
    <link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=Roboto+Mono:wght@400;500;700&display=swap" rel="stylesheet">

    <!-- Libraries -->
    <link rel="icon" href="data:;base64,iVBORw0KGgo=">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/gsap.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.2/ScrollTrigger.min.js"></script>
    <script src="https://cdn.jsdelivr.net/gh/studio-freight/lenis@1.0.27/bundled/lenis.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>

    <style>
        :root {{
            --primary: #FF0000;
            --primary-glow: rgba(255, 0, 0, 0.4);
            --bg-dark: #030303;
            --surface: rgba(15, 15, 15, 0.6);
            --surface-hover: rgba(25, 25, 25, 0.8);
            --text-main: #FFFFFF;
            --text-muted: #888888;
            --border: rgba(255, 255, 255, 0.08);
            --border-highlight: rgba(255, 0, 0, 0.5);

            --ap-high: #FF0000;
            --ap-med: #FF5500;
            --ap-low: #00E676;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}

        html.lenis {{
            height: auto;
        }}

        .lenis.lenis-smooth {{
            scroll-behavior: auto !important;
        }}

        body {{
            font-family: 'Space Grotesk', sans-serif;
            background-color: var(--bg-dark);
            color: var(--text-main);
            padding: 4rem 2rem;
            min-height: 100vh;
            line-height: 1.6;
            -webkit-font-smoothing: antialiased;
            overflow-x: hidden;
        }}

        #webgl-canvas {{
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            z-index: -1;
            pointer-events: none;
        }}

        /* Top Nav */
        .top-nav {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 80px;
            display: flex;
            align-items: center;
            padding: 0 4rem;
            z-index: 100;
            background: rgba(3, 3, 3, 0.8);
            backdrop-filter: blur(20px);
            border-bottom: 1px solid var(--border);
        }}

        .logo {{
            font-size: 24px;
            font-weight: 700;
            color: var(--text-main);
            text-decoration: none;
            display: flex;
            align-items: center;
            gap: 12px;
            letter-spacing: -1px;
            transition: color 0.3s;
        }}

        .logo span {{
            color: transparent;
            -webkit-text-stroke: 1px var(--primary);
        }}

        .nav-links {{
            margin-left: auto;
            display: flex;
            gap: 2rem;
        }}

        .nav-links a {{
            color: var(--text-muted);
            text-decoration: none;
            font-weight: 500;
            transition: color 0.3s;
        }}

        .nav-links a:hover {{
            color: var(--text-main);
        }}

        .container {{
            max-width: 1600px;
            margin: 80px auto 0;
        }}

        .header {{
            margin-bottom: 3rem;
            padding: 0;
            background: var(--surface);
            backdrop-filter: blur(24px);
            border: 1px solid var(--border);
            border-radius: 24px;
            position: relative;
            overflow: hidden;
        }}

        .header::before {{
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle at center, var(--primary-glow) 0%, transparent 40%);
            opacity: 0.15;
            pointer-events: none;
        }}

        .terminal-header {{
            display: flex;
            align-items: center;
            padding: 12px 20px;
            background: rgba(0, 0, 0, 0.6);
            border-bottom: 1px solid var(--border);
            font-family: 'Roboto Mono', monospace;
            font-size: 0.85rem;
            color: var(--text-muted);
            gap: 8px;
        }}

        .dot {{
            width: 12px;
            height: 12px;
            border-radius: 50%;
        }}
        .dot.red {{ background: #ff5f56; }}
        .dot.yellow {{ background: #ffbd2e; }}
        .dot.green {{ background: #27c93f; }}

        .terminal-body {{
            padding: 2.5rem 3rem;
            font-family: 'Roboto Mono', monospace;
            color: #00E676;
            min-height: 200px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }}

        .typewriter-line {{
            margin-bottom: 0.6rem;
            font-size: 1rem;
            opacity: 0;
            transform: translateY(10px);
        }}

        .typewriter-line.visible {{
            opacity: 1;
            transform: translateY(0);
            transition: opacity 0.2s, transform 0.2s;
        }}

        h1 {{
            font-size: clamp(2rem, 3.5vw, 3.5rem);
            font-weight: 700;
            letter-spacing: -1px;
            margin-bottom: 0.5rem;
            position: relative;
            z-index: 2;
        }}

        h1 .accent {{
            color: transparent;
            -webkit-text-stroke: 1px var(--primary);
            text-shadow: 0 0 20px var(--primary-glow);
        }}

        .summary {{
            color: var(--text-muted);
            font-size: 1.15rem;
            position: relative;
            z-index: 2;
        }}

        .summary strong {{
            color: var(--text-main);
            font-size: 1.3rem;
            font-weight: 700;
        }}

        .pulse-text {{
            animation: pulse-color 2s infinite;
        }}

        @keyframes pulse-color {{
            0% {{ color: var(--primary); text-shadow: 0 0 10px var(--primary-glow); }}
            50% {{ color: var(--text-main); text-shadow: none; }}
            100% {{ color: var(--primary); text-shadow: 0 0 10px var(--primary-glow); }}
        }}

        /* Metric Highlights Grid */
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 1.5rem;
            margin-bottom: 3rem;
        }}

        .metric-card {{
            background: var(--surface);
            backdrop-filter: blur(20px);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 1.5rem 2rem;
            transition: transform 0.3s, border-color 0.3s;
        }}

        .metric-card:hover {{
            transform: translateY(-4px);
            border-color: var(--border-highlight);
        }}

        .metric-title {{
            font-size: 0.85rem;
            text-transform: uppercase;
            letter-spacing: 1.5px;
            color: var(--text-muted);
            font-family: 'Roboto Mono', monospace;
            margin-bottom: 0.5rem;
        }}

        .metric-value {{
            font-size: 2.2rem;
            font-weight: 700;
            color: var(--text-main);
        }}

        /* Filter Controls */
        .controls-panel {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 1.5rem;
            margin-bottom: 2.5rem;
            padding: 1.5rem;
            background: var(--surface);
            backdrop-filter: blur(24px);
            border: 1px solid var(--border);
            border-radius: 18px;
        }}

        .filter-tabs {{
            display: flex;
            gap: 0.6rem;
            flex-wrap: wrap;
        }}

        .filter-btn {{
            background: rgba(255, 255, 255, 0.04);
            color: var(--text-muted);
            border: 1px solid var(--border);
            padding: 8px 16px;
            border-radius: 10px;
            font-size: 0.85rem;
            font-family: 'Space Grotesk', sans-serif;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.25s;
        }}

        .filter-btn:hover, .filter-btn.active {{
            background: var(--primary);
            color: #000;
            border-color: var(--primary);
            box-shadow: 0 0 15px var(--primary-glow);
        }}

        .search-box {{
            display: flex;
            align-items: center;
            background: #000;
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 8px 16px;
            width: 320px;
        }}

        .search-box input {{
            background: transparent;
            border: none;
            outline: none;
            color: #FFF;
            font-family: 'Roboto Mono', monospace;
            font-size: 0.85rem;
            width: 100%;
        }}

        /* Cards Grid */
        .cards-grid {{
            display: flex;
            flex-direction: column;
            gap: 1.8rem;
            margin-bottom: 4rem;
        }}

        .query-card {{
            padding: 2rem;
            background: var(--surface);
            backdrop-filter: blur(24px);
            border: 1px solid var(--border);
            border-radius: 18px;
            transition: transform 0.3s, box-shadow 0.3s, border-color 0.3s;
        }}

        .query-card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 12px 35px rgba(0, 0, 0, 0.5);
            border-color: var(--border-highlight);
        }}

        .clean-card {{
            border-left: 4px solid #00E676;
        }}

        .warning-card {{
            border-left: 4px solid #f39c12;
        }}

        .violation-card {{
            border-left: 4px solid var(--primary);
        }}

        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1.2rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border);
            flex-wrap: wrap;
            gap: 1rem;
        }}

        .card-title {{
            display: flex;
            align-items: center;
            gap: 1rem;
            flex-wrap: wrap;
        }}

        .card-title small {{
            font-family: 'Roboto Mono', monospace;
            color: var(--text-muted);
            font-weight: 500;
            letter-spacing: 0.5px;
        }}

        .file-info {{
            font-family: 'Roboto Mono', monospace;
            color: #CCCCCC;
            font-size: 0.85rem;
            background: rgba(255, 255, 255, 0.08);
            padding: 4px 10px;
            border-radius: 6px;
            border: 1px solid var(--border);
        }}

        .badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 8px;
            color: #000 !important;
            font-weight: 700;
            font-size: 0.75rem;
            letter-spacing: 1px;
            font-family: 'Roboto Mono', monospace;
            box-shadow: 0 0 12px var(--primary-glow);
        }}

        .pass-badge {{
            background: #00E676 !important;
            box-shadow: 0 0 12px rgba(0, 230, 118, 0.4) !important;
        }}

        .warn-badge {{
            background: #f39c12 !important;
            box-shadow: 0 0 12px rgba(243, 156, 18, 0.4) !important;
        }}

        .sev-badge {{
            font-family: 'Roboto Mono', monospace;
            font-size: 0.7rem;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 4px;
            letter-spacing: 1px;
        }}

        .card-meta {{
            display: flex;
            align-items: center;
            gap: 1rem;
        }}

        .cost-badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 600;
            font-family: 'Roboto Mono', monospace;
            text-transform: uppercase;
            border: 1px solid var(--border);
        }}

        .conf-badge {{
            font-weight: 700;
            color: #00E676;
            font-size: 0.9rem;
            font-family: 'Roboto Mono', monospace;
        }}

        .card-body p.message {{
            color: #FFFFFF !important;
            font-size: 1.05rem;
            margin-bottom: 1.2rem;
            line-height: 1.6;
        }}

        .alt-solution-box {{
            background: rgba(255, 85, 0, 0.08);
            border: 1px solid rgba(255, 85, 0, 0.3);
            border-radius: 12px;
            padding: 1rem 1.4rem;
            margin-bottom: 1.5rem;
            font-size: 0.95rem;
            line-height: 1.6;
            color: #ffd8c0;
        }}

        .alt-solution-box strong {{
            color: #FF5500;
            display: block;
            margin-bottom: 0.3rem;
            font-family: 'Roboto Mono', monospace;
            font-size: 0.85rem;
            letter-spacing: 0.5px;
        }}

        .code-compare {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
        }}

        @media (max-width: 990px) {{
            .code-compare {{
                grid-template-columns: 1fr;
            }}
        }}

        .code-block h4 {{
            font-size: 0.8rem;
            color: #888888;
            margin-bottom: 0.6rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            font-family: 'Roboto Mono', monospace;
        }}

        pre.snippet, pre.rewrite {{
            background: #000 !important;
            padding: 1.2rem;
            border-radius: 12px;
            font-size: 0.85rem;
            overflow-x: auto;
            max-width: 100%;
            white-space: pre-wrap;
            word-break: break-word;
            font-family: 'Roboto Mono', monospace;
            color: #E0E0E0 !important;
            border: 1px solid var(--border) !important;
            position: relative;
            line-height: 1.5;
        }}

        pre.rewrite {{
            border-left: 3px solid #00E676 !important;
        }}

        pre.clean-snippet {{
            border-left: 3px solid #00E676 !important;
        }}

        pre.rewrite.na {{
            border-left: 3px solid #888888 !important;
            color: #888888 !important;
        }}

        .footer {{
            text-align: center;
            margin-top: 5rem;
            color: var(--text-muted);
            font-size: 0.85rem;
            font-family: 'Roboto Mono', monospace;
            letter-spacing: 1px;
            padding-bottom: 4rem;
        }}
    </style>
</head>

<body>
    <canvas id="webgl-canvas"></canvas>

    <nav class="top-nav">
        <a href="docs.html" class="logo">ASQL <span>REPORT</span></a>
        <div class="nav-links">
            <a href="docs.html">Documentation</a>
            <a href="findings.json" target="_blank">Export JSON</a>
        </div>
    </nav>

    <div class="container">
        <!-- Terminal Header -->
        <div class="header">
            <div class="terminal-header">
                <div class="dot red"></div>
                <div class="dot yellow"></div>
                <div class="dot green"></div>
                <span style="margin-left: 10px; letter-spacing: 1px;">root@asql-engine: ~/scan_logs</span>
            </div>
            <div class="terminal-body" id="terminal-body">
                <div id="typewriter"></div>
                <div id="main-header-content" style="display:none;">
                    <h1 class="reveal-text">SQL Anti-Pattern <span class="accent">Detection Report</span></h1>
                    <p class="summary reveal-fade">
                        Found <strong>{total_findings_count}</strong> anti-pattern(s) across <strong>{total_scanned}</strong> scanned SQL queries.
                    </p>
                </div>
            </div>
        </div>

        <!-- Metric Highlights -->
        <div class="metrics-grid reveal-fade">
            <div class="metric-card">
                <div class="metric-title">Total Files Scanned</div>
                <div class="metric-value">{total_scanned}</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Anti-Patterns Flagged</div>
                <div class="metric-value" style="color: var(--primary);">{total_findings_count}</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Clean / Passing Queries</div>
                <div class="metric-value" style="color: #00E676;">{clean_queries_count}</div>
            </div>
            <div class="metric-card">
                <div class="metric-title">Engine Health Score</div>
                <div class="metric-value" style="color: {'#00E676' if health_score >= 80 else '#FF5500' if health_score >= 50 else '#FF0000'};">{health_score}%</div>
            </div>
        </div>

        <!-- Interactive Charts -->
        <div class="charts-wrapper reveal-fade" style="margin-bottom: 3.5rem;">
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(400px, 1fr)); gap: 2rem;">
                <div class="glass-card" style="padding: 2.2rem; background: var(--surface); backdrop-filter: blur(24px); border: 1px solid var(--border); border-radius: 20px;">
                    <h3 style="margin-bottom: 1.5rem; font-size: 1.1rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 2px;">
                        Anti-Pattern Distribution
                    </h3>
                    <div style="height: 250px;"><canvas id="violationChart"></canvas></div>
                </div>
                <div class="glass-card" style="padding: 2.2rem; background: var(--surface); backdrop-filter: blur(24px); border: 1px solid var(--border); border-radius: 20px;">
                    <h3 style="margin-bottom: 1.5rem; font-size: 1.1rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 2px;">
                        Impact & Cost Signals
                    </h3>
                    <div style="height: 250px;"><canvas id="impactChart"></canvas></div>
                </div>
            </div>
        </div>

        <!-- Filter Controls -->
        <div class="controls-panel reveal-fade">
            <div class="filter-tabs">
                <button class="filter-btn active" data-filter="all">All Queries ({total_scanned})</button>
                <button class="filter-btn" data-filter="flagged">Flagged ({flagged_queries_count})</button>
                <button class="filter-btn" data-filter="clean">Clean / Passed ({clean_queries_count})</button>
                <button class="filter-btn" data-filter="AP-01">AP-01</button>
                <button class="filter-btn" data-filter="AP-02">AP-02</button>
                <button class="filter-btn" data-filter="AP-03">AP-03</button>
                <button class="filter-btn" data-filter="AP-04">AP-04</button>
                <button class="filter-btn" data-filter="AP-05">AP-05</button>
                <button class="filter-btn" data-filter="AP-06">AP-06</button>
            </div>
            <div class="search-box">
                <input type="text" id="searchInput" placeholder="Search queries, rules, files...">
            </div>
        </div>

        <!-- Query Cards Grid -->
        <div class="cards-grid" id="cardsGrid">
            {cards_html}
        </div>

        <div class="footer">
            Generated by ASQL Deterministic AST Static Engine • Web3 Cinematic Interface
        </div>
    </div>

    <!-- Scripts: Three.js, GSAP, Lenis, Chart.js & Filters -->
    <script>
        // Smooth scrolling via Lenis
        const lenis = new Lenis({{
            duration: 1.2,
            easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)),
            direction: 'vertical',
            smooth: true
        }});

        function raf(time) {{
            lenis.raf(time);
            requestAnimationFrame(raf);
        }}
        requestAnimationFrame(raf);

        // Three.js Animated WebGL Canvas
        const initWebGL = () => {{
            const canvas = document.getElementById('webgl-canvas');
            const scene = new THREE.Scene();
            scene.fog = new THREE.FogExp2(0x030303, 0.025);

            const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
            camera.position.set(0, 5, 25);

            const renderer = new THREE.WebGLRenderer({{ canvas, antialias: true, alpha: true }});
            renderer.setSize(window.innerWidth, window.innerHeight);
            renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

            // Wireframe terrain
            const planeGeo = new THREE.PlaneGeometry(150, 150, 64, 64);
            const planeMat = new THREE.MeshBasicMaterial({{
                color: 0xff0000,
                wireframe: true,
                transparent: true,
                opacity: 0.15
            }});
            const plane = new THREE.Mesh(planeGeo, planeMat);
            plane.rotation.x = -Math.PI / 2;
            plane.position.y = -10;
            scene.add(plane);

            // Floating data shards
            const shardGeo = new THREE.BoxGeometry(1.2, 1.2, 1.2);
            const shardMat = new THREE.MeshPhysicalMaterial({{
                color: 0xff1100,
                metalness: 0.8,
                roughness: 0.2,
                transmission: 0.9,
                thickness: 0.5,
                emissive: 0x220000,
                wireframe: true
            }});

            const shards = new THREE.Group();
            for (let i = 0; i < 40; i++) {{
                const shard = new THREE.Mesh(shardGeo, shardMat);
                shard.position.set(
                    (Math.random() - 0.5) * 80,
                    (Math.random() - 0.5) * 40,
                    (Math.random() - 0.5) * 80 - 10
                );
                shard.rotation.set(Math.random() * Math.PI, Math.random() * Math.PI, 0);
                const scale = Math.random() * 2 + 0.5;
                shard.scale.set(scale, scale, scale);

                shard.userData = {{
                    speedRot: (Math.random() - 0.5) * 0.02,
                    initialY: shard.position.y,
                    phase: Math.random() * Math.PI * 2
                }};
                shards.add(shard);
            }}
            scene.add(shards);

            // Lighting
            scene.add(new THREE.AmbientLight(0xffffff, 0.3));
            const pointLight = new THREE.PointLight(0xff0000, 10, 100);
            pointLight.position.set(0, 20, 0);
            scene.add(pointLight);

            // Animation Loop
            let time = 0;
            const animate = () => {{
                requestAnimationFrame(animate);
                time += 0.03;

                const pos = planeGeo.attributes.position;
                for (let i = 0; i < pos.count; i++) {{
                    const x = pos.getX(i);
                    const y = pos.getY(i);
                    pos.setZ(i, Math.sin(x * 0.15 + time) * 2 + Math.cos(y * 0.15 + time * 0.8) * 2);
                }}
                pos.needsUpdate = true;

                shards.children.forEach(shard => {{
                    shard.rotation.x += shard.userData.speedRot;
                    shard.rotation.y += shard.userData.speedRot;
                    shard.position.y = shard.userData.initialY + Math.sin(time + shard.userData.phase) * 3;
                }});

                renderer.render(scene, camera);
            }};
            animate();

            // Parallax
            window.addEventListener('resize', () => {{
                camera.aspect = window.innerWidth / window.innerHeight;
                camera.updateProjectionMatrix();
                renderer.setSize(window.innerWidth, window.innerHeight);
            }});
        }};
        initWebGL();

        // Terminal Typewriter & GSAP Animations
        document.addEventListener("DOMContentLoaded", () => {{
            gsap.registerPlugin(ScrollTrigger);

            const lines = [
                "> Initializing ASQL Engine...",
                "> Scanning all corpus SQL files...",
                "> Executing deterministic AST rules...",
                "> Applying Flagging System & generating alternative rewrites...",
                "> SCAN COMPLETE. Processed {total_scanned} queries."
            ];

            const typewriterEl = document.getElementById('typewriter');
            const mainHeader = document.getElementById('main-header-content');
            const chartsWrapper = document.querySelector('.charts-wrapper');

            gsap.set(chartsWrapper, {{ opacity: 0 }});

            let lineIdx = 0;
            function typeNextLine() {{
                if (lineIdx < lines.length) {{
                    const lineDiv = document.createElement('div');
                    lineDiv.className = 'typewriter-line';
                    lineDiv.textContent = lines[lineIdx];
                    if (lineIdx === lines.length - 1) {{
                        lineDiv.style.color = 'var(--primary)';
                    }}
                    typewriterEl.appendChild(lineDiv);
                    void lineDiv.offsetWidth;
                    lineDiv.classList.add('visible');
                    lineIdx++;
                    setTimeout(typeNextLine, 180 + Math.random() * 200);
                }} else {{
                    setTimeout(() => {{
                        gsap.to(typewriterEl, {{ opacity: 0, duration: 0.4, onComplete: () => {{
                            typewriterEl.style.display = 'none';
                            mainHeader.style.display = 'block';
                            startMainAnimations();
                        }}}});
                    }}, 500);
                }}
            }}

            setTimeout(typeNextLine, 200);

            function startMainAnimations() {{
                const tl = gsap.timeline();
                tl.from("#main-header-content .reveal-text", {{ y: 20, opacity: 0, duration: 0.8, ease: "power4.out" }})
                  .from("#main-header-content .reveal-fade", {{ y: 15, opacity: 0, duration: 0.6, ease: "power3.out" }}, "-=0.4")
                  .to(chartsWrapper, {{ opacity: 1, duration: 0.6, ease: "power2.out" }}, "-=0.2");

                gsap.to(".query-card", {{
                    y: 0,
                    opacity: 1,
                    stagger: 0.03,
                    duration: 0.6,
                    ease: "back.out(1.1)"
                }});
            }}

            // Chart.js Setup
            Chart.defaults.color = '#888888';
            Chart.defaults.font.family = "'Space Grotesk', sans-serif";

            const ruleLabels = {chart_rule_labels};
            const ruleData = {chart_rule_data};
            const costLabels = {chart_cost_labels};
            const costData = {chart_cost_data};

            new Chart(document.getElementById('violationChart'), {{
                type: 'doughnut',
                data: {{
                    labels: ruleLabels.length ? ruleLabels : ['No Anti-patterns'],
                    datasets: [{{
                        data: ruleData.length ? ruleData : [1],
                        backgroundColor: [
                            'rgba(255, 0, 0, 0.85)',
                            'rgba(255, 85, 0, 0.85)',
                            'rgba(255, 0, 85, 0.85)',
                            'rgba(170, 0, 255, 0.85)',
                            'rgba(0, 176, 255, 0.85)',
                            'rgba(0, 230, 118, 0.85)'
                        ],
                        borderColor: '#030303',
                        borderWidth: 2
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    cutout: '72%',
                    plugins: {{
                        legend: {{ position: 'right', labels: {{ padding: 14, usePointStyle: true }} }}
                    }}
                }}
            }});

            new Chart(document.getElementById('impactChart'), {{
                type: 'bar',
                data: {{
                    labels: costLabels.length ? costLabels : ['VERIFIED'],
                    datasets: [{{
                        label: 'Queries',
                        data: costData.length ? costData : [{clean_queries_count}],
                        backgroundColor: 'rgba(255, 0, 0, 0.2)',
                        borderColor: '#FF0000',
                        borderWidth: 1,
                        borderRadius: 6
                    }}]
                }},
                options: {{
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {{
                        y: {{ beginAtZero: true, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
                        x: {{ grid: {{ display: false }} }}
                    }},
                    plugins: {{ legend: {{ display: false }} }}
                }}
            }});

            // Interactive Filtering
            const filterButtons = document.querySelectorAll('.filter-btn');
            const searchInput = document.getElementById('searchInput');
            const cards = document.querySelectorAll('.query-card');

            function applyFilters() {{
                const activeBtn = document.querySelector('.filter-btn.active');
                const filter = activeBtn ? activeBtn.getAttribute('data-filter') : 'all';
                const search = (searchInput.value || '').toLowerCase().trim();

                cards.forEach(card => {{
                    const cardRule = card.getAttribute('data-rule') || '';
                    const cardStatus = card.getAttribute('data-status') || '';
                    const text = card.textContent.toLowerCase();

                    let matchFilter = false;
                    if (filter === 'all') matchFilter = true;
                    else if (filter === 'flagged') matchFilter = (cardStatus === 'flagged');
                    else if (filter === 'clean') matchFilter = (cardStatus === 'clean');
                    else matchFilter = (cardRule === filter);

                    const matchSearch = !search || text.includes(search);

                    card.style.display = (matchFilter && matchSearch) ? 'block' : 'none';
                }});
            }}

            filterButtons.forEach(btn => {{
                btn.addEventListener('click', () => {{
                    filterButtons.forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                    applyFilters();
                }});
            }});

            if (searchInput) {{
                searchInput.addEventListener('input', applyFilters);
            }}
        }});
    </script>
</body>
</html>"""

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_html)
