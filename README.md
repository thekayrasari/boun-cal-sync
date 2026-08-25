# Boğaziçi University Academic Calendar Synchronization (iCal / .ics)

This project automatically fetches academic dates, exams, course registrations, and administrative deadlines from the official [Boğaziçi University Academic Calendar](https://akademiktakvim.bogazici.edu.tr/) portal and generates standard **RFC 5545** compliant `.ics` (iCalendar / Webcal) calendar feeds.

Once subscribed in **Google Calendar**, **Apple Calendar (iOS / macOS)**, or **Microsoft Outlook**, any schedule updates or changes made by the university will automatically sync to your devices.

---

## Features

- **Automated & Zero Maintenance:** Runs twice daily via GitHub Actions (at 04:00 and 16:00 UTC), fetches updates, and deploys directly to GitHub Pages.
- **Bilingual Feeds:** Available in both Turkish (`academic.ics`) and English (`academic-en.ics`).
- **Category-Specific Calendars:**
  - `academic.ics` — Complete calendar (all events)
  - `academic-en.ics` — Complete calendar in English
  - `academic-kayit.ics` — Course registration and application periods
  - `academic-egitim.ics` — Instruction terms and exam dates
  - `academic-yadyok.ics` — School of Foreign Languages (YADYOK / SFL)
- **One-Click Subscription Web UI:** Simple web interface with direct buttons for Google Calendar and Apple Calendar.

---

## Setup and Deployment (GitHub Pages)

### 1. Push to Your GitHub Repository
```bash
git init
git add .
git commit -m "feat: initial boun-cal-sync setup"
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
- **Turkish Feed:** `https://YOUR_GITHUB_USERNAME.github.io/boun-cal-sync/academic.ics`
- **English Feed:** `https://YOUR_GITHUB_USERNAME.github.io/boun-cal-sync/academic-en.ics`

---

## How to Subscribe

### Google Calendar (Web / Android)
1. Open [Google Calendar](https://calendar.google.com/).
2. On the left sidebar, click the **+** icon next to **Other calendars**.
3. Select **From URL**.
4. Paste your `.ics` feed URL and click **Add calendar**.

*(Alternatively, click the **Add to Google Calendar** button on your hosted landing page).*

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
