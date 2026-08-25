# Boğaziçi Üniversitesi Akademik Takvim Senkronizasyon Scripti (PowerShell)
# Windows ortamında yerel olarak çalıştırmak ve tüm ICS/HTML çıktılarını üretmek için

[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

$OutputDir = Join-Path $PSScriptRoot "dist"
if (!(Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

$CurrentYear = (Get-Date).Year
$StartDate = "$($CurrentYear - 1)-01-01"
$EndDate = "$($CurrentYear + 2)-12-31"

Write-Host "🔄 Boğaziçi Akademik Takvim çekiliyor ($StartDate - $EndDate)..." -ForegroundColor Cyan

function Fetch-Events($Url) {
    try {
        $resp = Invoke-RestMethod -Uri $Url -Method Get -Headers @{ "User-Agent" = "Mozilla/5.0" }
        return $resp
    } catch {
        Write-Host "Hata ($Url): $_" -ForegroundColor Red
        return @()
    }
}

$UrlTr = "https://akademiktakvim.bogazici.edu.tr/tr/json?type=4&date=$StartDate&last_date=$EndDate"
$UrlEn = "https://akademiktakvim.bogazici.edu.tr/en/json?type=4&date=$StartDate&last_date=$EndDate"

$EventsTr = Fetch-Events -Url $UrlTr
Write-Host "✅ $($EventsTr.Count) Türkçe etkinlik alındı." -ForegroundColor Green

$EventsEn = Fetch-Events -Url $UrlEn
Write-Host "✅ $($EventsEn.Count) İngilizce etkinlik alındı." -ForegroundColor Green

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
        if ($category) { 
            if ($Lang -eq "tr") { $descParts += "Kategori: $category" } else { $descParts += "Category: $category" }
        }
        if ($descRaw) { $descParts += $descRaw }
        if ($link) {
            if ($Lang -eq "tr") { $descParts += "Detay: $link" } else { $descParts += "Details: $link" }
        }
        if ($Lang -eq "tr") {
            $descParts += "Otomatik Güncellenen Boğaziçi Akademik Takvimi"
        } else {
            $descParts += "Auto-synced Boğaziçi University Academic Calendar"
        }

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

$IcsTr = ConvertTo-Ics -Events $EventsTr -CalName "Boğaziçi Üniversitesi Akademik Takvim" -CalDesc "Resmi Boğaziçi Üniversitesi Akademik Takvimi" -Lang "tr"
[System.IO.File]::WriteAllText((Join-Path $OutputDir "academic.ics"), $IcsTr, [System.Text.Encoding]::UTF8)

$IcsEn = ConvertTo-Ics -Events $EventsEn -CalName "Boğaziçi University Academic Calendar" -CalDesc "Official Boğaziçi University Academic Calendar" -Lang "en"
[System.IO.File]::WriteAllText((Join-Path $OutputDir "academic-en.ics"), $IcsEn, [System.Text.Encoding]::UTF8)

# Kategori bazlı takvimler
$catFilters = @{
    "kayit" = @("Kayıt", "Başvuru");
    "yadyok" = @("YADYOK");
    "egitim" = @("Eğitim-Öğretim")
}
foreach ($kv in $catFilters.GetEnumerator()) {
    $slug = $kv.Key
    $cats = $kv.Value
    $filtered = $EventsTr | Where-Object {
        $cat = [string]$_.kategoriadi
        $matched = $false
        foreach ($c in $cats) {
            if ($cat.IndexOf($c, [System.StringComparison]::OrdinalIgnoreCase) -ge 0) { $matched = $true; break }
        }
        $matched
    }
    if ($filtered.Count -gt 0) {
        $catIcs = ConvertTo-Ics -Events $filtered -CalName "Boğaziçi Akademik Takvim - $($cats[0])" -CalDesc "Boğaziçi Üniversitesi $($cats -join ', ') Takvimi" -Lang "tr"
        [System.IO.File]::WriteAllText((Join-Path $OutputDir "academic-$slug.ics"), $catIcs, [System.Text.Encoding]::UTF8)
        Write-Host "💾 Kategori takvimi oluşturuldu: academic-$slug.ics ($($filtered.Count) etkinlik)" -ForegroundColor Cyan
    }
}

# JSON files
$EventsTr | ConvertTo-Json -Depth 5 | Out-File -FilePath (Join-Path $OutputDir "events-tr.json") -Encoding utf8
$EventsEn | ConvertTo-Json -Depth 5 | Out-File -FilePath (Join-Path $OutputDir "events-en.json") -Encoding utf8

# Generate HTML
$nowStr = (Get-Date).ToString("dd.MM.yyyy HH:mm") + " (TSİ)"
$sortedTr = $EventsTr | Sort-Object { $_.start_date }
$todayStr = (Get-Date).ToString("yyyy-MM-dd")
$upcomingTr = $sortedTr | Where-Object { $_.end_date -ge $todayStr -or $_.start_date -ge $todayStr } | Select-Object -First 20
if (-not $upcomingTr -or $upcomingTr.Count -eq 0) {
    $upcomingTr = $sortedTr | Select-Object -Last 20
}
$upcomingJsonTr = $upcomingTr | ConvertTo-Json -Depth 5 -Compress

$htmlContent = @"
<!DOCTYPE html>
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
            --badge-kayit: #8b5cf6;
            --badge-egitim: #10b981;
            --badge-idari: #ef4444;
            --badge-yadyok: #0ea5e9;
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
            max-width: 1000px;
            margin: 0 auto;
            padding: 2rem 1.5rem;
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
            font-size: 1.1rem;
            max-width: 650px;
            margin: 0 auto;
        }
        .card {
            background: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 1rem;
            padding: 1.75rem;
            margin-bottom: 2rem;
            box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
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
        }
        .feed-box h3 {
            font-size: 1.2rem;
            font-weight: 700;
            margin-bottom: 0.35rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        .feed-box p {
            color: var(--text-muted);
            font-size: 0.875rem;
            margin-bottom: 1rem;
        }
        .btn-group {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }
        .btn {
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
        }
        .btn-google {
            background: #ea4335;
            color: white;
        }
        .btn-google:hover {
            background: #d33426;
        }
        .btn-apple {
            background: #334155;
            color: white;
        }
        .btn-apple:hover {
            background: #475569;
        }
        .btn-copy {
            background: rgba(255, 255, 255, 0.08);
            color: #cbd5e1;
            border: 1px solid rgba(255, 255, 255, 0.15);
        }
        .btn-copy:hover {
            background: rgba(255, 255, 255, 0.15);
            color: white;
        }
        .url-display {
            background: #0f172a;
            border: 1px solid #334155;
            padding: 0.5rem 0.75rem;
            border-radius: 0.375rem;
            font-size: 0.75rem;
            color: #94a3b8;
            word-break: break-all;
            margin-top: 0.5rem;
            font-family: monospace;
        }
        .instructions {
            margin-top: 1rem;
        }
        .instructions h4 {
            font-size: 1rem;
            margin-bottom: 0.75rem;
            color: #e2e8f0;
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
            max-height: 450px;
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
        .tag-kayit { background: rgba(139, 92, 246, 0.2); color: #c4b5fd; border: 1px solid rgba(139, 92, 246, 0.4); }
        .tag-egitim { background: rgba(16, 185, 129, 0.2); color: #6ee7b7; border: 1px solid rgba(16, 185, 129, 0.4); }
        .tag-idari { background: rgba(239, 68, 68, 0.2); color: #fca5a5; border: 1px solid rgba(239, 68, 68, 0.4); }
        .tag-yadyok { background: rgba(14, 165, 233, 0.2); color: #7dd3fc; border: 1px solid rgba(14, 165, 233, 0.4); }
        .tag-other { background: rgba(148, 163, 184, 0.2); color: #cbd5e1; border: 1px solid rgba(148, 163, 184, 0.4); }
        
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
            <span style="font-size: 0.85rem; color: var(--text-muted);">Son Senkronizasyon: $nowStr</span>
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
    const eventsTr = $upcomingJsonTr;
    
    function getFullIcsUrl(filename) {
        return window.location.href.split('#')[0].split('?')[0].replace(/index\.html$/, '') + filename;
    }

    function getWebcalUrl(filename) {
        const icsUrl = getFullIcsUrl(filename);
        return icsUrl.replace(/^https?:\/\//i, 'webcal://');
    }

    function updateUrlDisplays() {
        ['academic.ics', 'academic-en.ics'].forEach(fn => {
            const el = document.getElementById('url-' + fn);
            if (el) {
                el.innerText = getFullIcsUrl(fn);
            }
        });
    }

    function subscribeGoogle(filename) {
        const fullUrl = encodeURIComponent(getFullIcsUrl(filename));
        window.open('https://calendar.google.com/calendar/render?cid=' + fullUrl, '_blank');
    }

    function subscribeApple(filename) {
        window.location.href = getWebcalUrl(filename);
    }

    function copyIcsUrl(filename) {
        const url = getFullIcsUrl(filename);
        navigator.clipboard.writeText(url).then(() => {
            showToast('ICS bağlantısı kopyalandı!');
        }).catch(() => {
            prompt('ICS Bağlantısı:', url);
        });
    }

    function showToast(msg) {
        const toast = document.getElementById('toast');
        toast.innerText = msg;
        toast.style.display = 'block';
        setTimeout(() => { toast.style.display = 'none'; }, 2500);
    }

    function renderEvents() {
        const container = document.getElementById('upcoming-list');
        if (!eventsTr || eventsTr.length === 0) {
            container.innerHTML = '<p style="color: var(--text-muted); padding: 1rem;">Gelecek etkinlik bulunamadı.</p>';
            return;
        }

        container.innerHTML = eventsTr.map(ev => {
            const cat = ev.kategoriadi || 'Genel';
            let tagClass = 'tag-other';
            if (cat.includes('Kayıt') || cat.includes('Registration')) tagClass = 'tag-kayit';
            else if (cat.includes('Eğitim') || cat.includes('Instruction')) tagClass = 'tag-egitim';
            else if (cat.includes('İdari') || cat.includes('Administrative')) tagClass = 'tag-idari';
            else if (cat.includes('YADYOK') || cat.includes('SFL')) tagClass = 'tag-yadyok';

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
        updateUrlDisplays();
        renderEvents();
    });
</script>

</body>
</html>
"@

[System.IO.File]::WriteAllText((Join-Path $OutputDir "index.html"), $htmlContent, [System.Text.Encoding]::UTF8)

Write-Host "🎉 Senkronizasyon ve web arayüzü başarıyla tamamlandı!" -ForegroundColor Green
