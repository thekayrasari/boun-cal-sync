#!/usr/bin/env python3
"""
Boğaziçi Üniversitesi Akademik Takvim Senkronizasyon Scripti
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

# Turkey timezone offset UTC+3
TR_TZ = timezone(timedelta(hours=3))

def fetch_events(base_url: str, start_date: str, end_date: str) -> list:
    """Fetch calendar events from Boğaziçi API for a given date range."""
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

def generate_ics(events: list, cal_name: str, cal_desc: str, lang: str = "tr") -> str:
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

        # Build clean description
        desc_parts = []
        if category:
            desc_parts.append(f"Kategori: {category}" if lang == "tr" else f"Category: {category}")
        if description_raw:
            desc_parts.append(description_raw)
        if event_link:
            desc_parts.append(f"Detay: {event_link}" if lang == "tr" else f"Details: {event_link}")
        
        desc_parts.append(
            "Otomatik Güncellenen Boğaziçi Akademik Takvimi" 
            if lang == "tr" else 
            "Auto-synced Boğaziçi University Academic Calendar"
        )
        
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
            "TRANSP:TRANSPARENT",  # Does not block time as busy
        ])

        if category:
            lines.append(f"CATEGORIES:{sanitize_ics_text(category)}")
        if event_link:
            lines.append(f"URL:{event_link}")

        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"

def generate_html_landing_page(
    events_tr: list, 
    events_en: list, 
    repo_url: str = "", 
    github_pages_url: str = ""
) -> str:
    """Generate a responsive, aesthetic landing page with 1-click subscription buttons."""
    now_str = datetime.now(TR_TZ).strftime("%d.%m.%Y %H:%M (TSİ)")
    
    # Sort events by start date
    sorted_tr = sorted(events_tr, key=lambda x: x.get("start_date", ""))
    sorted_en = sorted(events_en, key=lambda x: x.get("start_date", ""))

    # Select upcoming events (from today onwards)
    today_str = datetime.now(TR_TZ).strftime("%Y-%m-%d")
    upcoming_tr = [e for e in sorted_tr if e.get("end_date", e.get("start_date", "")) >= today_str][:20]
    upcoming_en = [e for e in sorted_en if e.get("end_date", e.get("start_date", "")) >= today_str][:20]

    # If no upcoming events in current range, take the last 20
    if not upcoming_tr:
        upcoming_tr = sorted_tr[-20:]
    if not upcoming_en:
        upcoming_en = sorted_en[-20:]

    upcoming_json_tr = json.dumps(upcoming_tr, ensure_ascii=False)
    upcoming_json_en = json.dumps(upcoming_en, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="tr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Boğaziçi Üniversitesi Akademik Takvim Senkronizasyonu</title>
    <meta name="description" content="Boğaziçi Üniversitesi Akademik Takvimi'ni Google Calendar, Apple Calendar ve Outlook ile otomatik senkronize edin.">
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
            --badge-kayit: #8b5cf6;
            --badge-egitim: #10b981;
            --badge-idari: #ef4444;
            --badge-yadyok: #0ea5e9;
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
            padding: 2rem 1.5rem;
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
        .tag-kayit {{ background: rgba(139, 92, 246, 0.2); color: #c4b5fd; border: 1px solid rgba(139, 92, 246, 0.4); }}
        .tag-egitim {{ background: rgba(16, 185, 129, 0.2); color: #6ee7b7; border: 1px solid rgba(16, 185, 129, 0.4); }}
        .tag-idari {{ background: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.4); }}
        .tag-yadyok {{ background: rgba(14, 165, 233, 0.2); color: #7dd3fc; border: 1px solid rgba(14, 165, 233, 0.4); }}
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
            <span class="pulse"></span> Otomatik Güncellenen Akış
        </div>
        <h1>Boğaziçi Akademik Takvim</h1>
        <p class="subtitle">
            Resmi akademik takvim etkinliklerini Google Calendar, Apple Calendar ve Outlook takviminize tek tıkla ekleyin, değişiklikler otomatik yansısın.
        </p>
    </header>

    <div class="card">
        <div class="grid">
            <!-- Türkçe Takvim -->
            <div class="feed-box">
                <div>
                    <h3><i class="fa-solid fa-calendar-check" style="color: #38bdf8;"></i> Türkçe Takvim</h3>
                    <p>Tüm akademik, idari, kayıt ve sınav tarihlerini içeren ana takvim akışı.</p>
                </div>
                <div class="btn-group">
                    <button class="btn btn-google" onclick="subscribeGoogle('academic.ics')">
                        <i class="fa-brands fa-google"></i> Google Calendar'a Ekle
                    </button>
                    <button class="btn btn-apple" onclick="subscribeApple('academic.ics')">
                        <i class="fa-brands fa-apple"></i> Apple Takvim'e Ekle
                    </button>
                    <button class="btn btn-copy" onclick="copyIcsUrl('academic.ics')">
                        <i class="fa-solid fa-copy"></i> .ics Linkini Kopyala
                    </button>
                    <div class="url-display" id="url-academic.ics">.../academic.ics</div>
                </div>
            </div>

            <!-- English Calendar -->
            <div class="feed-box">
                <div>
                    <h3><i class="fa-solid fa-globe" style="color: #34d399;"></i> English Calendar</h3>
                    <p>Complete academic calendar feed translated in English for international students.</p>
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
        </div>

        <div class="instructions">
            <h4>💡 Nasıl Çalışır?</h4>
            <ol class="step-list">
                <li><strong>Google Calendar:</strong> "Google Calendar'a Ekle" butonuna bastığınızda Google Takvim açılır ve URL otomatik eklenir.</li>
                <li><strong>iPhone / Mac (Apple Calendar):</strong> "Apple Takvim'e Ekle" butonuna tıkladığınızda iOS/macOS Takvim uygulaması açılır ve takvim aboneliğiniz başlatılır.</li>
                <li><strong>Otomatik Güncelleme:</strong> Takviminiz, Boğaziçi Üniversitesi'ndeki tarih güncellemelerini arka planda periyodik olarak kontrol edip yeniler.</li>
            </ol>
        </div>
    </div>

    <!-- Yaklaşan Etkinlikler Önizleme -->
    <div class="card">
        <div class="events-preview-header">
            <h3><i class="fa-solid fa-clock-rotate-left"></i> Yaklaşan Etkinlikler</h3>
            <span style="font-size: 0.85rem; color: var(--text-muted);">Son Senkronizasyon: {now_str}</span>
        </div>
        <div class="event-list" id="upcoming-list">
            <!-- Populated via JS -->
        </div>
    </div>

    <footer>
        <p>
            Veriler resmi <a href="https://akademiktakvim.bogazici.edu.tr/" target="_blank">Boğaziçi Üniversitesi Akademik Takvim</a> portalından alınmaktadır.
        </p>
        <p style="margin-top: 0.5rem; opacity: 0.7;">
            Açık kaynaklı proje • GitHub Actions & Pages ile barındırılmaktadır.
        </p>
    </footer>
</div>

<div class="toast" id="toast">Link panoya kopyalandı!</div>

<script>
    const eventsTr = {upcoming_json_tr};
    
    function getFullIcsUrl(filename) {{
        return window.location.href.split('#')[0].split('?')[0].replace(/index\.html$/, '') + filename;
    }}

    function getWebcalUrl(filename) {{
        const icsUrl = getFullIcsUrl(filename);
        return icsUrl.replace(/^https?:\/\//i, 'webcal://');
    }}

    function updateUrlDisplays() {{
        ['academic.ics', 'academic-en.ics'].forEach(fn => {{
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
            showToast('ICS bağlantısı kopyalandı!');
        }}).catch(() => {{
            prompt('ICS Bağlantısı:', url);
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
        if (!eventsTr || eventsTr.length === 0) {{
            container.innerHTML = '<p style="color: var(--text-muted); padding: 1rem;">Gelecek etkinlik bulunamadı.</p>';
            return;
        }}

        container.innerHTML = eventsTr.map(ev => {{
            const cat = ev.kategoriadi || 'Genel';
            let tagClass = 'tag-other';
            if (cat.includes('Kayıt') || cat.includes('Registration')) tagClass = 'tag-kayit';
            else if (cat.includes('Eğitim') || cat.includes('Instruction')) tagClass = 'tag-egitim';
            else if (cat.includes('İdari') || cat.includes('Administrative')) tagClass = 'tag-idari';
            else if (cat.includes('YADYOK') || cat.includes('SFL')) tagClass = 'tag-yadyok';

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
    # Target output directory (e.g. dist/ or current directory)
    output_dir = Path(os.environ.get("OUTPUT_DIR", "dist"))
    output_dir.mkdir(parents=True, exist_ok=True)

    current_year = datetime.now().year
    start_date = f"{current_year - 1}-01-01"
    end_date = f"{current_year + 2}-12-31"

    print(f"🔄 Fetching Boğaziçi Academic Calendar ({start_date} to {end_date})...")

    # Fetch Turkish & English events
    events_tr = fetch_events(BASE_URL_TR, start_date, end_date)
    print(f"✅ Fetched {len(events_tr)} events in Turkish.")

    events_en = fetch_events(BASE_URL_EN, start_date, end_date)
    print(f"✅ Fetched {len(events_en)} events in English.")

    if not events_tr and not events_en:
        print("⚠️ Warning: No events fetched. Check network or API.")
        return

    # Generate main ICS files
    ics_tr = generate_ics(
        events_tr, 
        cal_name="Boğaziçi Üniversitesi Akademik Takvim",
        cal_desc="Resmi Boğaziçi Üniversitesi Akademik Takvimi (Otomatik Senkronize)",
        lang="tr"
    )
    with open(output_dir / "academic.ics", "w", encoding="utf-8") as f:
        f.write(ics_tr)
    print(f"💾 Saved {output_dir / 'academic.ics'}")

    ics_en = generate_ics(
        events_en,
        cal_name="Boğaziçi University Academic Calendar",
        cal_desc="Official Boğaziçi University Academic Calendar (Auto-synced)",
        lang="en"
    )
    with open(output_dir / "academic-en.ics", "w", encoding="utf-8") as f:
        f.write(ics_en)
    print(f"💾 Saved {output_dir / 'academic-en.ics'}")

    # Generate category-specific calendars
    categories_tr = {
        "kayit": ["Kayıt", "Başvuru"],
        "yadyok": ["YADYOK"],
        "egitim": ["Eğitim-Öğretim"]
    }
    for slug, cat_list in categories_tr.items():
        filtered = [e for e in events_tr if any(c.lower() in e.get("kategoriadi", "").lower() for c in cat_list)]
        if filtered:
            cat_ics = generate_ics(
                filtered,
                cal_name=f"Boğaziçi Akademik Takvim - {cat_list[0]}",
                cal_desc=f"Boğaziçi Üniversitesi {', '.join(cat_list)} Takvimi",
                lang="tr"
            )
            with open(output_dir / f"academic-{slug}.ics", "w", encoding="utf-8") as f:
                f.write(cat_ics)
            print(f"💾 Saved category feed: {output_dir / f'academic-{slug}.ics'} ({len(filtered)} events)")

    # Save JSON files as well for API consumers / frontend
    with open(output_dir / "events-tr.json", "w", encoding="utf-8") as f:
        json.dump(events_tr, f, ensure_ascii=False, indent=2)
    with open(output_dir / "events-en.json", "w", encoding="utf-8") as f:
        json.dump(events_en, f, ensure_ascii=False, indent=2)

    # Generate HTML landing page
    html_content = generate_html_landing_page(events_tr, events_en)
    with open(output_dir / "index.html", "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"💾 Saved landing page {output_dir / 'index.html'}")

    print("🎉 Sync completed successfully!")

if __name__ == "__main__":
    main()
