# Boğaziçi University Academic Calendar Synchronization (iCal / .ics)

This project automatically fetches academic dates, exams, course registrations, and administrative deadlines from the official [Boğaziçi University Academic Calendar](https://akademiktakvim.bogazici.edu.tr/) portal and generates standard **RFC 5545** compliant `.ics` (iCalendar / Webcal) calendar feeds.

Once subscribed in **Google Calendar**, **Apple Calendar (iOS / macOS)**, or **Microsoft Outlook**, any schedule updates or changes made by the university will automatically sync to your devices.

---

## Available Feeds

### Complete Calendars
- **English Complete:** `academic-en.ics`
- **Turkish Complete:** `academic.ics`

### Official Category Feeds (English)
- **Registration (`academic-registration.ics`):** Course registration windows, advisor approvals, add/drop periods, and fee payment deadlines.
- **Administrative (`academic-administrative.ics`):** University administrative meetings (ÜYK/FKK), official deadlines, and department submissions.
- **Instruction & Exams (`academic-instruction.ics`):** First and last days of classes, exam periods, grade submissions, and semester dates.
- **School of Foreign Languages (`academic-sfl.ics`):** BUEPT English proficiency exams, placement tests, and preparatory school terms.
- **Admission & Applications (`academic-admission.ics`):** Undergraduate/graduate applications, double major/minor transfers, and exchange programs.

### Official Category Feeds (Turkish)
- **Kayıt:** `academic-kayit.ics`
- **İdari:** `academic-idari.ics`
- **Eğitim-Öğretim:** `academic-egitim.ics`
- **YADYOK:** `academic-yadyok.ics`
- **Başvuru:** `academic-basvuru.ics`

---

## Setup and Deployment (GitHub Pages)

### 1. Push to Your GitHub Repository
```bash
git init
git add .
git commit -m "feat: add 5 official category feeds and interactive filter UI"
git branch -M main
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/boun-cal-sync.git
git push -u origin main
```

### 2. Enable GitHub Pages
1. Go to your repository settings: **Settings** > **Pages**.
2. Under **Build and deployment** > **Source**, select **GitHub Actions**.

### 3. Access Your Feeds
Once the workflow runs, your calendar web page and `.ics` feeds will be live at:
- **Landing Page:** `https://YOUR_GITHUB_USERNAME.github.io/boun-cal-sync/`
- **English Feed:** `https://YOUR_GITHUB_USERNAME.github.io/boun-cal-sync/academic-en.ics`
- **Registration:** `https://YOUR_GITHUB_USERNAME.github.io/boun-cal-sync/academic-registration.ics`
- **Administrative:** `https://YOUR_GITHUB_USERNAME.github.io/boun-cal-sync/academic-administrative.ics`
- **Instruction & Exams:** `https://YOUR_GITHUB_USERNAME.github.io/boun-cal-sync/academic-instruction.ics`
- **SFL / YADYOK:** `https://YOUR_GITHUB_USERNAME.github.io/boun-cal-sync/academic-sfl.ics`
- **Admission:** `https://YOUR_GITHUB_USERNAME.github.io/boun-cal-sync/academic-admission.ics`

---

## How to Subscribe

### Google Calendar (Web / Android)
1. Open [Google Calendar](https://calendar.google.com/).
2. On the left sidebar, click the **+** icon next to **Other calendars**.
3. Select **From URL**.
4. Paste your `.ics` feed URL and click **Add calendar**.

*(Alternatively, click the **Add to Google Calendar** button directly on your hosted landing page).*

### Apple Calendar (iPhone, iPad, Mac)
- **iPhone / iPad:**
  1. Open Safari and tap the **Add to Apple Calendar** button on your landing page (or enter the `webcal://` link).
  2. Tap **Subscribe** in the confirmation prompt.
  3. Set your preferred auto-refresh frequency (e.g., *Hourly* or *Daily*).
- **Mac:**
  1. Open the **Calendar** application.
  2. Go to **File** > **New Calendar Subscription...**.
  3. Paste the `.ics` feed URL and click **Subscribe**.

### Microsoft Outlook
1. Open [Outlook Calendar](https://outlook.live.com/calendar/) or the Outlook desktop app.
2. Select **Add Calendar** > **Subscribe from web**.
3. Paste the `.ics` feed URL and click **Import**.

---

## Local Development and Testing

You can run the synchronization manually in your local environment:

- **Using Python:**
  ```bash
  python src/sync.py
  ```
- **Using PowerShell (Windows):**
  ```powershell
  .\sync.ps1
  ```

All output files will be generated under the `dist/` directory.

---

## License

MIT License. Calendar data is sourced from the official [Boğaziçi University Academic Calendar](https://akademiktakvim.bogazici.edu.tr/) portal.
