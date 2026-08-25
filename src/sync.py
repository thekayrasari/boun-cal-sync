#!/usr/bin/env python3
"""
Bogazici University Academic Calendar Sync Script
Fetches academic calendar from https://akademiktakvim.bogazici.edu.tr/
Generates standard RFC 5545 compliant iCalendar (.ics) files and a web landing page.
Zero external dependencies - runs on standard Python 3.8+.
"""

import os
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path
import re
import html

BASE_URL_TR = "https://akademiktakvim.bogazici.edu.tr/tr/json"
BASE_URL_EN = "https://akademiktakvim.bogazici.edu.tr/en/json"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

TR_TZ = timezone(timedelta(hours=3))

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
    """
    In RFC 5545, all-day DTEND is exclusive (day after the event ends).
    """
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
    events_tr: list
) -> str:
    """Generate a responsive, clean English landing page with 1-click subscription buttons."""
    now_str = datetime.now(TR_TZ).strftime("%B %d, %Y %H:%M (UTC+3)")
    
    sorted_en = sorted(events_en, key=lambda x: x.get("start_date", ""))
    today_str = datetime.now(TR_TZ).strftime("%Y-%m-%d")
    upcoming_en = [e for e in sorted_en if e.get("end_date", e.get("start_date", "")) >= today_str][:20]

    if not upcoming_en:
        upcoming_en = sorted_en[-20:]

    upcoming_json_en = json.dumps(upcoming_en, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bogazici University Academic Calendar Sync</title>
    <meta name="description" content="Auto-synced Bogazici University Academic Calendar feeds for Google Calendar, Apple Calendar, and Microsoft Outlook.">
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
            --badge-registration: #8b5cf6;
            --badge-instruction: #10b981;
            --badge-admin: #ef4444;
            --badge-sfl: #0ea5e9;
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
            max-width: 1000px;
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
            font-size: 1.1rem;
            max-width: 650px;
            margin: 0 auto;
        }}
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 1rem;
            padding: 1.75rem;
            margin-bottom: 2rem;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        }}
        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
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
        }}
        .feed-box h3 {{
            font-size: 1.2rem;
            font-weight: 700;
            margin-bottom: 0.35rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        .feed-box p {{
            color: var(--text-muted);
            font-size: 0.875rem;
            margin-bottom: 1rem;
        }}
        .btn-group {{
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }}
        .btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
            padding: 0.65rem 1rem;
            border-radius: 0.5rem;
            font-size: 0.9rem;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.2s ease;
            border: none;
        }}
        .btn-google {{
            background: #ea4335;
            color: white;
        }}
        .btn-google:hover {{
            background: #d33426;
        }}
        .btn-apple {{
            background: #334155;
            color: white;
        }}
        .btn-apple:hover {{
            background: #475569;
        }}
        .btn-copy {{
            background: rgba(255, 255, 255, 0.08);
            color: #cbd5e1;
            border: 1px solid rgba(255, 255, 255, 0.15);
        }}
        .btn-copy:hover {{
            background: rgba(255, 255, 255, 0.15);
            color: white;
        }}
        .url-display {{
            background: #0f172a;
            border: 1px solid #334155;
            padding: 0.5rem 0.75rem;
            border-radius: 0.375rem;
            font-size: 0.75rem;
            color: #94a3b8;
            word-break: break-all;
            margin-top: 0.5rem;
            font-family: monospace;
        }}
        .instructions {{
            margin-top: 1rem;
        }}
        .instructions h4 {{
            font-size: 1rem;
            margin-bottom: 0.75rem;
            color: #e2e8f0;
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
            max-height: 450px;
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
        .tag-admin {{ background: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.4); }}
        .tag-sfl {{ background: rgba(14, 165, 233, 0.2); color: #7dd3fc; border: 1px solid rgba(14, 165, 233, 0.4); }}
        .tag-other {{ background: rgba(148, 163, 184, 0.2); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.4); }}
        
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
            <span class="pulse"></span> Live Auto-Synced Feed
        </div>
        <h1>Bogazici Academic Calendar</h1>
        <p class="subtitle">
            Subscribe to official Bogazici University academic events, exams, and registration deadlines with 1-click sync for Google Calendar, Apple Calendar, and Outlook.
        </p>
    </header>

    <div class="card">
        <div class="grid">
            <!-- English Calendar -->
            <div class="feed-box">
                <div>
                    <h3><i class="fa-solid fa-globe" style="color: #38bdf8;"></i> English Feed</h3>
                    <p>Complete academic calendar translated into English for international students and researchers.</p>
                </div>
                <div class="btn-group">
                    <button class="btn btn-google" onclick="subscribeGoogle('academic-en.ics')">
                        <i class="fa-brands fa-google"></i> Add to Google Calendar
                    </button>
                    <button class="btn btn-apple" onclick="subscribeApple('academic-en.ics')">
                        <i class="fa-brands fa-apple"></i> Add to Apple Calendar
                    </button>
                    <button class="btn btn-copy" onclick="copyIcsUrl('academic-en.ics')">
                        <i class="fa-solid fa-copy"></i> Copy .ics Link
                    </button>
                    <div class="url-display" id="url-academic-en.ics">.../academic-en.ics</div>
                </div>
            </div>

            <!-- Turkish Calendar -->
            <div class="feed-box">
                <div>
                    <h3><i class="fa-solid fa-calendar-check" style="color: #34d399;"></i> Turkish Feed</h3>
                    <p>Original academic calendar feed with all Turkish titles and descriptions.</p>
                </div>
                <div class="btn-group">
                    <button class="btn btn-google" onclick="subscribeGoogle('academic.ics')">
                        <i class="fa-brands fa-google"></i> Add to Google Calendar
                    </button>
                    <button class="btn btn-apple" onclick="subscribeApple('academic.ics')">
                        <i class="fa-brands fa-apple"></i> Add to Apple Calendar
                    </button>
                    <button class="btn btn-copy" onclick="copyIcsUrl('academic.ics')">
                        <i class="fa-solid fa-copy"></i> Copy .ics Link
                    </button>
                    <div class="url-display" id="url-academic.ics">.../academic.ics</div>
                </div>
            </div>
        </div>

        <div class="instructions">
            <h4>Subscription Instructions</h4>
            <ol class="step-list">
                <li><strong>Google Calendar:</strong> Click "Add to Google Calendar" to automatically open and import the feed into your Google account.</li>
                <li><strong>Apple Calendar (iOS / macOS):</strong> Click "Add to Apple Calendar" to prompt the system calendar subscription dialog.</li>
                <li><strong>Automatic Updates:</strong> Your calendar client will periodically fetch and reflect any schedule revisions made by the university.</li>
            </ol>
        </div>
    </div>

    <!-- Upcoming Events Preview -->
    <div class="card">
        <div class="events-preview-header">
            <h3><i class="fa-solid fa-clock-rotate-left"></i> Upcoming Events</h3>
            <span style="font-size: 0.85rem; color: var(--text-muted);">Last Synchronized: {now_str}</span>
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

<div class="toast" id="toast">Link copied to clipboard!</div>

<script>
    const eventsEn = {upcoming_json_en};
    
    function getFullIcsUrl(filename) {{
        return window.location.href.split('#')[0].split('?')[0].replace(/index\.html$/, '') + filename;
    }}

    function getWebcalUrl(filename) {{
        const icsUrl = getFullIcsUrl(filename);
        return icsUrl.replace(/^https?:\/\//i, 'webcal://');
    }}

    function updateUrlDisplays() {{
        ['academic-en.ics', 'academic.ics'].forEach(fn => {{
            const el = document.getElementById('url-' + fn);
            if (el) {{
                el.innerText = getFullIcsUrl(fn);
            }}
        }});
    }}

    function subscribeGoogle(filename) {{
        const fullUrl = encodeURIComponent(getFullIcsUrl(filename));
        window.open('https://calendar.google.com/calendar/render?cid=' + fullUrl, '_blank');
    }}

    function subscribeApple(filename) {{
        window.location.href = getWebcalUrl(filename);
    }}

    function copyIcsUrl(filename) {{
        const url = getFullIcsUrl(filename);
        navigator.clipboard.writeText(url).then(() => {{
            showToast('ICS link copied to clipboard!');
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

    function renderEvents() {{
        const container = document.getElementById('upcoming-list');
        if (!eventsEn || eventsEn.length === 0) {{
            container.innerHTML = '<p style="color: var(--text-muted); padding: 1rem;">No upcoming events found.</p>';
            return;
        }}

        container.innerHTML = eventsEn.map(ev => {{
            const cat = ev.kategoriadi || 'General';
            let tagClass = 'tag-other';
            if (cat.includes('Registration') || cat.includes('Admission')) tagClass = 'tag-registration';
            else if (cat.includes('Instruction')) tagClass = 'tag-instruction';
            else if (cat.includes('Administrative')) tagClass = 'tag-admin';
            else if (cat.includes('SFL') || cat.includes('YADYOK')) tagClass = 'tag-sfl';

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
        updateUrlDisplays();
        renderEvents();
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

    # Generate main ICS files
    ics_en = generate_ics(
        events_en,
        cal_name="Bogazici University Academic Calendar",
        cal_desc="Official Bogazici University Academic Calendar (Auto-synced)",
        lang="en"
    )
    with open(output_dir / "academic-en.ics", "w", encoding="utf-8") as f:
        f.write(ics_en)
    print(f"Saved {output_dir / 'academic-en.ics'}")

    ics_tr = generate_ics(
        events_tr, 
        cal_name="Bogazici University Academic Calendar (TR)",
        cal_desc="Official Bogazici University Academic Calendar (TR)",
        lang="tr"
    )
    with open(output_dir / "academic.ics", "w", encoding="utf-8") as f:
        f.write(ics_tr)
    print(f"Saved {output_dir / 'academic.ics'}")

    # Generate category-specific calendars
    categories_en = {
        "registration": ["Registration", "Admission"],
        "sfl": ["SFL", "YADYOK"],
        "instruction": ["Instruction"]
    }
    for slug, cat_list in categories_en.items():
        filtered = [e for e in events_en if any(c.lower() in e.get("kategoriadi", "").lower() for c in cat_list)]
        if filtered:
            cat_ics = generate_ics(
                filtered,
                cal_name=f"Bogazici Academic Calendar - {cat_list[0]}",
                cal_desc=f"Bogazici University {', '.join(cat_list)} Calendar",
                lang="en"
            )
            with open(output_dir / f"academic-{slug}.ics", "w", encoding="utf-8") as f:
                f.write(cat_ics)
            print(f"Saved category feed: {output_dir / f'academic-{slug}.ics'} ({len(filtered)} events)")

    # Save JSON files
    with open(output_dir / "events-en.json", "w", encoding="utf-8") as f:
        json.dump(events_en, f, ensure_ascii=False, indent=2)
    with open(output_dir / "events-tr.json", "w", encoding="utf-8") as f:
        json.dump(events_tr, f, ensure_ascii=False, indent=2)

    # Generate HTML landing page
    html_content = generate_html_landing_page(events_en, events_tr)
    with open(output_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Saved landing page {output_dir / 'index.html'}")

    print("Sync completed successfully!")

if __name__ == "__main__":
    main()
