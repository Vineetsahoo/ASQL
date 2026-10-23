import re

with open(r'c:\Users\vinee\Downloads\ASQL\report.html', 'r', encoding='utf-8') as f:
    content = f.read()

tbody_match = re.search(r'<tbody>(.*?)</tbody>', content, re.DOTALL)
if not tbody_match:
    print("No tbody found")
    exit()

tbody = tbody_match.group(1)
rows = re.findall(r'<tr>(.*?)</tr>', tbody, re.DOTALL)

cards_html = '<div class="cards-grid">\n'
for row in rows:
    tds = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
    if len(tds) < 9:
        continue
    
    idx = tds[0].strip()
    file_path = tds[1].strip()
    line_num = tds[2].strip()
    violation = tds[3].strip()
    message = tds[4].strip()
    snippet = tds[5].strip()
    rewrite = tds[6].strip()
    impact = tds[7].strip()
    conf = tds[8].strip()

    card = f"""
    <div class="glass-card violation-card">
        <div class="card-header">
            <div class="card-title">
                {violation}
                <span class="file-info">{file_path}:{line_num}</span>
            </div>
            <div class="card-meta">
                {impact}
                <span class="conf-badge">{conf}</span>
            </div>
        </div>
        <div class="card-body">
            <p class="message">{message}</p>
            <div class="code-compare">
                <div class="code-block snippet-block">
                    <h4>Original Code</h4>
                    {snippet}
                </div>
                <div class="code-block rewrite-block">
                    <h4>Optimized Rewrite</h4>
                    {rewrite}
                </div>
            </div>
        </div>
    </div>
"""
    cards_html += card

cards_html += '</div>'

table_responsive_pattern = r'<div class="table-responsive">\s*<table>.*?</table>\s*</div>'
new_content = re.sub(table_responsive_pattern, cards_html, content, flags=re.DOTALL)

css = """
        .cards-grid {
            display: flex;
            flex-direction: column;
            gap: 1.5rem;
            margin-bottom: 4rem;
        }
        .violation-card {
            padding: 2rem;
            background: var(--surface);
            backdrop-filter: blur(24px);
            border: 1px solid var(--border);
            border-radius: 16px;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .violation-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
            border-color: var(--border-highlight);
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 1px solid var(--border);
        }
        .card-title {
            display: flex;
            align-items: center;
            gap: 1rem;
            flex-wrap: wrap;
        }
        .file-info {
            font-family: 'Roboto Mono', monospace;
            color: #CCCCCC;
            font-size: 0.9rem;
            background: rgba(255,255,255,0.1);
            padding: 4px 8px;
            border-radius: 4px;
        }
        .card-meta {
            display: flex;
            align-items: center;
            gap: 1rem;
        }
        .conf-badge {
            font-weight: 700;
            color: #00E676;
            font-size: 0.9rem;
        }
        .card-body p.message {
            max-width: 100%;
            color: #FFFFFF !important;
            font-size: 1.05rem;
            margin-bottom: 1.5rem;
            line-height: 1.6;
        }
        .code-compare {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 1.5rem;
        }
        @media (max-width: 900px) {
            .code-compare {
                grid-template-columns: 1fr;
            }
        }
        .code-block h4 {
            font-size: 0.85rem;
            color: #888888;
            margin-bottom: 0.5rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .code-block pre {
            max-width: 100% !important;
            width: 100%;
            margin: 0;
            box-sizing: border-box;
        }
"""
new_content = new_content.replace('</style>', css + '\n    </style>')

new_content = new_content.replace('.from("tbody tr"', '.from(".violation-card"')
new_content = new_content.replace('const rows = document.querySelectorAll(\'tbody tr\');', 'const rows = document.querySelectorAll(\'.violation-card\');')
new_content = new_content.replace('const violationCell = row.cells[3].innerText;', 'const badge = row.querySelector(".card-title .badge");\\n                const violationCell = badge ? badge.innerText : "";')
new_content = new_content.replace('const impactCell = row.cells[7].innerText.trim();', 'const impactElement = row.querySelector(".card-meta .cost-badge");\\n                const impactCell = impactElement ? impactElement.innerText.trim() : "";')

with open(r'c:\Users\vinee\Downloads\ASQL\report.html', 'w', encoding='utf-8') as f:
    f.write(new_content)
print("Transformation complete.")
