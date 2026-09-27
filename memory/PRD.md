# PRD — Sistem Pemesanan Rumah & CRM Rumah KORPRI

## Original Problem Statement
Platform pemesanan rumah + CRM KPR yang menghubungkan 4 stakeholder: Peminat/ASN, Admin KORPRI, Mitra Developer, dan Bank BTN. Workflow: isi data & pilih unit dengan simulasi KPR → bayar booking fee (QRIS/VA) → SPR PDF otomatis → developer approve + TTD digital → forward ke BTN → CRM checklist dokumen + follow-up WhatsApp → keputusan kelayakan KPR.

## User Choices
- Payment gateway: SIMULATED (QRIS / VA BTN via webhook)
- WhatsApp: SIMULATED (log pesan tersimpan di dashboard)
- Deliverable: full-stack app + dokumen arsitektur
- Auth: JWT + akun demo seeded
- Bahasa: Indonesia

## Architecture
- Backend: FastAPI (modular: server.py, auth.py, kpr.py, spr.py, seed.py, db.py), MongoDB (motor), reportlab untuk PDF SPR, JWT (Bearer) + bcrypt.
- Frontend: React 19 + react-router v7, Tailwind + shadcn/ui, framer-motion. Tema Organic & Earthy (forest green #0F5132).
- Collections: users, projects, units, bookings, kpr_applications, documents, notifications, wa_logs.

## User Personas / Roles
- consumer (Peminat ASN), admin_korpri (CRM), admin_developer (Mitra), btn_evaluator (Analis BTN)

## Implemented (2026-06-25)
- Landing page + katalog proyek/unit + kalkulator KPR interaktif (FLPP/Komersial, Fix & Floating, tenor 5–30 thn)
- Booking unit + pembayaran simulasi QRIS/VA + webhook verifikasi
- Auto-generate SPR PDF; developer approve dengan tanda tangan digital (canvas)
- Auto-forward KPR application ke Bank BTN + seed checklist 6 dokumen
- Consumer portal: bayar, unduh SPR, unggah dokumen
- CRM KORPRI: stats, checklist dokumen, verifikasi, follow-up WhatsApp otomatis
- BTN dashboard: keputusan kelayakan (pre_approved/approved/rejected/need_revision) + catatan SLIK
- Notifikasi in-app + log WhatsApp; halaman dokumentasi arsitektur (/arsitektur)
- JWT auth 4 peran + akun demo seeded. All tests 100% (23/23 backend).
- (Iterasi 2) Developer: tambah proyek & unit (harga, foto tampak depan, layout, siteplan, alamat detail, validasi ukuran gambar & duplikasi blok/no). Peminat: dialog detail unit (foto/layout/siteplan/alamat + simulasi KPR per unit) → pesan → dialog pembayaran menampilkan estimasi DP + booking fee.
- (Iterasi 3) Tahap pembayaran DP penuh (uang muka) setelah SPR terbit; Object Storage Emergent untuk foto unit/proyek (served via /api/files/{path}, helper mediaUrl di FE); Developer edit & hapus unit (Kelola Unit) dengan validasi kepemilikan booking pada DP dan cek duplikat blok/no saat edit. Semua test 100% (iteration_3).
- (Iterasi 4) Validasi magic-bytes foto (hanya JPG/PNG/WebP asli, else 400); Termin cicilan DP (3 termin berurutan, sisa tagihan & status partial/paid di portal peminat, endpoint pay-dp?termin_no & webhook kind=dp_termin); Developer edit proyek (PUT /api/developer/projects/{id}: nama, lokasi, alamat, banner, program — nama proyek ikut ter-update di unit).

- (Import 2026-06 ke Emergent) Repo `pardz2006/rumahkorpri` di-clone & di-import. Skema bunga KPR Komersial diubah jadi Promo KORPRI: 2,65% fixed 3 tahun, lalu naik bertahap (5% thn 4-5, 7,5% thn 6-8) hingga cap floating 9,99% (kpr.py `rate_tiers`, re-amortisasi per tahap). FLPP tetap flat 5%.

- (Iterasi 5) Tabel Amortisasi bulan-per-bulan (pokok/bunga/sisa pokok, endpoint /api/kpr/amortization, tabel scroll di simulator + ringkasan total bunga/bayar); Unduh Simulasi KPR PDF (/api/kpr/simulate/pdf via reportlab: ringkasan + skema tahapan + amortisasi tahunan); WhatsApp Twilio (backend/whatsapp.py: kirim asli via Twilio jika TWILIO_ACCOUNT_SID/AUTH_TOKEN/WHATSAPP_FROM terisi, fallback simulasi jika kosong; wa_log menyimpan channel/status/provider_sid; badge status Twilio di CRM). Pengurutan proyek di landing menurut kota lalu provinsi domisili user login (users.city/province, form registrasi diperbarui, match_score di /api/projects, badge "Dekat domisili Anda"). NOTE: akun Twilio user masih Trial → pengiriman WhatsApp hanya jalan ke nomor terverifikasi & yang sudah join sandbox.

- (Iterasi 6) Riwayat Simulasi: peminat bisa simpan simulasi KPR (POST/GET/DELETE /api/simulations, tombol "Simpan ke Riwayat" di simulator), buka kembali & bandingkan hingga 3 simulasi berdampingan di portal (tab Riwayat Simulasi + panel perbandingan). Profil Domisili editable (PATCH /api/profile: kota/provinsi/no. WA) langsung mengurutkan ulang proyek di landing sesuai domisili. Tombol "Tes Kirim WhatsApp" di CRM (POST /api/whatsapp/test, admin_korpri) untuk validasi Twilio setelah join sandbox. Semua test 100% (10/10 backend, frontend OK). CATATAN: akun Twilio user masih Trial → kirim asli hanya berhasil ke nomor terverifikasi/yang sudah join sandbox.

- (Iterasi 6b) Unduh PDF langsung dari tiap item Riwayat Simulasi (pakai ulang /api/kpr/simulate/pdf); Simulasi tersimpan otomatis saat peminat memesan unit (label "… (pesanan)" di create_booking).

- (Iterasi 7) User demo tambahan: 2 analis bank (Bank BTN, Bank DKI — role btn_evaluator, field `bank`) & 3 developer berbeda (developer/developer2/developer3, field `company`). Bagikan Simulasi: tautan publik per simulasi (POST /api/simulations/{id}/share → token; GET /api/public/simulations/{token} tanpa auth; halaman publik /s/{token} + tombol bagikan WhatsApp & unduh PDF di Riwayat). Pengingat DP jatuh tempo: endpoint cron POST /api/cron/dp-reminders (dipanggil scheduler harian via .emergent/crons.yml) mengirim WhatsApp untuk termin DP yang jatuh tempo ≤3 hari & belum diingatkan (idempoten, tandai reminded). Dashboard bank kini menampilkan nama bank user. Semua test 100% (15/15 backend, frontend OK).

## Environment Import (2026-09-25 — rumah-deps workspace)
- Repo ZIP di-import ke /app; deps diinstall: `yarn install` (frontend, Yarn 1.22.22, resolutions respected) + `pip install -r requirements.txt` (venv /root/.venv, Python 3.11.16, Node 20.20.2). `pip check` bersih.
- Fix saat install: hash fragment `#sha256=` pada URL wheel litellm di requirements.txt dihapus (konflik ResolutionImpossible dengan emergentintegrations).
- Env wired: `JWT_SECRET` + `EMERGENT_LLM_KEY` ditambahkan ke backend/.env (JWT_SECRET wajib — auth.py KeyError tanpa itu); `MONGO_URL`/`DB_NAME`/`CORS_ORIGINS`/`REACT_APP_BACKEND_URL` sudah ada.
- Opsional belum diisi (fallback aman): `TWILIO_ACCOUNT_SID/AUTH_TOKEN/WHATSAPP_FROM` (WhatsApp → mode simulasi), `OWNER_EMAIL/OWNER_PASSWORD` (default admin@rumahkorpri.com/korpri123), `INTEGRATION_PROXY_URL` (default integrations.emergentagent.com).
- Smoke test 100% (test_reports/iteration_8.json): health OK, seed jalan (2 proyek + 7 user), login admin & consumer via UI OK, simulasi KPR publik OK, object storage terinisialisasi.

## Iterasi 8 — Isolasi Data & Katalog Diperluas (2026-09-25)
- **Isolasi Developer**: setiap `admin_developer` hanya melihat/mengelola proyek & unit miliknya. Proyek kini punya `developer_id` (pemilik). Endpoint baru `GET /api/developer/projects` (scoped); `create_project` set `developer_id`; `update_project`/`create_unit`/`update_unit`/`delete_unit`/`approve_spr` cek `_assert_project_owner` (403 bila lintas developer); `/api/developer/spr-queue` & `/api/stats` di-scope per developer. Landing/`/api/projects` publik tetap menampilkan semua proyek ke peminat.
- **Isolasi Bank**: proyek punya field `bank` (Bank BTN / Bank DKI). KPR application menyimpan `bank` dari proyek saat SPR disetujui. `GET /api/kpr/applications` difilter per `user.bank` untuk `btn_evaluator`; `update_kpr_status` 403 bila lintas bank; stats bank di-scope. Admin KORPRI tetap melihat semua.
- **Katalog diperluas**: seed versioned (SEED_VERSION=3, re-seed sekali & wipe demo lama). 6 proyek milik 3 developer berbeda, total 28 unit (tipe 36–70), campuran FLPP/Bank BTN & KOMERSIAL/Bank DKI.
- **Gambar denah**: tiap unit punya `image_front` (foto rumah) + `image_layout` (denah 2D per luas bangunan 36/45/60/70 m², menampilkan ruang tamu, kamar tidur, dapur, kamar mandi, carport) — tampil di dialog detail unit ("Layout Rumah"). Form proyek developer kini punya pilihan Bank Pembiayaan (pf-bank).
- Verifikasi: 15/15 pytest isolasi PASS (iteration_9.json), frontend isolasi + render denah OK. Catatan: 403 lintas-bank belum diuji e2e karena 0 pengajuan KPR pasca re-seed (butuh alur booking→bayar→SPR); logika sudah benar per inspeksi kode.

## Iterasi 9 — Filter Katalog + Alur KPR E2E + Admin Baru (2026-09-25)
- Filter katalog di landing (Kota/Tipe/Program/Harga, hitungan real-time, reset, empty-state) — terverifikasi UI.
- Alur booking→bayar→SPR→KPR dijalankan e2e: isolasi bank terbukti dengan data nyata (BTN hanya lihat BTN, DKI hanya lihat DKI, PATCH lintas-bank 403). 7/7 pytest PASS (iteration_10.json).
- Login Admin KORPRI baru: pardz2006@gmail.com / korpri123 (seed upsert idempoten = juga mereset password).

## Iterasi 10 — 5 Login Baru + Katalog 12 Proyek (2026-09-25)
- 2 analis Bank DKI baru (bankdki2@, bankdki3@ / dki123) sebagai alternatif Bank BTN — isolasi per-bank: sesama analis DKI melihat himpunan pengajuan DKI yang sama (rekan satu bank), tidak bisa melihat pengajuan BTN.
- 3 developer baru dengan produk berbeda: developer4@ (PT Cendana Propertindo — Sleman & Bantul, Yogyakarta), developer5@ (PT Harmoni Land Indonesia — Semarang), developer6@ (PT Sinar Purnama Development — Malang & Surabaya) / developer123.
- 6 proyek baru (total 12 proyek, 49 unit) di-seed secara ADITIF via ensure_project() — data booking/KPR nyata dari iterasi 9 TIDAK terhapus. Isolasi per-developer & lintas-developer 403 terverifikasi 15/15 (iteration_11.json).

## Iterasi 11 — 5 Peminat Baru + Koreksi Model Bank + Quick-Login Portal (2026-09-25)
- 5 peminat baru beda kota: consumer2@ (Tangerang, Banten), consumer3@ (Palangka Raya, Kalteng), consumer4@ (Bandar Lampung, Lampung), consumer5@ (Semarang, Jateng), consumer6@ (Medan, Sumut) — semua / consumer123.
- Koreksi bank: model dirampingkan jadi TEPAT 1 Bank BTN (btn@) + 1 Bank DKI (bankdki@) sebagai entitas terpisah dengan data KPR masing-masing. Akun bankdki2@/bankdki3@ DIHAPUS dari seed & DB (login → 401). Isolasi BTN↔DKI terverifikasi ulang.
- Quick-login portal: halaman /login menampilkan SEMUA akun demo (16 akun, dikelompokkan per peran) — klik langsung masuk tanpa mengetik (quickLogin). Panel tampil di desktop (kolom kiri gelap) & mobile (panel terang di atas form). data-testid: demo-<email>.
- Verifikasi: 15/15 pytest + 7/7 flow UI PASS (iteration_12.json); data 12 proyek/49 unit & 2 pengajuan KPR tetap utuh.

## Iterasi 12 — Peta Interaktif + Notifikasi Unit Baru (2026-09-25)
- Peta lokasi proyek (Leaflet + OpenStreetMap, tanpa API key) di landing page: 12 marker proyek. Saat peminat login, header "perumahan terdekat dari {kota}", marker biru domisili, dan marker oranye untuk proyek TERDEKAT (haversine); popup punya tombol "Lihat Unit" → /proyek/{id}. Komponen: components/ProjectsMap.js. Backend: geo.py (CITY_COORDS + coords_for_location), koordinat di-backfill ke semua proyek + field lat/lng di /api/projects.
- Notifikasi Unit Baru: saat developer membuat proyek (POST /api/developer/projects), semua peminat yang berdomisili di kota proyek otomatis mendapat notifikasi in-app (muncul di lonceng Navbar). Terverifikasi city-scoped (positif utk kota cocok, negatif utk kota lain).
- Verifikasi: backend 3/3 + frontend map/notif PASS (iteration_13.json), katalog tetap 12 proyek/49 unit. Catatan: belum ada endpoint DELETE proyek.

## Demo Accounts
- Admin KORPRI: admin@rumahkorpri.com / korpri123
- Admin KORPRI (Pardz): pardz2006@gmail.com / korpri123
- Developer: developer@rumahkorpri.com / developer123
- Bank BTN: btn@rumahkorpri.com / btn123
- Consumer: consumer@rumahkorpri.com / consumer123

## Backlog (P1/P2)
- P1: Auth guard pada endpoint unduh SPR PDF (token query param)
- P1: Siteplan interaktif visual (grid blok) selain daftar unit
- P2: Integrasi WhatsApp gateway riil (Twilio) & payment gateway riil (Midtrans/Xendit)
- P2: Email SPR otomatis (Resend), pemisahan router backend per modul
- P2: Ekspor laporan CRM & analitik funnel konversi


## Import dari GitHub (2026-09-27)
- Repo privat `pardz2006/rumahkorpri` (branch main, dijadikan publik sementara) di-clone & di-sync ke /app via rsync (mempertahankan .env lokal).
- Dependencies: `pip install -r backend/requirements.txt` (OK, +twilio/reportlab/aiohttp-retry/chardet) & `yarn install` frontend (OK, lockfile baru tersimpan).
- Env: `JWT_SECRET` + `EMERGENT_LLM_KEY` ditambahkan ke backend/.env (dibutuhkan auth.py & storage.py); MONGO_URL/DB_NAME/CORS_ORIGINS/REACT_APP_BACKEND_URL tetap.
- Verifikasi: supervisor backend+frontend RUNNING; /api health OK; seed jalan (12 proyek, 49 unit, 16 user demo); login admin OK; object storage terinisialisasi; landing page render sempurna.
- Kredensial demo dicatat di memory/test_credentials.md. Twilio tidak dikonfigurasi → WhatsApp berjalan dalam mode simulasi (by design).

## Iterasi 14 — Field Unit Baru + Zoom Gambar + Duplikat Unit (2026-09-27)
- Field baru pada unit: `image_location_map` (gambar peta lokasi dari jalan raya, via object storage) & `gps_coordinates` (teks "lat, lng"). Ditambahkan di UnitCreateInput/UnitUpdateInput + store_media. Form developer punya input GPS & upload peta lokasi.
- Detail unit peminat (ProjectDetail): semua gambar (tampak depan, layout, siteplan, peta lokasi) kini zoomable via komponen `ZoomableImage` (lightbox full-screen, zoom in/out 100–500%, wheel/drag, reset). GPS ditampilkan sebagai tautan "Buka di Google Maps".
- Duplikat/Clone unit: tombol Copy di kartu Kelola Unit menyalin semua data unit (tipe, harga, luas, gambar, GPS) ke form Tambah Unit dengan Blok/No dikosongkan agar developer cukup mengubah alamat unit lalu simpan.
- Verifikasi: backend create-unit dengan gps_coordinates OK; form baru & zoom lightbox 200% terverifikasi via screenshot.

## Iterasi 15 — Galeri Foto + Duplikat Massal + Rute ke Lokasi (2026-09-27)
- **Galeri Foto**: form unit developer punya `GalleryInput` (upload beberapa foto, hapus per item; disimpan di `unit.gallery` via object storage). Detail unit peminat memakai komponen `UnitGallery` — carousel swipeable (panah prev/next, counter, thumbnail) menggabungkan foto tampak depan + galeri; tiap slide bisa di-zoom.
- **Duplikat Massal**: endpoint `POST /api/developer/units/bulk` (UnitBulkCreateInput: start_number, count 1–50, number_prefix, number_pad) membuat banyak unit berurutan dalam 1 request dengan media di-upload sekali & dibagikan. Cek bentrok nomor. Form developer punya toggle "Duplikat Massal" + input Mulai No./Jumlah + preview rentang (mis. No. 01–05).
- **Rute ke Lokasi**: di detail unit, di samping koordinat GPS ada tombol "Rute ke lokasi" → `google.com/maps/dir/?api=1&destination=<gps>&travelmode=driving` (navigasi dari posisi peminat).
- Verifikasi: bulk API buat 5 unit (No.01–05) OK; galeri carousel, tombol rute, & toggle massal terverifikasi via screenshot.
