# Bogazici University Academic Calendar Synchronization (iCal / .ics)

This project automatically fetches academic dates, exams, course registrations, and administrative deadlines from the official [Boğaziçi University Academic Calendar](https://akademiktakvim.bogazici.edu.tr/) portal and generates dedicated, category-specific **RFC 5545** compliant `.ics` calendar feeds.

Once subscribed in **Google Calendar**, **Apple Calendar (iOS / macOS)**, or **Microsoft Outlook**, any schedule updates or changes made by the university will automatically sync to your devices.

---

## Category Feeds

Each feed is mapped strictly to the official university category IDs with zero overlaps or duplicates:

### English Feeds
- **Registration (`registration.ics`):** Course registration windows, advisor approvals, add/drop periods, and fee payment deadlines.
- **Administrative (`administrative.ics`):** University administrative meetings (ÜYK/FKK), official deadlines, and department submissions.
- **Instruction & Exams (`instruction.ics`):** First and last days of classes, exam periods, grade submissions, and semester dates.
- **School of Foreign Languages (`sfl.ics`):** BUEPT English proficiency exams, placement tests, and preparatory school terms.
- **Admission & Applications (`admission.ics`):** Undergraduate/graduate applications, double major/minor transfers, and exchange programs.

### Turkish Feeds
- **Kayıt:** `kayit.ics`
- **İdari:** `idari.ics`
- **Eğitim-Öğretim:** `egitim.ics`
- **YADYOK:** `yadyok.ics`
- **Başvuru:** `basvuru.ics`

---

## Setup and Deployment (GitHub Pages)

### 1. Push to Your GitHub Repository
```bash
git add .
git commit -m "feat: strict 1-to-1 category feeds and clean ics links"
git push -f origin main
```

### 2. Enable GitHub Pages
1. Go to your repository settings: **Settings** > **Pages**.
2. Under **Build and deployment** > **Source**, select **GitHub Actions**.

### 3. Access Your Feeds
Once the workflow runs, your calendar web page and `.ics` feeds will be live at:
- **Landing Page:** `https://YOUR_GITHUB_USERNAME.github.io/boun-cal-sync/`
- **Registration:** `https://YOUR_GITHUB_USERNAME.github.io/boun-cal-sync/registration.ics`
- **Administrative:** `https://YOUR_GITHUB_USERNAME.github.io/boun-cal-sync/administrative.ics`
- **Instruction & Exams:** `https://YOUR_GITHUB_USERNAME.github.io/boun-cal-sync/instruction.ics`
- **SFL / YADYOK:** `https://YOUR_GITHUB_USERNAME.github.io/boun-cal-sync/sfl.ics`
- **Admission:** `https://YOUR_GITHUB_USERNAME.github.io/boun-cal-sync/admission.ics`

---

## How to Subscribe

Copy the category `.ics` link you need and add it to your calendar client:

### Google Calendar (Web / Android)
1. Open [Google Calendar](https://calendar.google.com/).
2. On the left sidebar, click the **+** icon next to **Other calendars**.
3. Select **From URL**.
4. Paste your category `.ics` feed URL and click **Add calendar**.

### Apple Calendar (iPhone, iPad, Mac)
- **iPhone / iPad:** Go to Settings > Calendar > Accounts > Add Account > Other > Add Subscribed Calendar, paste the `.ics` link, and tap Next.
- **Mac:** Open Calendar, go to **File** > **New Calendar Subscription...**, paste the `.ics` link, and click **Subscribe**.

### Microsoft Outlook
1. Open [Outlook Calendar](https://outlook.live.com/calendar/) or the Outlook desktop app.
2. Select **Add Calendar** > **Subscribe from web**.
3. Paste the category `.ics` feed URL and click **Import**.

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
