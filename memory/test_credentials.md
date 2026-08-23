# Kredensial Uji SIPRO (demo seed)

Sandi SEMUA akun demo: `Sipro#2026`

| Peran | Email | Catatan |
|---|---|---|
| Super Admin | superadmin@sipro.co.id | akses penuh + admin sistem |
| Owner/Direksi | owner@sipro.co.id | dashboard direksi, laporan |
| Manajer Sales | manager@sipro.co.id | approve diskon, pipeline |
| Marketing Admin | marketing@sipro.co.id | leads, kampanye |
| Sales | sales@sipro.co.id | leads/deal miliknya (uji RBAC 403 konstruksi) |
| Sales 2 | sales2@sipro.co.id | uji isolasi antar sales |
| Finance | finance@sipro.co.id | pembayaran, kas, GL |
| Manajer Proyek | pm@sipro.co.id | konstruksi, kalender, kalibrasi |
| Pelaksana Lapangan | site@sipro.co.id | Papan Mandor, progres (tanpa tombol kalibrasi) |
| Manajer Keuangan | finlead@sipro.co.id | approve fee/komisi/kas bon, tutup periode GL |
| Supervisor Digital Marketing | dmlead@sipro.co.id | otomasi, template WA, broadcast, showroom |
| Staf Digital Marketing | dm@sipro.co.id | inbox WA, broadcast (tanpa approve) |

## Pemisahan tugas yang DIUJI (jangan dianggap bug)
- **Fee mitra**: sales/marketing/manajer **MENGAJUKAN** (`marketing_fee:create`), finance
  **MENYETUJUI + MEMBAYAR** (`approve`/`update`). Karena itu tombol **"Ajukan Fee"
  SENGAJA nonaktif untuk finance** dan `POST /api/partners/rules/issue` menjawab **403**
  untuk finance — itu perilaku benar, bukan cacat.
- **Pemeliharaan jam tahap** (`POST /api/aging/reconcile`): hanya owner/super_admin
  (`aging:manage`). Semua peran boleh MELIHAT laporan umur tahap.
- **Mitra**: sales hanya boleh MELIHAT; finance boleh mengubah **aturan fee**
  (`partners:update`) tetapi TIDAK boleh mendaftarkan mitra baru (`partners:create`).

## Memulihkan lingkungan dari repo (WAJIB dibaca agen lanjutan)
Berkas `.env` TIDAK ada di git. Setelah `git clone`, backend akan **gagal login** sampai
variabel ini ada di `backend/.env` (selain `MONGO_URL` dan `DB_NAME` milik container):

```
JWT_SECRET="<acak, mis. python3 -c 'import secrets;print(secrets.token_urlsafe(48))'>"
```

`security.py` membacanya dengan `os.environ["JWT_SECRET"]` (tanpa nilai bawaan), jadi tanpa
baris itu setiap `POST /api/auth/login` mati 500. Variabel lain (WhatsApp, e-sign, storage)
opsional: bila kosong, modulnya jalan dalam **mode simulasi** dan aplikasi tetap utuh.

Dependensi yang biasanya belum ada di image dasar: `APScheduler`, `reportlab`, `tzlocal`
(`pip install -r backend/requirements.txt` bisa bentrok antara `emergentintegrations` dan
wheel `litellm`; pasang tiga paket itu saja bila paket lain sudah ada).

## Portal Pelanggan
- Login OTP; **OTP master pengujian = `000000`** (env `PORTAL_MASTER_OTP`).
- Nomor/nama pelanggan demo dapat dilihat di halaman Customer (hasil seed `customers`).

## Catatan pengujian
- Tidak ada backdoor auth. Halaman login punya tombol **"Masuk cepat"** yang hanya memanggil
  `POST /api/auth/login` biasa dengan akun demo di atas (boleh dihapus sebelum go-live).
- Bersihkan `localStorage` saat berganti peran agar sesi lama tidak terbawa.
- Login endpoint: `POST {REACT_APP_BACKEND_URL}/api/auth/login` body `{"email": "...", "password": "Sipro#2026"}`.

## Sesi & perpanjangan (Fase 54) — yang DIUJI, jangan dianggap bug
- **Sesi diperpanjang DIAM-DIAM.** Token kerja berumur 24 jam, tetapi klien memperpanjangnya
  sendiri pada `exp − 5 menit` dan juga saat tab kembali terlihat. Jadi selama menguji, sesi
  **tidak boleh** habis sendiri — kalau habis, itu cacat.
- **`POST /api/auth/refresh`** memerlukan bekal `refresh_token`. Peramban memakai cookie
  `httponly`; klien non-peramban (skrip/gate) boleh mengirimnya di **badan permintaan**
  (`{"refresh_token": "..."}`) atau tajuk `X-Refresh-Token`.
- **Tajuk `X-Session-State`** menyertai setiap penolakan sesi:
  `missing` (belum masuk) · `expired` (boleh diperpanjang) · `invalid` (bekal tidak dikenali /
  salah jenis) · `revoked` (akun dinonaktifkan atau organisasi disuspend).
  **Hanya `expired`** yang dicoba diperpanjang klien; sisanya langsung mengantar ke halaman
  masuk. Kamusnya di `backend/reference_p54.py` (`session_state`).
- **Spanduk peringatan sesi (`session-warning-banner`) SEHARUSNYA TIDAK MUNCUL** pada
  pemakaian normal. Ia hanya muncul bila perpanjangan otomatis GAGAL. Menganggap
  ketidakhadirannya sebagai "fitur hilang" adalah salah lapor.
- **Kembali ke tempat kerja.** Bila sesi benar-benar berakhir, halaman yang sedang dibuka
  dicatat; sesudah masuk ulang pengguna DIKEMBALIKAN ke sana (`login-return-to-hint`
  menampilkan janjinya, dan janji itu harus ditepati). Catatan ini **sekali pakai**: membuka
  `/login` saat sudah masuk tidak boleh memantulkan ke halaman lama.
- **Perpanjangan bukan celah.** Akun yang dinonaktifkan dan organisasi yang disuspend **TIDAK
  BISA** memperpanjang sesi (`revoked`), dan token kerja yang masih sah pun **berhenti
  bekerja** begitu akunnya dimatikan. Peran terbatas tetap terbatas memakai token hasil
  refresh (mis. `sales@` tetap 403 di modul pajak) — itu benar, bukan cacat.
- **Super admin yang sedang "bertindak sebagai" penyewa lain** tetap di penyewa itu sesudah
  sesinya diperpanjang. Kalau ia mendadak pulang ke `org-sipro`, itu cacat.
- **Portal pembeli SENGAJA tidak punya perpanjangan otomatis** (masuknya lewat OTP; menyimpan
  bekal 7 hari di perangkat pembeli bukan pertukaran yang pantas). Yang wajib ada di portal
  adalah akhir yang jujur: sesi dibersihkan dan `portal-session-notice` menjelaskan sebabnya
  dengan kalimat untuk pembeli.
- **Dua dunia sesi terpisah**: token portal tidak bisa dipakai di endpoint staf dan
  sebaliknya. Keduanya menjawab 401 — itu benar.
- Untuk menguji keadaan "sesi berakhir" tanpa menunggu 24 jam: pakai
  **`python3 scripts/_token54.py`** (menerbitkan token bertanda tangan sah dengan waktu yang
  dipalsukan; peran tetap dibaca dari database, jadi ini bukan celah hak akses):
  ```
  python3 scripts/_token54.py                          # superadmin, kedaluwarsa 5 menit
  python3 scripts/_token54.py --email=sales@sipro.co.id
  python3 scripts/_token54.py --detik=60               # masih sah 60 detik
  python3 scripts/_token54.py --jenis=refresh --detik=-10
  ```
  lalu di console peramban `localStorage.setItem('sipro_token', '<token>')` dan muat ulang
  halaman DALAM (mis. `/leads`). Harapan: halaman TETAP TERMUAT (pulih diam-diam). Untuk
  menguji sesi yang BENAR-BENAR mati, hapus cookie situs lebih dulu — bekal perpanjangan ada
  di cookie `refresh_token` yang `httponly`.

## Analitik & BI (Fase 44) — yang DIUJI, jangan dianggap bug
- **Metrik yang mengaku "belum ada data" itu BENAR.** 6 dari 47 metrik memang belum punya
  sumber data di sistem (demografi lead, alasan reschedule survei, pendapatan add-on tanpa
  `price_breakdown`, margin proyek tanpa budget operasional, waktu jual dari riwayat status
  bentukan migrasi, alasan lost yang belum diisi). Aturan repo: **jangan pernah menampilkan 0
  untuk data yang tidak ada** — kartunya menulis "belum ada data" + menyebut apa yang kurang.
- **Lencana "Dihitung dari sebagian data (40/47)"** juga benar: angkanya sah tetapi cakupannya
  belum penuh (mis. hanya 40 dari 47 lead punya `stage_history`).
- **Row-scope**: `sales@sipro.co.id` HANYA melihat metrik miliknya (server memaksa lewat
  `owner_email`); tombol "Hitung ulang snapshot" sengaja TIDAK muncul untuknya
  (butuh `analytics:manage`). Peran ber-`manage`: owner, super_admin, manajer sales, manajer
  keuangan, manajer proyek, supervisor DM.
- **Snapshot bukan kebenaran**: `POST /api/analytics/snapshots/rebuild` selalu menghitung ulang
  dan MEMPERBAIKI baris lama; gate membuktikannya dengan sengaja merusak satu nilai snapshot.

## Konstruksi Fase 46 — yang DIUJI, jangan dianggap bug
- **Unit tanpa jadwal menulis "belum ada data", bukan 0%.** `planned_progress`,
  `deviation`, `days_late` sengaja `null` + daftar `missing[]` ("jadwal_pembangunan",
  "rencana_bayar"). Menampilkan 0 untuk data yang tidak ada = cacat, bukan sebaliknya.
- **Tombol "Mulai Bangun" default = PERINGATAN.** Setting `build.require_dp_before_start`
  bawaannya **False**: unit boleh dimulai walau DP belum terbukti, TAPI peringatan wajib
  dicentang + alasan **minimal 5 huruf** (tercatat di `start_gate_log` + aktivitas + audit).
  Bila admin menyalakan setting, alasan yang sama MEMBLOKIR (`POST /api/build/unit/{id}/start`
  → 400 "Belum bisa dimulai").
- **Pelaksana lapangan (`site@sipro.co.id`) mendapat 403 di "Mulai Bangun"** — itu pemisahan
  tugas (`construction:approve`), bukan bug. Ia tetap boleh **mengajukan** hasil kerja.
- **Mengajukan hasil kerja WAJIB foto** (bawaan 2 foto untuk langkah persiapan) + checklist
  mutu lengkap; pengaju tidak boleh memverifikasi pekerjaannya sendiri (403).
- **Data demo gerbang:** `seed_phase46` menjadwalkan **satu unit tanpa memulainya** (mis.
  `A-05`/`A-03`, lencana kesiapan "peringatan") supaya dialog Mulai Bangun bisa dicoba. Bila
  sudah ditekan seseorang, unit itu jadi "berjalan" dan seed **tidak** mengembalikannya —
  jalankan `bash scripts/seed_reset.sh` bila butuh keadaan awal lagi.
- **Unit fixture uji:** `GATE46-01` (gate) dan `POC46-01/02` (POC) dibuat & dibuang otomatis.
  Bila terlihat di papan berarti ada run yang mati di tengah; jalankan gate/POC sekali lagi
  (keduanya membersihkan sisa sebelum mulai).
- **Izin tanpa tanggal berlaku** ditulis "masa berlaku belum dicatat" — bukan "aman
  selamanya"; izin `disetujui` yang tanggalnya lewat dilaporkan **kedaluwarsa**.

## Fase 47 — yang DIUJI, jangan dianggap bug
- **Mutasi rekening yang belum dicocokkan BUKAN pelunasan.** Saldo tagihan pelanggan tidak
  berubah sampai kasir menekan "Cocokkan". Itu inti fase ini, bukan data yang tertinggal.
- **Bukti transfer dari portal berstatus "menunggu verifikasi".** Tagihan **tidak** berkurang
  sebelum finance memverifikasi; pesan di portal memang menegaskan hal itu.
- **Hanya Manajer Keuangan (`finlead@sipro.co.id`) yang boleh MEMBATALKAN pencocokan bank**
  (`bank:approve`) dan **menyetujui/membayar rekap upah** (`labor:approve`). `finance@` biasa
  mendapat **403** di kedua aksi itu — pemisahan tugas, bukan cacat.
- **Yang MENGAJUKAN rekap upah tidak boleh menyetujuinya** (`pm@`/`site@` = 403).
- **Sales tidak punya akses** mutasi bank, bukti transfer, tenaga kerja, dan absensi (403);
  **sales juga tidak boleh menyetujui diskon penawarannya sendiri** (403 di
  `POST /api/quotations/{id}/decision`).
- **Simulasi KPR kosong menulis "belum ada data" + daftar yang kurang, bukan Rp 0.** Bunga &
  tenor harus datang dari bank; sistem tidak mengarang. Sama halnya: mutasi bank tanpa kolom
  saldo ditulis "saldo belum dicatat", dan selisih rekonsiliasi yang tak terjelaskan
  dinyatakan sebagai sebab `unexplained` beserta nominalnya.
- **Alasan wajib**: pembatalan/pengabaian pencocokan & keputusan diskon minimal **5 huruf**,
  penolakan bukti transfer minimal **10 huruf** (alasannya dibaca pelanggan di portal).
- **Absensi**: tanggal yang belum terjadi ditolak; satu orang satu baris per hari (koreksi =
  baris DIPERBARUI + riwayat, bukan baris kembar); tanggal yang sudah masuk rekap upah
  terkunci sampai rekapnya dibatalkan. Selisih dengan buku harian tampil sebagai
  **peringatan informasi** (match/mismatch/belum ada buku harian), tidak memblokir.
- **Rekap upah** menolak periode yang bertumpang dan periode tanpa absensi berupah (tidak ada
  dokumen kosong). Pembayaran melahirkan jurnal Dr `1-1600` (pekerjaan dalam proses) /
  Cr `1-1200` (bank) dan tidak bisa dibayar dua kali.
- **Data demo Fase 47** (`seed_phase47`, `demo_batch="fase47"`): 1 rekening bank + mutasi yang
  SENGAJA dibiarkan belum dicocokkan (satu di antaranya bernominal sama dengan termin nyata
  supaya usulan pencocokan muncul), 1 bukti transfer **pending**, 6 tenaga kerja + absensi 2
  hari terakhir, dan 1 penawaran berdiskon **di atas kewenangan** (menunggu persetujuan).
  Seed tidak pernah menekan tombol milik manusia. Bila keadaan awal dibutuhkan lagi:
  `bash scripts/seed_reset.sh`.
- **Bahan uji gate** bertanda `gate47` (unit `GATE47-*`, pekerja/lead "Uji … Gate47") dibuat &
  dibuang otomatis. Bila terlihat di layar, ada run gate yang mati di tengah — jalankan gate
  itu sekali lagi (setiap gate membersihkan sisa sebelum mulai).
- **Impor mutasi bank = berkas CSV** (kolom yang dikenali: tanggal, keterangan, debet/kredit
  atau nominal+arah, saldo, referensi). **Tarikan API bank belum ada** dan tidak dijanjikan
  di layar. WhatsApp (kirim penawaran), e-sign, dan storage terkelola tetap **MODE SIMULASI**.

## Guardrail Fase 47 (cara membuktikan cepat)
```
python3 scripts/verify_bank_recon.py        # gate ke-31
python3 scripts/verify_portal_proof.py      # gate ke-32
python3 scripts/verify_quotation_labor.py   # gate ke-33
python3 scripts/mutasi_47.py --check        # pola 19 mutasi masih ada di kode (cepat)
python3 scripts/mutasi_47.py                # uji-mutasi penuh (~40 menit, restart backend)
bash scripts/run_all_gates.sh               # 33 gates
```

## Fase 48 — Pengadaan & Subkon lanjutan (yang DIUJI, jangan dianggap bug)
- **Pemisahan tugas paling ketat ada di sini.** Uang muka subkon & pencairan retensi hanya
  boleh DIPUTUS `finlead@sipro.co.id` (finance_manager). `finance@sipro.co.id` sengaja
  menerima **403** untuk `POST /api/subcon/advances/{id}/decision` dan
  `POST /api/subcon/retentions/{id}/release` — itu perilaku benar.
- **Tagihan yang melebihi barang diterima DITOLAK (400), bukan sekadar ditandai.** Hanya
  `finlead` (atau owner) yang boleh menerobos, wajib `override_hold=true` +
  `override_reason` minimal 10 huruf. Penolakan ini bukan bug.
- **Retensi tidak bisa dicairkan** selama masa pemeliharaan berjalan ATAU masih ada temuan
  punch list terbuka pada unit lingkup SPK. Data demo sengaja memuat keduanya supaya
  gerbangnya bisa dicoba manusia.
- **Transfer material antar proyek** butuh `materials:approve` (PM/owner) — `site@` sengaja
  403 supaya barang tidak berpindah pusat biaya tanpa persetujuan.
- **Angka "belum ada data" itu BENAR**: vendor tanpa transaksi tidak diberi skor 0, material
  tanpa harga masuk tidak dihitung nilainya, harga tanpa acuan tidak dinyatakan "wajar".
- Data demo `fase48`: vendor VND-01..03 + daftar harga, permintaan material PR yang stoknya
  kurang (untuk mencoba tombol **Buat PO**), uang muka UMK/2026/0001 + 2 potongan menunggu,
  batas stok minimum pada dua material.

## Penutupan Fase 48 (18 Agu 2026) — perubahan yang perlu diketahui penguji
- **Lingkungan dipulihkan dari repo GitHub `luarbinasaaa/sipro`.** `backend/.env` dibuat ulang:
  selain `MONGO_URL`/`DB_NAME` milik container, WAJIB ada `JWT_SECRET` **dan**
  `DEFAULT_ORG_ID="org-sipro"` (dengan TANDA HUBUNG). Semua gate & POC memakai `org-sipro`
  secara harfiah; menulis `org_sipro` membuat 4 pemeriksaan `verify_build_hub.py` merah
  padahal kodenya benar.
- **Bug laten yang diperbaiki:** `seed.py` mengimpor `_run_3way` dari `procurement_router`
  (sudah dipindah ke `procurement_extra.evaluate_bill` pada Fase 48B), sehingga container
  dengan **DB kosong** mati saat startup dan tidak pernah ter-seed. Sekarang seed penuh
  (sampai Fase 48) jalan di DB bersih.
- **Data demo baru:** uang muka **UMK/2026/0003** (SPK/2026/0002 · PT Instalasi Prima ·
  Rp 15.000.000) sengaja ditinggalkan berstatus **"Diajukan / menunggu keputusan"** supaya
  gerbang "hanya Manajer Keuangan yang boleh memutuskan uang muka" bisa dicoba manusia.
  Pengajunya `pm@sipro.co.id` (aturan empat-mata tetap berlaku: pengaju tidak boleh
  memutuskan). Dokumen ini idempoten lewat penanda `demo_marker="advance_menunggu"` — bila
  sudah diputus, restart backend TIDAK membuat uang muka baru (dulu sempat menumpuk).
  Kembalikan keadaan awal dengan `bash scripts/seed_reset.sh`.
- **`/materials` sekarang menolak dengan sopan.** Sebelum ini `sales@` yang membuka
  `/materials` melihat tabel kosong + "Belum ada transaksi" padahal server menjawab **403** —
  layar berbohong "tidak ada data" untuk hal yang benar-benar "tidak boleh dilihat". Sekarang
  muncul kartu **AKSES DITOLAK** (`data-testid="materials-access-denied"`), sama seperti
  `/construction`.
- **PR/2026/0003 sudah dipakai** untuk membuktikan alur "Buat PO dari kekurangan stok"
  (lahir **PO/2026/0005**, Rp 34.250.000, berjejak `requisition_id`). Karena itu tombol
  "Buat PO" pada PR itu kini menolak dengan sopan ("Seluruh kebutuhan sudah tercukupi …
  PO terkait: PO/2026/0005") dan tombolnya mati — **itu bukti idempoten, bukan cacat**.
  PR/2026/0001 masih tersedia untuk dicoba manusia.
- **Pembanding harga tidak punya tombol.** Kotak "Pembanding harga" muncul sendiri begitu
  sebuah material dipilih di tab **Daftar Harga** (`vendor-price-material-select`). Test id
  `vendor-price-compare-button` sudah DIHAPUS karena tidak pernah dirender dan membuat uji
  E2E salah lapor.
- **Test id tab permintaan material = `materials-tab-requisitions`** (berakhiran huruf s).

## Data demo Fase 49 (penutupan buku & pajak) — dibaca agen lanjutan
- **Identitas pajak DEMO** terisi oleh `seed_phase49.py` **hanya bila masih kosong**:
  `tax.company_npwp = 0012345678901000`, `tax.company_idtku = 0012345678901000000000`.
  Ganti dengan NPWP asli sebelum berkas dikirim ke DJP.
- **Faktur demo** ada di masa pajak **BULAN LALU** (bukan bulan berjalan) atas unit yang
  dibukukan seed (`deals.demo_marker = "deal_faktur_demo"`). Pembelinya SENGAJA belum punya
  NPWP → tab `/tax?tab=faktur-export` memperlihatkan ekspor **DITAHAN** beserta faktur mana
  yang harus dilengkapi; tuntaskan lewat tombol **Ganti** (isi NPWP) lalu unduh XML/CSV.
- **Bukti potong demo** (`0100000004`, PPh 4(2) konstruksi Rp 875.000, kode objek 28-409-11)
  terbit otomatis dari pembayaran tagihan `CV Sumber Beton Sejahtera`
  (`ap_invoices.demo_marker = "bill_pph_konstruksi"`, status `partial`).
- **Potongan PPh fee mitra Rp 425.000 SENGAJA dibiarkan tanpa bukti potong** supaya daftar
  "kandidat" di tab e-Bupot punya isi yang jujur (tie-out menyebut selisihnya). Menerbitkannya
  lewat UI adalah perilaku benar, bukan perbaikan bug.
- **Masa pajak berjalan adalah ruang kerja uji inti.** `poc/poc_49.py`, `verify_closing.py`, dan
  `verify_tax_compliance.py` menghitung PPN keluaran & menguji ekspor di masa berjalan. Bila Anda
  menerbitkan faktur baru di bulan berjalan lewat UI lalu tidak membatalkannya, gate 38 bisa
  melaporkan ekspor "masih ditahan karena faktur lain" — itu keadaan yang benar, bukan bug.
- **Bulan/tahun buku TIDAK ditutup oleh seed** (keputusan manusia). Bulan berjalan memang punya
  pemeriksaan yang MENAHAN penutupan (mutasi bank belum dicocokkan, tagihan menunggu
  persetujuan) — itu bahan mencoba jalur "tahan" & "terobosan beralasan" di
  `/accounting?tab=closing`.
- Peran yang dibutuhkan: `finlead@sipro.co.id` (boleh menerobos tutup bulan),
  `owner@sipro.co.id` (tutup/buka tahun buku, buka periode), `finance@sipro.co.id`
  (pajak: terbit/ganti/batal/ekspor), `sales@sipro.co.id` (pembanding 403).

## Fase 50 — Serah Terima (BAST), Garansi & Antrean Perangkat (yang DIUJI, jangan dianggap bug)
- **Serah terima DITAHAN itu benar.** `/units/{id}` tab **Serah Terima & Garansi** menolak
  menerbitkan BAST selama masih ada temuan punch terbuka, progres belum selesai, inspeksi
  serah terima belum lolos, kewajiban pembayaran belum beres, atau dokumen wajib belum
  terverifikasi. Pesannya menyebut sebab satu per satu + tautan halaman sumbernya.
- **Yang boleh MENEROBOS bukan yang boleh MENERBITKAN.** `pm@` & `finance@` boleh menerbitkan
  (`handover:create`); menerobos daftar periksa hanya `finlead@`/`owner@`/`superadmin@`
  (`handover:override`) dan wajib alasan **≥10 huruf**. `pm@` mendapat **403** saat mencoba
  menerobos — itu pemisahan tugas, bukan cacat.
- **Pembatalan BAST hanya `handover:cancel`** (`finlead@`/`owner@`/`superadmin@`); `finance@`
  sengaja **403**. Pembatalan **DITOLAK** selama masih ada klaim garansi berjalan, dan
  dokumennya TIDAK dihapus (status "Dibatalkan" + alasan + siapa).
- **Penerbitan BAST idempoten.** Menekan "Terbitkan BAST" dua kali (atau kiriman antrean
  diputar ulang) TIDAK membuat dokumen kedua — nomor lamanya dipakai kembali.
- **Klaim garansi yang lewat masa TETAP tercatat** berstatus *Ditolak beralasan* dengan
  tanggal habisnya. Itu jawaban tertulis untuk pembeli, bukan data sampah.
- **Pemisahan tugas klaim garansi:** pengaju (`manager@`/`sales@`/CS, `warranty:create`)
  **403** di keputusan klaim; pelaksana (`site@`, `warranty:update`) **403** di pemeriksaan
  mutu; dan **pemeriksa tidak boleh orang yang mengerjakan** (dijaga di data — `pm@` yang
  baru saja menyelesaikan perbaikan ditolak 400 saat mencoba meluluskannya sendiri).
- **"Selesai" wajib bukti foto.** Menyatakan perbaikan selesai tanpa foto ditolak (dijaga di
  kontrak permintaan DAN mesin). Penutupan klaim butuh **pengakuan pembeli** (`ack_by`).
- **Masa garansi per bagian dibaca dari Pusat Konfigurasi** (`warranty.struktur_months` 120,
  `atap_plafon` 12, `dinding_lantai` 12, `plumbing` 6, `listrik` 6, `kusen` 6, `finishing` 3;
  ambang "hampir habis" 30 hari). Mengubah setelan berlaku untuk BAST yang diterbitkan
  SESUDAHNYA — dokumen lama tetap memakai masa yang tercetak di dalamnya.
- **Rumah yang belum diserahterimakan menulis "belum ada data"**, bukan 0 bulan garansi; rekap
  klaim tanpa data menulis rata-rata hari "belum ada datanya", bukan 0 hari.
- **Antrean perangkat (Fase 50B):** absensi, buku harian, temuan/status punch, klaim garansi,
  dan bukti perbaikan semuanya membawa `client_ref`. Mengirim ulang penanda yang sama dijawab
  `replay` (bukan data kedua) — jadi "absensi tercatat sekali padahal ditekan dua kali" adalah
  perilaku BENAR. Antrean bisa dibuka dari spanduk jaringan di **halaman mana saja**.
- **Data demo Fase 50** (`seed_phase50.py`, `demo_batch="fase50"`): unit **A-06** sengaja
  dibiarkan *siap BAST* (bisa dicoba manusia), unit **B-01** sudah punya `BAST/2025/0001`
  (bertanggal lampau) dengan 2 klaim garansi — satu berjalan, satu ditolak karena lewat masa.
  Bila A-06 sudah diserahkan seseorang, seed TIDAK mengembalikannya: jalankan
  `bash scripts/seed_reset.sh` bila butuh keadaan awal lagi.
- **Bahan uji gate/POC bertanda `gate50`** (proyek "Proyek Gate 39/40", unit `G39-*`/`G40-*`)
  dibuat & dibuang otomatis. Bila terlihat di layar berarti ada run yang mati di tengah —
  jalankan gate itu sekali lagi.

## Guardrail Fase 50 (cara membuktikan cepat)
```
python3 poc/poc_50.py                        # POC core 50A
python3 scripts/verify_handover_warranty.py  # gate ke-39 (43 pemeriksaan)
python3 scripts/verify_offline_queue.py      # gate ke-40 (14 pemeriksaan)
python3 scripts/mutasi_50.py --check         # pola 37 mutasi masih ada di kode (cepat)
python3 scripts/mutasi_50.py                 # uji-mutasi penuh (~45 menit, backend reload)
bash scripts/run_all_gates.sh                # 40 gates
```

---

## Fase 51 — yang DIUJI, jangan dianggap bug

### 51A Retensi subkon ↔ klaim garansi (`/subcon?tab=retentions`)
- **Retensi yang DITAHAN karena klaim garansi berjalan adalah perilaku BENAR.** Kartunya
  menyebut **nomor + judul klaim** dan menautkan ke papan garansi
  (`/construction?tab=warranty`). Retensi adalah jaminan mutu: ia tidak boleh cair saat
  mutunya sedang dipersoalkan.
- **Hanya Manajer Keuangan (`finlead@`) yang boleh MENGABAIKAN penahanan** (izin
  `subcon_finance:override`). `finance@` dan `pm@` mendapat **403** dan di layar melihat
  **kalimat penjelas** — bukan tombol mati. Itu pemisahan tugas, bukan cacat.
- **Alasan pengabaian wajib ≥10 huruf** (dijaga kontrak permintaan DAN mesin). Kode yang
  tidak sedang menahan, atau kode di luar daftar yang boleh diabaikan, **ditolak 400**.
- **Sesudah diabaikan, penahanannya TETAP DITAMPILKAN** (blok violet "Penahanan yang
  diabaikan" + siapa/kapan/kenapa). Itu untuk auditor — bukan sisa tampilan.
- **Penahanan hilang SENDIRI begitu klaimnya ditutup** — tidak perlu diabaikan.
- **Pengaju pencairan tidak boleh mencairkan sendiri** (`pm@` mengajukan → `finlead@`
  mencairkan). Kiriman ulang dengan `client_ref` sama dijawab `replay` **tanpa** tagihan AP
  kedua; pencairan kedua ditolak 400 "tidak bisa dicairkan dua kali".
- **"Masa pemeliharaan belum dicatat"** bukan "0 hari" — 0 hari berarti sudah lewat, artinya
  kebalikan. Layar menulis kalimat sebabnya.

### 51B Pengingat WhatsApp otomatis (`/automation?tab=reminders`)
- **Mode kirim = `simulasi`** selama `WHATSAPP_TOKEN`/`WHATSAPP_PHONE_ID` kosong (keputusan
  owner untuk lingkungan demo). Statusnya ditulis **`simulasi`, bukan `terkirim`** — itu
  kejujuran yang disengaja, bukan kegagalan. Isi pesannya tetap tersimpan & bisa dibaca.
- **"Sudah diingatkan untuk periode ini"** pada kandidat = dedup bekerja. Menjalankan dua
  kali TIDAK mengirim dua kali (dijaga index unik database `uq_wa_reminder_dedup`).
- **Yang boleh MENJALANKAN**: `sales_manager`/`marketing`/`dmlead`/`finlead`/owner
  (`reminders:manage`). `sales@` dan `pm@` boleh **melihat** riwayat & kandidat tetapi
  mendapat **403** saat menjalankan — di layar berupa kalimat, bukan tombol mati.
- **Kandidat tertahan tetap ditampilkan beserta sebabnya** (nomor WA belum dicatat, template
  belum disetujui, pengingat dimatikan di Pusat Konfigurasi). Menyembunyikannya membuat
  pertanyaan "kenapa pembeli ini tidak pernah diingatkan" tidak bisa dijawab.
- **Ambang batas dari Pusat Konfigurasi** grup `pengingat`: `reminder.warranty_days` 30,
  `installment_days_before` 3, `overdue_every_days` 7. Mengubahnya benar-benar mengubah
  daftar kandidat (dibuktikan gate).
- **Termin yang sudah lunas & garansi yang sudah habis TIDAK diingatkan** — termasuk termin
  lunas di dalam tagihan yang masih berjalan (tidak ada pengingat "Rp 0").
- Jadwal otomatis: **08:00 WIB** sekali sehari (`wa_reminder_daily`).

### 51C Portal pembeli (`/portal`, OTP master `000000`)
- **Pembeli demo yang rumahnya SUDAH diserahterimakan = `Bapak Hendra Demo (Fase 50)`,
  telepon `+6281250000502`** (unit **B-01**): punya `BAST/2025/0001`, kwitansi
  `KWT/2026/0003`, dan 3 klaim garansi — `KG/2026/0003` berstatus **`diverifikasi`** sehingga
  tombol pengakuan muncul. Akun portal dibuat otomatis saat pertama kali meminta OTP.
- **Jangan pakai `Ibu Dewi Kartika` (+628121111111) untuk menguji 51C**: rumahnya (A-01)
  belum diserahterimakan, jadi tab Dokumen & Garansi memang **kosong-jujur** di sana. Catatan
  lama yang menulis "pembeli demo B-01 = Ibu Dewi Kartika" SALAH dan pernah membuat uji UI
  salah lapor.
- Tab **Dokumen** berisi BAST + kwitansi +
  dokumen transaksi; semua diunduh lewat sesi portal (**bukan** tautan mentah bertoken).
- **Dokumen orang lain dijawab 404, bukan 403** — membedakan "ada tapi bukan milikmu" dari
  "tidak ada" membocorkan keberadaan dokumen orang lain.
- **Pengakuan penyelesaian klaim** hanya untuk klaim yang sudah **`diverifikasi`** (mutunya
  diperiksa staf). Klaim yang masih `dikerjakan` ditolak 400 dengan alasan jujur.
- **"Belum beres" TIDAK menutup klaim** — klaim dikembalikan ke `dikerjakan`, catatan pembeli
  tersimpan, dan tim yang menangani diberi tahu. Dialognya menyebut akibat itu apa adanya.
- **Pengakuan tercatat atas nama PEMBELI** (nama + nomor dari sesi portalnya), bukan staf.
- Belum ada BAST/kwitansi → **kalimat sebab** ("rumah belum diserahterimakan…", "belum ada
  data, bukan Rp 0"), bukan tabel hampa.
- **Bahan uji gate/POC bertanda `gate51`** (proyek/unit `G51-*`, nomor `BAST/G51/*`,
  `KWT/G51/*`) dibuat & dibuang otomatis. Bila terlihat di layar berarti ada run yang mati
  di tengah — jalankan gate itu sekali lagi.

## Guardrail Fase 51 (cara membuktikan cepat)
```
python3 poc/poc_51.py                            # POC inti 51 (67 pemeriksaan)
python3 scripts/verify_retention_warranty.py     # gate 41 (40 pemeriksaan)
python3 scripts/verify_wa_reminders.py           # gate 42 (54 pemeriksaan)
python3 scripts/verify_portal_warranty.py        # gate 43 (46 pemeriksaan)
python3 scripts/mutasi_51.py --check             # 52 pola mutasi masih ada (cepat)
python3 scripts/mutasi_51.py --ringkas           # laporan kumulatif: 52 TERTANGKAP
python3 scripts/mutasi_51.py --pulihkan          # bila run mutasi mati di tengah
bash scripts/run_all_gates.sh                    # 43 gates, OVERALL PASS
```
Catatan: gate 42 **menolak berjalan** bila mode kirim `nyata` — menjalankan pengingat dengan
kredensial sungguhan berarti mengirim WhatsApp ke pelanggan hanya untuk menghijaukan gate.
