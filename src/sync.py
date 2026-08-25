#!/usr/bin/env python3
"""
Bogazici University Academic Calendar Sync Script
Fetches academic calendar from https://akademiktakvim.bogazici.edu.tr/
Generates category-specific RFC 5545 compliant iCalendar (.ics) files and a web landing page.
Zero external dependencies - runs on standard Python 3.8+.
"""

import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path
import html

BASE_URL_TR = "https://akademiktakvim.bogazici.edu.tr/tr/json"
BASE_URL_EN = "https://akademiktakvim.bogazici.edu.tr/en/json"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

TR_TZ = timezone(timedelta(hours=3))

# Exact 1-to-1 official category definitions mapped by university kat_id
CATEGORIES = [
    {
        "kat_id": "29",
        "slug": "registration",
        "slug_tr": "kayit",
        "title": "Registration",
        "title_tr": "Kayıt",
        "description": "Course registration windows, advisor approvals, add/drop periods, and fee payment deadlines."
    },
    {
        "kat_id": "24",
        "slug": "administrative",
        "slug_tr": "idari",
        "title": "Administrative",
        "title_tr": "İdari",
        "description": "Administrative board meetings (ÜYK/FKK), official university deadlines, and department submissions."
    },
    {
        "kat_id": "23",
        "slug": "instruction",
        "slug_tr": "egitim",
        "title": "Instruction & Exams",
        "title_tr": "Eğitim-Öğretim",
        "description": "First and last days of classes, midterm & final exam periods, grade submissions, and semester dates."
    },
    {
        "kat_id": "25",
        "slug": "sfl",
        "slug_tr": "yadyok",
        "title": "School of Foreign Languages (SFL / YADYOK)",
        "title_tr": "YADYOK",
        "description": "BUEPT English proficiency exams, placement tests, preparatory classes terms, and result announcements."
    },
    {
        "kat_id": "28",
        "slug": "admission",
        "slug_tr": "basvuru",
        "title": "Admission & Applications",
        "title_tr": "Başvuru",
        "description": "Undergraduate/graduate applications, double major/minor transfers, and exchange program deadlines."
    }
]

def fetch_events(base_url: str, start_date: str, end_date: str) -> list:
    """Fetch calendar events from Bogazici API for a given date range."""
    url = f"{base_url}?type=4&date={start_date}&last_date={end_date}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = resp.read().decode("utf-8")
            events = json.loads(data)
            return events if isinstance(events, list) else []
    except Exception as e:
        print(f"Error fetching from {url}: {e}")
        return []

def sanitize_ics_text(text: str) -> str:
    """Escape special characters according to RFC 5545."""
    if not text:
        return ""
    text = html.unescape(text)
    text = text.replace("\\", "\\\\")
    text = text.replace(";", "\\;")
    text = text.replace(",", "\\,")
    text = text.replace("\r\n", "\\n").replace("\n", "\\n").replace("\r", "\\n")
    return text.strip()

def format_all_day_date(dt_str: str) -> str:
    """Parse 'YYYY-MM-DD HH:MM:SS' and return 'YYYYMMDD'."""
    dt = datetime.strptime(dt_str.split()[0], "%Y-%m-%d")
    return dt.strftime("%Y%m%d")

def format_all_day_end_date(dt_str: str) -> str:
    """In RFC 5545, all-day DTEND is exclusive (day after the event ends)."""
    dt = datetime.strptime(dt_str.split()[0], "%Y-%m-%d") + timedelta(days=1)
    return dt.strftime("%Y%m%d")

def generate_ics(events: list, cal_name: str, cal_desc: str, lang: str = "en") -> str:
    """Generate RFC 5545 compliant iCalendar string."""
    now_utc = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Bogazici University//Academic Calendar Sync//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{cal_name}",
        f"X-WR-CALDESC:{cal_desc}",
        f"X-WR-TIMEZONE:Europe/Istanbul",
        "REFRESH-INTERVAL;VALUE=DURATION:P1D",
        "X-PUBLISHED-TTL:P1D",
    ]

    seen_ids = set()

    for item in events:
        event_id = str(item.get("id", ""))
        if not event_id or event_id in seen_ids:
            continue
        seen_ids.add(event_id)

        title = item.get("adi", "").strip()
        if not title:
            continue

        raw_start = item.get("start_date", "")
        raw_end = item.get("end_date", "") or raw_start

        try:
            dtstart_val = format_all_day_date(raw_start)
            dtend_val = format_all_day_end_date(raw_end)
        except Exception:
            continue

        category = item.get("kategoriadi", "").strip()
        description_raw = item.get("aciklama", "").strip()
        event_link = item.get("link", "").strip()

        desc_parts = []
        if category:
            desc_parts.append(f"Category: {category}")
        if description_raw:
            desc_parts.append(description_raw)
        if event_link:
            desc_parts.append(f"Details: {event_link}")
        
        desc_parts.append("Auto-synced Bogazici University Academic Calendar")
        
        description = "\\n\\n".join([sanitize_ics_text(p) for p in desc_parts if p])
        summary = sanitize_ics_text(title)
        uid = f"boun-academic-{event_id}@bogazici.edu.tr"

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_utc}",
            f"DTSTART;VALUE=DATE:{dtstart_val}",
            f"DTEND;VALUE=DATE:{dtend_val}",
            f"SUMMARY:{summary}",
            f"DESCRIPTION:{description}",
            f"STATUS:CONFIRMED",
            "TRANSP:TRANSPARENT",
        ])

        if category:
            lines.append(f"CATEGORIES:{sanitize_ics_text(category)}")
        if event_link:
            lines.append(f"URL:{event_link}")

        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"

def generate_html_landing_page(
    events_en: list, 
    feed_metadata: list
) -> str:
    """Generate a clean, modern English landing page with ONLY ICS copy links."""
    now_str = datetime.now(TR_TZ).strftime("%B %d, %Y %H:%M (UTC+3)")
    
    sorted_en = sorted(events_en, key=lambda x: x.get("start_date", ""))
    today_str = datetime.now(TR_TZ).strftime("%Y-%m-%d")
    upcoming_en = [e for e in sorted_en if e.get("end_date", e.get("start_date", "")) >= today_str][:50]

    if not upcoming_en:
        upcoming_en = sorted_en[-50:]

    upcoming_json_en = json.dumps(upcoming_en, ensure_ascii=False)
    feeds_json = json.dumps(feed_metadata, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bogazici University Academic Calendar Feeds</title>
    <meta name="description" content="Official Bogazici University Academic Calendar category-specific ICS feeds for Google Calendar, Apple Calendar, and Microsoft Outlook.">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css">
    <style>
        :root {{
            --primary: #003366;
            --primary-light: #00509e;
            --accent: #2563eb;
            --accent-hover: #1d4ed8;
            --bg: #0f172a;
            --card-bg: #1e293b;
            --card-border: #334155;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --success: #10b981;
            --color-registration: #8b5cf6;
            --color-administrative: #ef4444;
            --color-instruction: #10b981;
            --color-sfl: #0ea5e9;
            --color-admission: #f59e0b;
        }}
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }}
        body {{
            background-color: var(--bg);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            line-height: 1.6;
        }}
        .container {{
            max-width: 1080px;
            margin: 0 auto;
            padding: 2.5rem 1.5rem;
            width: 100%;
        }}
        header {{
            text-align: center;
            margin-bottom: 2.5rem;
        }}
        .badge-live {{
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            background: rgba(16, 185, 129, 0.15);
            color: var(--success);
            border: 1px solid rgba(16, 185, 129, 0.3);
            padding: 0.35rem 0.85rem;
            border-radius: 9999px;
            font-size: 0.85rem;
            font-weight: 600;
            margin-bottom: 1rem;
        }}
        .pulse {{
            width: 8px;
            height: 8px;
            background: var(--success);
            border-radius: 50%;
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
            animation: pulse-animation 1.8s infinite;
        }}
        @keyframes pulse-animation {{
            0% {{ box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }}
            70% {{ box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }}
        }}
        h1 {{
            font-size: 2.25rem;
            font-weight: 800;
            letter-spacing: -0.025em;
            margin-bottom: 0.75rem;
            background: linear-gradient(135deg, #ffffff 0%, #94a3b8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}
        .subtitle {{
            color: var(--text-muted);
            font-size: 1.05rem;
            max-width: 720px;
            margin: 0 auto;
        }}
        .section-title {{
            font-size: 1.35rem;
            font-weight: 700;
            margin-bottom: 1.25rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            color: #f1f5f9;
        }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 1rem;
            padding: 1.75rem;
            margin-bottom: 2rem;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        }}
        .grid-feeds {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 1.25rem;
            margin-bottom: 1.5rem;
        }}
        .feed-box {{
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--card-border);
            border-radius: 0.75rem;
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: border-color 0.2s ease;
        }}
        .feed-box:hover {{
            border-color: #475569;
        }}
        .feed-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 0.5rem;
            gap: 0.5rem;
        }}
        .feed-header h3 {{
            font-size: 1.15rem;
            font-weight: 700;
            color: #f8fafc;
        }}
        .feed-box p {{
            color: var(--text-muted);
            font-size: 0.875rem;
            margin-bottom: 1.25rem;
            min-height: 2.6em;
        }}
        .url-box-container {{
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 0.5rem;
            padding: 0.5rem 0.75rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.5rem;
        }}
        .url-display {{
            font-size: 0.8rem;
            color: #94a3b8;
            word-break: break-all;
            font-family: monospace;
            flex: 1;
        }}
        .btn-copy {{
            background: var(--accent);
            color: white;
            padding: 0.45rem 0.85rem;
            border-radius: 0.375rem;
            font-size: 0.8rem;
            font-weight: 600;
            border: none;
            cursor: pointer;
            transition: background 0.2s ease;
            white-space: nowrap;
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
        }}
        .btn-copy:hover {{
            background: var(--accent-hover);
        }}
        
        /* Filter Bar */
        .filter-section {{
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--card-border);
            border-radius: 0.75rem;
            padding: 1rem 1.25rem;
            margin-bottom: 1.25rem;
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 1rem;
        }}
        .filter-label {{
            font-weight: 700;
            font-size: 0.95rem;
            color: #38bdf8;
        }}
        .filter-btn-clear {{
            background: var(--accent);
            color: white;
            padding: 0.35rem 0.9rem;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: 600;
            border: none;
            cursor: pointer;
            transition: background 0.2s ease;
        }}
        .filter-btn-clear:hover {{
            background: var(--accent-hover);
        }}
        .checkbox-group {{
            display: flex;
            flex-wrap: wrap;
            gap: 1.25rem;
            align-items: center;
        }}
        .checkbox-item {{
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            font-size: 0.9rem;
            font-weight: 500;
            cursor: pointer;
            user-select: none;
        }}
        .checkbox-item input[type="checkbox"] {{
            width: 16px;
            height: 16px;
            accent-color: var(--accent);
            cursor: pointer;
        }}
        .label-registration {{ color: var(--color-registration); }}
        .label-administrative {{ color: var(--color-administrative); }}
        .label-sfl {{ color: var(--color-sfl); }}
        .label-instruction {{ color: var(--color-instruction); }}
        .label-admission {{ color: var(--color-admission); }}

        .instructions {{
            margin-top: 1rem;
        }}
        .step-list {{
            list-style-position: inside;
            color: var(--text-muted);
            font-size: 0.9rem;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }}
        .events-preview-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            flex-wrap: wrap;
            gap: 0.5rem;
        }}
        .event-list {{
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            max-height: 520px;
            overflow-y: auto;
            padding-right: 0.5rem;
        }}
        .event-item {{
            background: rgba(15, 23, 42, 0.5);
            border: 1px solid var(--card-border);
            border-radius: 0.5rem;
            padding: 0.85rem 1rem;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 1rem;
        }}
        .event-item:hover {{
            border-color: #475569;
        }}
        .event-info {{
            flex: 1;
        }}
        .event-title {{
            font-weight: 600;
            font-size: 0.95rem;
            color: #f1f5f9;
            margin-bottom: 0.25rem;
        }}
        .event-date {{
            font-size: 0.8rem;
            color: #94a3b8;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }}
        .category-tag {{
            font-size: 0.7rem;
            font-weight: 700;
            padding: 0.2rem 0.5rem;
            border-radius: 0.25rem;
            white-space: nowrap;
        }}
        .tag-registration {{ background: rgba(139, 92, 246, 0.2); color: #c4b5fd; border: 1px solid rgba(139, 92, 246, 0.4); }}
        .tag-instruction {{ background: rgba(16, 185, 129, 0.2); color: #6ee7b7; border: 1px solid rgba(16, 185, 129, 0.4); }}
        .tag-administrative {{ background: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.4); }}
        .tag-sfl {{ background: rgba(14, 165, 233, 0.2); color: #7dd3fc; border: 1px solid rgba(14, 165, 233, 0.4); }}
        .tag-admission {{ background: rgba(245, 158, 11, 0.2); color: #fcd34d; border: 1px solid rgba(245, 158, 11, 0.4); }}
        .tag-other {{ background: rgba(148, 163, 184, 0.2); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.4); }}
        
        .badge-count {{
            font-size: 0.75rem;
            font-weight: 600;
            padding: 0.15rem 0.5rem;
            border-radius: 9999px;
            background: rgba(255, 255, 255, 0.1);
            color: #cbd5e1;
        }}
        
        footer {{
            text-align: center;
            padding: 2rem 0;
            color: var(--text-muted);
            font-size: 0.85rem;
            margin-top: auto;
        }}
        footer a {{
            color: #38bdf8;
            text-decoration: none;
        }}
        footer a:hover {{
            text-decoration: underline;
        }}
        .toast {{
            position: fixed;
            bottom: 2rem;
            right: 2rem;
            background: var(--success);
            color: white;
            padding: 0.75rem 1.25rem;
            border-radius: 0.5rem;
            font-weight: 600;
            font-size: 0.9rem;
            box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.5);
            display: none;
            z-index: 100;
        }}
    </style>
</head>
<body>

<div class="container">
    <header>
        <div class="badge-live">
            <span class="pulse"></span> Live Auto-Synced Feeds
        </div>
        <h1>Bogazici Academic Calendar Feeds</h1>
        <p class="subtitle">
            Official category-specific calendar feeds for Bogazici University. Copy any category link to subscribe in Google Calendar, Apple Calendar, or Outlook.
        </p>
    </header>

    <!-- Calendar Feeds Section -->
    <div class="card">
        <h2 class="section-title">Official Category Feeds</h2>
        <div class="grid-feeds" id="feeds-container">
            <!-- Dynamically populated via feeds metadata -->
        </div>

        <div class="instructions">
            <h2 class="section-title" style="font-size: 1.1rem; margin-top: 1rem;">How to Use the ICS Link</h2>
            <ol class="step-list">
                <li><strong>Google Calendar:</strong> Go to Other calendars (+) > From URL, paste the copied link, and click Add calendar.</li>
                <li><strong>Apple Calendar (iPhone / Mac):</strong> Go to File > New Calendar Subscription, paste the link, and choose your auto-refresh frequency.</li>
                <li><strong>Microsoft Outlook:</strong> Select Add Calendar > Subscribe from web, and paste the copied link.</li>
                <li><strong>Automatic Sync:</strong> University schedule updates are automatically synced to your subscribed calendar.</li>
            </ol>
        </div>
    </div>

    <!-- Upcoming Events Preview with Interactive Filtering -->
    <div class="card">
        <div class="events-preview-header">
            <h2 class="section-title" style="margin-bottom: 0;">Upcoming Events Preview</h2>
            <span style="font-size: 0.85rem; color: var(--text-muted);">Last Synchronized: {now_str}</span>
        </div>

        <!-- Filter Bar -->
        <div class="filter-section">
            <span class="filter-label">Filter Events:</span>
            <button class="filter-btn-clear" onclick="toggleAllFilters()" id="btn-toggle-all">Clear All</button>
            <div class="checkbox-group">
                <label class="checkbox-item label-registration">
                    <input type="checkbox" value="Registration" checked onchange="filterEvents()"> Registration
                </label>
                <label class="checkbox-item label-administrative">
                    <input type="checkbox" value="Administrative" checked onchange="filterEvents()"> Administrative
                </label>
                <label class="checkbox-item label-sfl">
                    <input type="checkbox" value="SFL" checked onchange="filterEvents()"> SFL / YADYOK
                </label>
                <label class="checkbox-item label-instruction">
                    <input type="checkbox" value="Instruction" checked onchange="filterEvents()"> Instruction
                </label>
                <label class="checkbox-item label-admission">
                    <input type="checkbox" value="Admission" checked onchange="filterEvents()"> Admission
                </label>
            </div>
        </div>

        <div class="event-list" id="upcoming-list">
            <!-- Populated via JS -->
        </div>
    </div>

    <footer>
        <p>
            Data sourced from the official <a href="https://akademiktakvim.bogazici.edu.tr/" target="_blank">Bogazici University Academic Calendar</a> portal.
        </p>
        <p style="margin-top: 0.5rem; opacity: 0.7;">
            Open-source project deployed via GitHub Actions and GitHub Pages.
        </p>
    </footer>
</div>

<div class="toast" id="toast">ICS link copied to clipboard</div>

<script>
    const feeds = {feeds_json};
    const eventsEn = {upcoming_json_en};
    
    function getFullIcsUrl(filename) {{
        return window.location.href.split('#')[0].split('?')[0].replace(/index\.html$/, '') + filename;
    }}

    function copyIcsUrl(filename) {{
        const url = getFullIcsUrl(filename);
        navigator.clipboard.writeText(url).then(() => {{
            showToast('ICS link copied to clipboard');
        }}).catch(() => {{
            prompt('ICS Link:', url);
        }});
    }}

    function showToast(msg) {{
        const toast = document.getElementById('toast');
        toast.innerText = msg;
        toast.style.display = 'block';
        setTimeout(() => {{ toast.style.display = 'none'; }}, 2500);
    }}

    function renderFeeds() {{
        const container = document.getElementById('feeds-container');
        container.innerHTML = feeds.map(f => `
            <div class="feed-box">
                <div>
                    <div class="feed-header">
                        <h3>${{f.title}}</h3>
                        <span class="badge-count">${{f.count}} events</span>
                    </div>
                    <p>${{f.description}}</p>
                </div>
                <div class="url-box-container">
                    <span class="url-display" id="url-${{f.filename}}">${{getFullIcsUrl(f.filename)}}</span>
                    <button class="btn-copy" onclick="copyIcsUrl('${{f.filename}}')">
                        <i class="fa-solid fa-copy"></i> Copy
                    </button>
                </div>
            </div>
        `).join('');
    }}

    function getSelectedCategories() {{
        const checkboxes = document.querySelectorAll('.checkbox-group input[type="checkbox"]:checked');
        return Array.from(checkboxes).map(cb => cb.value.toLowerCase());
    }}

    function toggleAllFilters() {{
        const checkboxes = document.querySelectorAll('.checkbox-group input[type="checkbox"]');
        const anyChecked = Array.from(checkboxes).some(cb => cb.checked);
        checkboxes.forEach(cb => cb.checked = !anyChecked);
        document.getElementById('btn-toggle-all').innerText = anyChecked ? 'Select All' : 'Clear All';
        filterEvents();
    }}

    function filterEvents() {{
        const selected = getSelectedCategories();
        const filtered = eventsEn.filter(ev => {{
            const cat = (ev.kategoriadi || '').toLowerCase();
            return selected.some(s => cat.includes(s));
        }});

        const container = document.getElementById('upcoming-list');
        if (filtered.length === 0) {{
            container.innerHTML = '<p style="color: var(--text-muted); padding: 1.5rem; text-align: center;">No matching events found for the selected categories.</p>';
            return;
        }}

        container.innerHTML = filtered.map(ev => {{
            const cat = ev.kategoriadi || 'General';
            let tagClass = 'tag-other';
            if (cat.includes('Registration')) tagClass = 'tag-registration';
            else if (cat.includes('Instruction')) tagClass = 'tag-instruction';
            else if (cat.includes('Administrative')) tagClass = 'tag-administrative';
            else if (cat.includes('SFL') || cat.includes('YADYOK')) tagClass = 'tag-sfl';
            else if (cat.includes('Admission')) tagClass = 'tag-admission';

            const dateStr = ev.tarih_bitis && ev.tarih_bitis !== ev.tarih ? `${{ev.tarih}} - ${{ev.tarih_bitis}}` : (ev.tarih || ev.start_date.split(' ')[0]);

            return `
                <div class="event-item">
                    <div class="event-info">
                        <div class="event-title">${{ev.adi}}</div>
                        <div class="event-date">
                            <i class="fa-regular fa-calendar"></i> ${{dateStr}}
                        </div>
                    </div>
                    <span class="category-tag ${{tagClass}}">${{cat}}</span>
                </div>
            `;
        }}).join('');
    }}

    window.addEventListener('DOMContentLoaded', () => {{
        renderFeeds();
        filterEvents();
    }});
</script>

</body>
</html>
"""

def main():
    output_dir = Path(os.environ.get("OUTPUT_DIR", "dist"))
    output_dir.mkdir(parents=True, exist_ok=True)

    current_year = datetime.now().year
    start_date = f"{current_year - 1}-01-01"
    end_date = f"{current_year + 2}-12-31"

    print(f"Fetching Bogazici Academic Calendar ({start_date} to {end_date})...")

    events_en = fetch_events(BASE_URL_EN, start_date, end_date)
    print(f"Fetched {len(events_en)} events in English.")

    events_tr = fetch_events(BASE_URL_TR, start_date, end_date)
    print(f"Fetched {len(events_tr)} events in Turkish.")

    if not events_en and not events_tr:
        print("Warning: No events fetched. Check network or API.")
        return

    feed_metadata = []

    # Generate exact 1-to-1 category-specific feeds (no complete feed)
    for cat in CATEGORIES:
        kat_id = cat["kat_id"]

        # English Category Feed
        filtered_en = [e for e in events_en if str(e.get("kat_id", "")) == kat_id]
        if filtered_en:
            cat_ics_en = generate_ics(
                filtered_en,
                cal_name=f"Bogazici Academic Calendar - {cat['title']}",
                cal_desc=f"Bogazici University {cat['title']} Calendar",
                lang="en"
            )
            fn_en = f"{cat['slug']}.ics"
            with open(output_dir / fn_en, "w", encoding="utf-8") as f:
                f.write(cat_ics_en)
            print(f"Saved category feed: {output_dir / fn_en} ({len(filtered_en)} events)")

            feed_metadata.append({
                "filename": fn_en,
                "title": cat["title"],
                "description": cat["description"],
                "count": len(filtered_en)
            })

        # Turkish Category Feed
        filtered_tr = [e for e in events_tr if str(e.get("kat_id", "")) == kat_id]
        if filtered_tr:
            cat_ics_tr = generate_ics(
                filtered_tr,
                cal_name=f"Bogazici Akademik Takvim - {cat['title_tr']}",
                cal_desc=f"Bogazici Universitesi {cat['title_tr']} Takvimi",
                lang="tr"
            )
            fn_tr = f"{cat['slug_tr']}.ics"
            with open(output_dir / fn_tr, "w", encoding="utf-8") as f:
                f.write(cat_ics_tr)
            print(f"Saved Turkish category feed: {output_dir / fn_tr} ({len(filtered_tr)} events)")

    # Save JSON files
    with open(output_dir / "events-en.json", "w", encoding="utf-8") as f:
        json.dump(events_en, f, ensure_ascii=False, indent=2)
    with open(output_dir / "events-tr.json", "w", encoding="utf-8") as f:
        json.dump(events_tr, f, ensure_ascii=False, indent=2)

    # Generate HTML landing page
    html_content = generate_html_landing_page(events_en, feed_metadata)
    with open(output_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Saved landing page {output_dir / 'index.html'}")

    print("Sync completed successfully!")

if __name__ == "__main__":
    main()
