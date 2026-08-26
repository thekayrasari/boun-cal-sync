# Boğaziçi University Academic Calendar Synchronization (iCal / .ics)

Automated synchronization and generation of dedicated, category-specific **RFC 5545** compliant `.ics` calendar feeds and JSON exports from the official [Boğaziçi University Academic Calendar](https://akademiktakvim.bogazici.edu.tr/) portal.

Once subscribed in **Google Calendar**, **Apple Calendar (iOS / macOS)**, or **Microsoft Outlook**, any academic schedule updates published by the university will automatically sync to your devices.

---

## Official Category Feeds

Feeds are strictly mapped 1-to-1 to official university category IDs with zero overlaps or duplicates:

### English Feeds
| Category | File | Description |
| :--- | :--- | :--- |
| **Registration** | `registration.ics` | Course registration windows, advisor approvals, add/drop periods, and fee deadlines. |
| **Administrative** | `administrative.ics` | University board meetings (ÜYK/FKK), official deadlines, and departmental submissions. |
| **Instruction & Exams** | `instruction.ics` | First/last days of classes, midterm & final exams, grade submissions, and semester dates. |
| **School of Foreign Languages** | `sfl.ics` | BUEPT English proficiency exams, placement tests, and preparatory school terms. |
| **Admission & Applications** | `admission.ics` | Undergraduate/graduate applications, double major/minor transfers, and exchange programs. |

### Turkish Feeds (Türkçe Takvimler)
| Kategori | Dosya | Açıklama |
| :--- | :--- | :--- |
| **Kayıt** | `kayit.ics` | Ders kayıtları, danışman onayları, ekle/bırak günleri ve katkı payı ödeme tarihleri. |
| **İdari** | `idari.ics` | ÜYK/FYK toplantıları, resmi son tarihler ve idari takvim. |
| **Eğitim-Öğretim** | `egitim.ics` | Derslerin başlangıç/bitiş günleri, ara sınavlar, final dönemleri ve not girişleri. |
| **YADYOK** | `yadyok.ics` | BUEPT İngilizce yeterlilik sınavları, düzey belirleme testleri ve hazırlık takvimi. |
| **Başvuru** | `basvuru.ics` | Lisans/lisansüstü başvurular, çift anadal/yandal yatay geçişler ve değişim programları. |

---

## Setup & Deployment (GitHub Pages)

### 1. Push to GitHub
```bash
git add .
git commit -m "feat: automated academic calendar sync"
git push origin main
```

### 2. Enable GitHub Pages
1. In your GitHub repository, navigate to **Settings** > **Pages**.
2. Under **Build and deployment** > **Source**, select **GitHub Actions**.

### 3. Access Feeds
The automated GitHub Actions workflow will build and publish your landing page and feeds to:
- **Interactive Landing Page:** `https://<USERNAME>.github.io/<REPO>/`
- **Category Feeds:** `https://<USERNAME>.github.io/<REPO>/<category>.ics`
- **JSON Data:** `https://<USERNAME>.github.io/<REPO>/events-en.json` (and `events-tr.json`)

---

## How to Subscribe

### 1-Click Subscription (`webcal://`)
On iOS, macOS, or modern calendar clients, click the **Subscribe** button directly on the web landing page, or replace `https://` with `webcal://` in your calendar app.

### Google Calendar (Web / Android)
1. Open [Google Calendar](https://calendar.google.com/).
2. In the left sidebar, click the **+** button next to **Other calendars** > **From URL**.
3. Paste the `.ics` link (e.g. `https://<USERNAME>.github.io/<REPO>/registration.ics`) and click **Add calendar**.

### Apple Calendar (iPhone, iPad, Mac)
- **iPhone / iPad:** Settings > Calendar > Accounts > Add Account > Other > Add Subscribed Calendar > paste the `.ics` link.
- **Mac:** Calendar app > **File** > **New Calendar Subscription...** > paste the link.

### Microsoft Outlook
1. Open [Outlook Calendar](https://outlook.live.com/calendar/).
2. Select **Add Calendar** > **Subscribe from web**.
3. Paste the `.ics` link and click **Import**.

---

## Local Development

The synchronization script has **zero external dependencies** and runs on standard Python 3.8+:

```bash
python src/sync.py
```

All output assets are generated in the `dist/` directory:
- 10 RFC 5545 compliant `.ics` calendar files
- `events-en.json` and `events-tr.json`
- `index.html` (Interactive landing page with category filtering and search)

---

## License

MIT License. Calendar data is sourced from the official [Boğaziçi University Academic Calendar](https://akademiktakvim.bogazici.edu.tr/) portal.

