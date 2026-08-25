# Bogazici University Academic Calendar Sync Script (PowerShell)
# For local execution and generating category-specific ICS/JSON/HTML assets on Windows

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$OutputDir = Join-Path $PSScriptRoot "dist"
if (!(Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

$CurrentYear = (Get-Date).Year
$StartDate = "$($CurrentYear - 1)-01-01"
$EndDate = "$($CurrentYear + 2)-12-31"

Write-Host "Fetching Bogazici Academic Calendar ($StartDate - $EndDate)..."

function Fetch-Events($Url) {
    try {
        $resp = Invoke-RestMethod -Uri $Url -Method Get -Headers @{ "User-Agent" = "Mozilla/5.0" }
        return $resp
    } catch {
        Write-Host "Error ($Url): $_"
        return @()
    }
}

$UrlEn = "https://akademiktakvim.bogazici.edu.tr/en/json?type=4&date=$StartDate&last_date=$EndDate"
$UrlTr = "https://akademiktakvim.bogazici.edu.tr/tr/json?type=4&date=$StartDate&last_date=$EndDate"

$EventsEn = Fetch-Events -Url $UrlEn
Write-Host "Fetched $($EventsEn.Count) English events."

$EventsTr = Fetch-Events -Url $UrlTr
Write-Host "Fetched $($EventsTr.Count) Turkish events."

function ConvertTo-Ics($Events, $CalName, $CalDesc, $Lang) {
    $nowUtc = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
    $sb = New-Object System.Text.StringBuilder
    [void]$sb.AppendLine("BEGIN:VCALENDAR")
    [void]$sb.AppendLine("VERSION:2.0")
    [void]$sb.AppendLine("PRODID:-//Bogazici University//Academic Calendar Sync//EN")
    [void]$sb.AppendLine("CALSCALE:GREGORIAN")
    [void]$sb.AppendLine("METHOD:PUBLISH")
    [void]$sb.AppendLine("X-WR-CALNAME:$CalName")
    [void]$sb.AppendLine("X-WR-CALDESC:$CalDesc")
    [void]$sb.AppendLine("X-WR-TIMEZONE:Europe/Istanbul")
    [void]$sb.AppendLine("REFRESH-INTERVAL;VALUE=DURATION:P1D")
    [void]$sb.AppendLine("X-PUBLISHED-TTL:P1D")

    $seen = New-Object System.Collections.Generic.HashSet[string]

    foreach ($ev in $Events) {
        $id = [string]$ev.id
        if ([string]::IsNullOrWhiteSpace($id) -or $seen.Contains($id)) { continue }
        [void]$seen.Add($id)

        $title = [string]$ev.adi
        if ([string]::IsNullOrWhiteSpace($title)) { continue }

        $startStr = [string]$ev.start_date
        $endStr = [string]$ev.end_date
        if ([string]::IsNullOrWhiteSpace($endStr)) { $endStr = $startStr }

        try {
            $startDate = [DateTime]::Parse($startStr.Split(' ')[0])
            $endDate = [DateTime]::Parse($endStr.Split(' ')[0]).AddDays(1)
        } catch {
            continue
        }

        $dtstart = $startDate.ToString("yyyyMMdd")
        $dtend = $endDate.ToString("yyyyMMdd")

        $category = [string]$ev.kategoriadi
        $descRaw = [string]$ev.aciklama
        $link = [string]$ev.link

        $descParts = @()
        if ($category) { $descParts += "Category: $category" }
        if ($descRaw) { $descParts += $descRaw }
        if ($link) { $descParts += "Details: $link" }
        $descParts += "Auto-synced Bogazici University Academic Calendar"

        $descText = ($descParts -join "\n\n") -replace ";", "\;" -replace ",", "\,"
        $summaryText = $title -replace ";", "\;" -replace ",", "\,"
        $uid = "boun-academic-$id@bogazici.edu.tr"

        [void]$sb.AppendLine("BEGIN:VEVENT")
        [void]$sb.AppendLine("UID:$uid")
        [void]$sb.AppendLine("DTSTAMP:$nowUtc")
        [void]$sb.AppendLine("DTSTART;VALUE=DATE:$dtstart")
        [void]$sb.AppendLine("DTEND;VALUE=DATE:$dtend")
        [void]$sb.AppendLine("SUMMARY:$summaryText")
        [void]$sb.AppendLine("DESCRIPTION:$descText")
        [void]$sb.AppendLine("STATUS:CONFIRMED")
        [void]$sb.AppendLine("TRANSP:TRANSPARENT")
        if ($category) { [void]$sb.AppendLine("CATEGORIES:$category") }
        if ($link) { [void]$sb.AppendLine("URL:$link") }
        [void]$sb.AppendLine("END:VEVENT")
    }

    [void]$sb.AppendLine("END:VCALENDAR")
    return $sb.ToString()
}

$feedsList = @()

$officialCategories = @(
    @{
        kat_id = "29"
        slug = "registration"
        slug_tr = "kayit"
        title = "Registration"
        title_tr = "Kayıt"
        description = "Course registration windows, advisor approvals, add/drop periods, and fee payment deadlines."
    },
    @{
        kat_id = "24"
        slug = "administrative"
        slug_tr = "idari"
        title = "Administrative"
        title_tr = "İdari"
        description = "Administrative board meetings (ÜYK/FKK), official university deadlines, and department submissions."
    },
    @{
        kat_id = "23"
        slug = "instruction"
        slug_tr = "egitim"
        title = "Instruction & Exams"
        title_tr = "Eğitim-Öğretim"
        description = "First and last days of classes, midterm & final exam periods, grade submissions, and semester dates."
    },
    @{
        kat_id = "25"
        slug = "sfl"
        slug_tr = "yadyok"
        title = "School of Foreign Languages (SFL / YADYOK)"
        title_tr = "YADYOK"
        description = "BUEPT English proficiency exams, placement tests, preparatory classes terms, and result announcements."
    },
    @{
        kat_id = "28"
        slug = "admission"
        slug_tr = "basvuru"
        title = "Admission & Applications"
        title_tr = "Başvuru"
        description = "Undergraduate/graduate applications, double major/minor transfers, and exchange program deadlines."
    }
)

foreach ($cat in $officialCategories) {
    $katId = $cat.kat_id

    # English Category Feed
    $filteredEn = $EventsEn | Where-Object { [string]$_.kat_id -eq $katId }
    if ($filteredEn.Count -gt 0) {
        $catIcsEn = ConvertTo-Ics -Events $filteredEn -CalName "Bogazici Academic Calendar - $($cat.title)" -CalDesc "Bogazici University $($cat.title) Calendar" -Lang "en"
        $fnEn = "$($cat.slug).ics"
        [System.IO.File]::WriteAllText((Join-Path $OutputDir $fnEn), $catIcsEn, [System.Text.Encoding]::UTF8)
        Write-Host "Saved category feed: $fnEn ($($filteredEn.Count) events)"

        $feedsList += @{
            filename = $fnEn
            title = $cat.title
            description = $cat.description
            count = $filteredEn.Count
        }
    }

    # Turkish Category Feed
    $filteredTr = $EventsTr | Where-Object { [string]$_.kat_id -eq $katId }
    if ($filteredTr.Count -gt 0) {
        $catIcsTr = ConvertTo-Ics -Events $filteredTr -CalName "Bogazici Akademik Takvim - $($cat.title_tr)" -CalDesc "Bogazici Universitesi $($cat.title_tr) Takvimi" -Lang "tr"
        $fnTr = "$($cat.slug_tr).ics"
        [System.IO.File]::WriteAllText((Join-Path $OutputDir $fnTr), $catIcsTr, [System.Text.Encoding]::UTF8)
        Write-Host "Saved Turkish category feed: $fnTr ($($filteredTr.Count) events)"
    }
}

# JSON files
$EventsEn | ConvertTo-Json -Depth 5 | Out-File -FilePath (Join-Path $OutputDir "events-en.json") -Encoding utf8
$EventsTr | ConvertTo-Json -Depth 5 | Out-File -FilePath (Join-Path $OutputDir "events-tr.json") -Encoding utf8

# Generate HTML
$nowStr = (Get-Date).ToString("MMMM dd, yyyy HH:mm") + " (UTC+3)"
$sortedEn = $EventsEn | Sort-Object { $_.start_date }
$todayStr = (Get-Date).ToString("yyyy-MM-dd")
$upcomingEn = $sortedEn | Where-Object { $_.end_date -ge $todayStr -or $_.start_date -ge $todayStr } | Select-Object -First 50
if (-not $upcomingEn -or $upcomingEn.Count -eq 0) {
    $upcomingEn = $sortedEn | Select-Object -Last 50
}
$upcomingJsonEn = $upcomingEn | ConvertTo-Json -Depth 5 -Compress
$feedsJson = $feedsList | ConvertTo-Json -Depth 3 -Compress

$htmlContent = @"
<!DOCTYPE html>
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
        :root {
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
        }
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }
        body {
            background-color: var(--bg);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            line-height: 1.6;
        }
        .container {
            max-width: 1080px;
            margin: 0 auto;
            padding: 2.5rem 1.5rem;
            width: 100%;
        }
        header {
            text-align: center;
            margin-bottom: 2.5rem;
        }
        .badge-live {
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
        }
        .pulse {
            width: 8px;
            height: 8px;
            background: var(--success);
            border-radius: 50%;
            box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7);
            animation: pulse-animation 1.8s infinite;
        }
        @keyframes pulse-animation {
            0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
            70% { box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
            100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
        }
        h1 {
            font-size: 2.25rem;
            font-weight: 800;
            letter-spacing: -0.025em;
            margin-bottom: 0.75rem;
            background: linear-gradient(135deg, #ffffff 0%, #94a3b8 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .subtitle {
            color: var(--text-muted);
            font-size: 1.05rem;
            max-width: 720px;
            margin: 0 auto;
        }
        .section-title {
            font-size: 1.35rem;
            font-weight: 700;
            margin-bottom: 1.25rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
            color: #f1f5f9;
        }
        .card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 1rem;
            padding: 1.75rem;
            margin-bottom: 2rem;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        }
        .grid-feeds {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
            gap: 1.25rem;
            margin-bottom: 1.5rem;
        }
        .feed-box {
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--card-border);
            border-radius: 0.75rem;
            padding: 1.25rem;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
            transition: border-color 0.2s ease;
        }
        .feed-box:hover {
            border-color: #475569;
        }
        .feed-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 0.5rem;
            gap: 0.5rem;
        }
        .feed-header h3 {
            font-size: 1.15rem;
            font-weight: 700;
            color: #f8fafc;
        }
        .feed-box p {
            color: var(--text-muted);
            font-size: 0.875rem;
            margin-bottom: 1.25rem;
            min-height: 2.6em;
        }
        .url-box-container {
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 0.5rem;
            padding: 0.5rem 0.75rem;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 0.5rem;
        }
        .url-display {
            font-size: 0.8rem;
            color: #94a3b8;
            word-break: break-all;
            font-family: monospace;
            flex: 1;
        }
        .btn-copy {
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
        }
        .btn-copy:hover {
            background: var(--accent-hover);
        }
        
        /* Filter Bar */
        .filter-section {
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--card-border);
            border-radius: 0.75rem;
            padding: 1rem 1.25rem;
            margin-bottom: 1.25rem;
            display: flex;
            flex-wrap: wrap;
            align-items: center;
            gap: 1rem;
        }
        .filter-label {
            font-weight: 700;
            font-size: 0.95rem;
            color: #38bdf8;
        }
        .filter-btn-clear {
            background: var(--accent);
            color: white;
            padding: 0.35rem 0.9rem;
            border-radius: 9999px;
            font-size: 0.8rem;
            font-weight: 600;
            border: none;
            cursor: pointer;
            transition: background 0.2s ease;
        }
        .filter-btn-clear:hover {
            background: var(--accent-hover);
        }
        .checkbox-group {
            display: flex;
            flex-wrap: wrap;
            gap: 1.25rem;
            align-items: center;
        }
        .checkbox-item {
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            font-size: 0.9rem;
            font-weight: 500;
            cursor: pointer;
            user-select: none;
        }
        .checkbox-item input[type="checkbox"] {
            width: 16px;
            height: 16px;
            accent-color: var(--accent);
            cursor: pointer;
        }
        .label-registration { color: var(--color-registration); }
        .label-administrative { color: var(--color-administrative); }
        .label-sfl { color: var(--color-sfl); }
        .label-instruction { color: var(--color-instruction); }
        .label-admission { color: var(--color-admission); }

        .instructions {
            margin-top: 1rem;
        }
        .step-list {
            list-style-position: inside;
            color: var(--text-muted);
            font-size: 0.9rem;
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }
        .events-preview-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
            flex-wrap: wrap;
            gap: 0.5rem;
        }
        .event-list {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
            max-height: 520px;
            overflow-y: auto;
            padding-right: 0.5rem;
        }
        .event-item {
            background: rgba(15, 23, 42, 0.5);
            border: 1px solid var(--card-border);
            border-radius: 0.5rem;
            padding: 0.85rem 1rem;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 1rem;
        }
        .event-item:hover {
            border-color: #475569;
        }
        .event-info {
            flex: 1;
        }
        .event-title {
            font-weight: 600;
            font-size: 0.95rem;
            color: #f1f5f9;
            margin-bottom: 0.25rem;
        }
        .event-date {
            font-size: 0.8rem;
            color: #94a3b8;
            display: flex;
            align-items: center;
            gap: 0.4rem;
        }
        .category-tag {
            font-size: 0.7rem;
            font-weight: 700;
            padding: 0.2rem 0.5rem;
            border-radius: 0.25rem;
            white-space: nowrap;
        }
        .tag-registration { background: rgba(139, 92, 246, 0.2); color: #c4b5fd; border: 1px solid rgba(139, 92, 246, 0.4); }
        .tag-instruction { background: rgba(16, 185, 129, 0.2); color: #6ee7b7; border: 1px solid rgba(16, 185, 129, 0.4); }
        .tag-administrative { background: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.4); }
        .tag-sfl { background: rgba(14, 165, 233, 0.2); color: #7dd3fc; border: 1px solid rgba(14, 165, 233, 0.4); }
        .tag-admission { background: rgba(245, 158, 11, 0.2); color: #fcd34d; border: 1px solid rgba(245, 158, 11, 0.4); }
        .tag-other { background: rgba(148, 163, 184, 0.2); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.4); }
        
        .badge-count {
            font-size: 0.75rem;
            font-weight: 600;
            padding: 0.15rem 0.5rem;
            border-radius: 9999px;
            background: rgba(255, 255, 255, 0.1);
            color: #cbd5e1;
        }
        
        footer {
            text-align: center;
            padding: 2rem 0;
            color: var(--text-muted);
            font-size: 0.85rem;
            margin-top: auto;
        }
        footer a {
            color: #38bdf8;
            text-decoration: none;
        }
        footer a:hover {
            text-decoration: underline;
        }
        .toast {
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
        }
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
            <span style="font-size: 0.85rem; color: var(--text-muted);">Last Synchronized: $nowStr</span>
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
    const feeds = $feedsJson;
    const eventsEn = $upcomingJsonEn;
    
    function getFullIcsUrl(filename) {
        return window.location.href.split('#')[0].split('?')[0].replace(/index\.html$/, '') + filename;
    }

    function copyIcsUrl(filename) {
        const url = getFullIcsUrl(filename);
        navigator.clipboard.writeText(url).then(() => {
            showToast('ICS link copied to clipboard');
        }).catch(() => {
            prompt('ICS Link:', url);
        });
    }

    function showToast(msg) {
        const toast = document.getElementById('toast');
        toast.innerText = msg;
        toast.style.display = 'block';
        setTimeout(() => { toast.style.display = 'none'; }, 2500);
    }

    function renderFeeds() {
        const container = document.getElementById('feeds-container');
        container.innerHTML = feeds.map(f => `
            <div class="feed-box">
                <div>
                    <div class="feed-header">
                        <h3>` + f.title + `</h3>
                        <span class="badge-count">` + f.count + ` events</span>
                    </div>
                    <p>` + f.description + `</p>
                </div>
                <div class="url-box-container">
                    <span class="url-display" id="url-` + f.filename + `">` + getFullIcsUrl(f.filename) + `</span>
                    <button class="btn-copy" onclick="copyIcsUrl('` + f.filename + `')">
                        <i class="fa-solid fa-copy"></i> Copy
                    </button>
                </div>
            </div>
        `).join('');
    }

    function getSelectedCategories() {
        const checkboxes = document.querySelectorAll('.checkbox-group input[type="checkbox"]:checked');
        return Array.from(checkboxes).map(cb => cb.value.toLowerCase());
    }

    function toggleAllFilters() {
        const checkboxes = document.querySelectorAll('.checkbox-group input[type="checkbox"]');
        const anyChecked = Array.from(checkboxes).some(cb => cb.checked);
        checkboxes.forEach(cb => cb.checked = !anyChecked);
        document.getElementById('btn-toggle-all').innerText = anyChecked ? 'Select All' : 'Clear All';
        filterEvents();
    }

    function filterEvents() {
        const selected = getSelectedCategories();
        const filtered = eventsEn.filter(ev => {
            const cat = (ev.kategoriadi || '').toLowerCase();
            return selected.some(s => cat.includes(s));
        });

        const container = document.getElementById('upcoming-list');
        if (filtered.length === 0) {
            container.innerHTML = '<p style="color: var(--text-muted); padding: 1.5rem; text-align: center;">No matching events found for the selected categories.</p>';
            return;
        }

        container.innerHTML = filtered.map(ev => {
            const cat = ev.kategoriadi || 'General';
            let tagClass = 'tag-other';
            if (cat.includes('Registration')) tagClass = 'tag-registration';
            else if (cat.includes('Instruction')) tagClass = 'tag-instruction';
            else if (cat.includes('Administrative')) tagClass = 'tag-administrative';
            else if (cat.includes('SFL') || cat.includes('YADYOK')) tagClass = 'tag-sfl';
            else if (cat.includes('Admission')) tagClass = 'tag-admission';

            const dateStr = ev.tarih_bitis && ev.tarih_bitis !== ev.tarih ? (ev.tarih + ' - ' + ev.tarih_bitis) : (ev.tarih || ev.start_date.split(' ')[0]);

            return `
                <div class="event-item">
                    <div class="event-info">
                        <div class="event-title">` + ev.adi + `</div>
                        <div class="event-date">
                            <i class="fa-regular fa-calendar"></i> ` + dateStr + `
                        </div>
                    </div>
                    <span class="category-tag ` + tagClass + `">` + cat + `</span>
                </div>
            `;
        }).join('');
    }

    window.addEventListener('DOMContentLoaded', () => {
        renderFeeds();
        filterEvents();
    });
</script>

</body>
</html>
"@

[System.IO.File]::WriteAllText((Join-Path $OutputDir "index.html"), $htmlContent, [System.Text.Encoding]::UTF8)

Write-Host "Sync completed successfully!"
