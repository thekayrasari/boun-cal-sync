# Boğaziçi Üniversitesi Akademik Takvim Otomatik Senkronizasyonu (iCal / .ics)

Bu proje, [Boğaziçi Üniversitesi Akademik Takvimi](https://akademiktakvim.bogazici.edu.tr/)'ndeki etkinlikleri, sınavları, ders kayıtlarını ve idari tarihleri otomatik olarak çekip **RFC 5545** standartlarında `.ics` (iCalendar / Webcal) takvim akışına dönüştürür.

Bu akışı **Google Calendar**, **Apple Calendar (iOS / macOS)** veya **Outlook** takviminize bir kez ekledikten sonra, üniversitedeki tüm takvim güncellemeleri cihazlarınıza **otomatik olarak senkronize edilir**.

---

## ✨ Özellikler

- 🔄 **%100 Otomatik & Sıfır Bakım:** GitHub Actions ile günde iki kez (07:00 ve 19:00 TSİ) çalışır, takvimi günceller ve GitHub Pages'e yükler.
- 🌐 **Çift Dil Desteği:** Türkçe (`academic.ics`) ve İngilizce (`academic-en.ics`) takvim seçenekleri.
- 🎯 **Kategori Bazlı Filtrelenmiş Akışlar:**
  - `academic.ics` — Tüm etkinlikler (Genel)
  - `academic-kayit.ics` — Ders kayıt ve başvuru dönemleri
  - `academic-egitim.ics` — Eğitim-öğretim ve sınav takvimi
  - `academic-yadyok.ics` — YADYOK / Hazırlık takvimi
- 📱 **Tek Tıkla Abonelik Arayüzü:** Modern web arayüzü sayesinde tek tıkla doğrudan Google Calendar veya Apple Takvim'e ekleme.

---

## 🚀 Kurulum (GitHub Pages ile 2 Dakikada Yayına Alma)

1. Bu projeyi kendi GitHub hesabınızda bir repository olarak oluşturun ve yükleyin:
   ```bash
   git init
   git add .
   git commit -m "feat: initial boun-cal-sync setup"
   git branch -M main
   git remote add origin https://github.com/<KULLANICI_ADINIZ>/boun-cal-sync.git
   git push -u origin main
   ```

2. GitHub Repository sayfanızda:
   - **Settings** > **Pages** menüsüne gidin.
   - **Build and deployment** > **Source** kısmında **`GitHub Actions`** seçeneğini seçin.

3. Artık takvim web siteniz ve `.ics` linkleriniz hazır:
   - **Web Sitesi:** `https://<KULLANICI_ADINIZ>.github.io/boun-cal-sync/`
   - **Türkçe Takvim:** `https://<KULLANICI_ADINIZ>.github.io/boun-cal-sync/academic.ics`
   - **İngilizce Takvim:** `https://<KULLANICI_ADINIZ>.github.io/boun-cal-sync/academic-en.ics`

---

## 📲 Takvime Ekleme Rehberi

### 🔴 Google Calendar (Web / Android)
1. [Google Calendar](https://calendar.google.com/)'ı açın.
2. Sol menüde **"Diğer takvimler"** yanındaki **`+`** butonuna tıklayın.
3. **"URL'den"** (From URL) seçeneğine tıklayın.
4. Takvim `.ics` URL'nizi yapıştırın ve **"Takvim ekle"** butonuna basın.

*(Veya yayınladığınız web sitesindeki **"Google Calendar'a Ekle"** butonuna tıklamanız yeterlidir).*

### 🍏 Apple Calendar (iPhone, iPad, Mac)
- **iPhone / iPad:** 
  1. Web sitenizdeki **"Apple Takvim'e Ekle"** butonuna dokunun (veya Safari'ye `webcal://.../academic.ics` linkini yapıştırın).
  2. Açılan pencerede **"Abone Ol"** butonuna dokunun.
  3. Güncelleme sıklığını belirleyin (Örn: *Her saat* veya *Her gün*).
- **Mac:**
  1. Takvim (Calendar) uygulamasını açın.
  2. Üst menüden **Dosya** > **Yeni Takvim Aboneliği...** seçeneğine tıklayın.
  3. `.ics` URL'sini yapıştırıp **Abone Ol** deyin.

### 🔷 Microsoft Outlook
1. [Outlook Web](https://outlook.live.com/calendar/) veya masaüstü uygulamasını açın.
2. **Takvim Ekle** > **Web'den Abone Ol** yolunu izleyin.
3. `.ics` URL'sini yapıştırın.

---

## 💻 Yerel Geliştirme ve Test

İstediğiniz zaman yerel ortamınızda da senkronizasyonu çalıştırabilirsiniz:

- **Python ile:**
  ```bash
  python src/sync.py
  ```
- **PowerShell ile (Windows):**
  ```powershell
  .\sync.ps1
  ```

Tüm çıktılar `dist/` klasörü altına oluşturulacaktır.

---

## ⚖️ Lisans

MIT License. Veriler [Boğaziçi Üniversitesi Resmi Akademik Takvim Portalı](https://akademiktakvim.bogazici.edu.tr/)'ndan sağlanmaktadır.
