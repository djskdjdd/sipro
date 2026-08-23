# Rencana Development SIPRO — Fase 56

> **STATUS PER PEMBARUAN TERAKHIR**
>
> | Bagian | Status |
> |---|---|
> | Pemulihan lingkungan dari repo `dnkajshxhs/sipro` di container baru | **SELESAI** — `backend/.env` dibuat ulang (`JWT_SECRET`, `DEFAULT_ORG_ID="org-sipro"`, `PORTAL_MASTER_OTP`), dependensi dipasang (APScheduler/reportlab/tzlocal + `@fontsource/*`, `@tanstack/react-table`), seed Fase 16..53 jalan di DB bersih, login OK |
> | Baseline guardrail | **SELESAI** — `bash scripts/run_all_gates.sh` → **OVERALL PASS (46 gates)** sebelum satu baris pun disentuh |
> | 56A — Cacat permukaan Fase 53 (temuan uji peramban) | **SELESAI** — 3 cacat diperbaiki, gate 46 diperkuat 78 → **95 pemeriksaan**, `mutasi_53.py` 37 → **46 mutan, 46 TERTANGGKAP / 0 LOLOS** |
> | 56B — Uji E2E permukaan layar Fase 53 (`testing_agent_v3`) | **BERJALAN** |
> | 56C — Fitur baru: **Pembatalan kontrak & Refund berjurnal** | BELUM |
> | 56D — Dokumentasi & penutupan | BELUM |

---

## 0) Kenapa dev sempat berhenti (dan apa yang sebenarnya terjadi)

Laporan terakhir sebelum fase ini berbunyi "login gagal" saat memverifikasi rantai Fase 53 di
peramban. Root cause-nya **bukan aplikasi**: skrip Playwright dijalankan **tanpa `await`**
sehingga setiap `page.*` hanya mengembalikan coroutine — tidak ada satu aksi pun yang benar-benar
dijalankan, dan `locator.count()` mencetak `<coroutine object …>`. Dijalankan ulang dengan
`await`, seluruh rantai TERBUKTI hidup (lihat 56A).

Pelajaran yang dicatat: **perangkat uji yang salah menghasilkan laporan yang salah**, dan
laporan yang salah membuat fase berikutnya dibangun di atas ketakutan yang tidak nyata.

---

## 1) 56A — Cacat permukaan Fase 53 (SELESAI)

Tiga cacat ini semuanya **tidak bisa terlihat dari uji HTTP** — hanya manusia (atau peramban)
yang bisa menemukannya, dan itulah alasan lapis uji ini ada.

1. **Janji yang tidak ditepati.** Tombol "Jadikan Pembeli" dan tautan "Buka Kontrak & Legal"
   mengarah ke `/customers/{id}?hub=kontrak53`, padahal `CustomerProfilePage` membaca penanda
   `?tab=`. Akibatnya pemakai mendarat di tab **Ringkasan** — kontrak yang baru saja lahir tidak
   diperlihatkan. **Diperbaiki**: kedua tautan memakai `?tab=kontrak53`.
2. **Bahasa mesin dipakai kepada manusia.** Daftar komponen biaya yang belum diisi ditulis
   sebagai **nama kolom** (`NOTARY_FEE`, `BANK_FEE`, `INSURANCE`, `PPH_SELLER`) di tiga tempat:
   spanduk "masih SEMENTARA" di layar, catatan total pada API, **dan di dalam dokumen SPR yang
   ditandatangani pembeli**. **Diperbaiki**: `build_breakdown()` menerbitkan
   `costs_incomplete_labels` (label manusia) dan semua permukaan manusia memakainya.
3. **Layar berbohong "tidak ada".** Sales yang membuka pembeli milik rekannya melihat
   "**Belum ada kontrak** — kontrak lahir saat lead dijadikan PEMBELI", padahal kontraknya ADA
   (hanya di luar lingkup datanya). Ini kelas cacat yang sama dengan `/materials` (Fase 48) dan
   `PanelStateView` (Fase 52). **Diperbaiki**: `GET /api/contracts` mengembalikan
   `reason_code="di_luar_lingkup"` + kalimat sebab (tanpa membocorkan nomor/nilai kontrak), dan
   layar menampilkan kartu tersendiri (`contract-out-of-scope`).

**Guardrail (agar tidak kembali diam-diam)**
- Gate 46 `scripts/verify_contract_legal_docgen.py`: **95 pemeriksaan** (K21/K21b janji tautan
  tab, K22–K24 bahasa label, K25/K25b kejujuran lingkup, D26b–D26i bukti HTTP + isi dokumen).
- `scripts/mutasi_53.py`: **46 mutan** (M38–M46 baru), semuanya **TERTANGKAP**.
- `bash scripts/run_all_gates.sh` → **OVERALL PASS (46 gates)** sesudah perbaikan.

---

## 2) 56B — Uji E2E permukaan layar Fase 53 (BERJALAN)

**User stories yang diuji di peramban**
1. Sebagai Manajer Sales, saya bisa membawa satu lead baru sampai menjadi PEMBELI: buat lead →
   reservasi unit → konfirmasi booking → "Jadikan Pembeli" (skema KPR + NIK) → **mendarat tepat
   di tab "Kontrak & Legal"** dengan kontrak yang baru lahir.
2. Sebagai pemakai, komponen biaya yang belum diisi saya baca sebagai "Belum diisi (bukan nol)",
   dan total ditandai "masih SEMENTARA" **dengan nama biaya, bukan nama kolom database**.
3. Sebagai Keuangan, saya bisa mengisi komponen biaya; sesudah lengkap penanda "sementara"
   hilang dan dokumen SPR KPR boleh diterbitkan.
4. Sebagai Manajer Sales, tahap legal yang tertahan menyebutkan SEBABnya; Keuangan tidak melihat
   tombolnya (pemisahan tugas) dan mendapat kalimat penjelas.
5. Sebagai Manajer Sales, panel KPR menuntut BUKTI: bank dipilih dari Kamus Data (bukan diketik),
   SP3K ditolak tanpa berkas, dan diterima bersama berkas + plafon.
6. Sebagai Manajer Sales, dokumen owner mengikuti skema: SPR KPR boleh, SPR Cash **terkunci
   dengan sebab**, nomor berformat `{urut}/{kode}/{proyek}/{romawi}/{tahun}`, dan bisa dicetak
   (PDF).
7. Sebagai Sales yang bukan pemegang lead, saya membaca "**kontrak ini di luar lingkup data
   Anda**" — bukan "belum ada kontrak".
8. Regresi Fase 54: sesi tidak mati sendiri; spanduk peringatan sesi tidak muncul pada
   pemakaian normal.

---

## 3) 56C — Fitur baru: **Pembatalan kontrak & Refund berjurnal**

**Kenapa ini yang dipilih.** Dokumen SPR yang sudah dicetak sistem ini **menjanjikan** aturan
pembatalan: potongan **35%** bila dibatalkan sebelum pembangunan, **50%** bila sedang dibangun,
dan refund dibayar setelah unit terjual kembali (`cancellation.cut_before_build_pct`,
`cut_during_build_pct`, `refund_clause` — semuanya sudah ada di Pusat Konfigurasi dan tercetak di
dokumen). Tetapi **tidak ada satu pun layar atau endpoint yang bisa menjalankan janji itu**:
- KPR yang DITOLAK bank hanya *mengusulkan* nominal refund; tidak ada yang membukukannya.
- `CustomerPaymentPlanTab` menulis apa adanya bahwa "mesin pembatalan/refund berjurnal belum
  ada" — pengakuan jujur yang sudah waktunya ditutup.
- Unit yang batal tidak punya jalur resmi kembali ke stok, sehingga rumah bisa "hilang" dari
  ketersediaan hanya karena satu pembeli mundur.

**User stories (rencana)**
1. Sebagai Manajer Sales, saya bisa mengajukan pembatalan kontrak dengan **alasan wajib** dan
   sistem menghitung potongan sesuai ketentuan SPR (memakai keadaan pembangunan NYATA).
2. Sebagai Manajer Keuangan, saya **memutuskan** pembatalan (pemisahan tugas: pengaju ≠
   pemutus), dan pada saat itulah jurnal lahir (potongan = pendapatan lain-lain, sisa = utang
   refund ke pembeli).
3. Sebagai Keuangan, saya membayar refund dari kas/bank dan sistem menutup utang refund itu —
   tidak ada refund yang dibayar dua kali (idempoten lewat `client_ref`).
4. Sebagai pemakai, unit yang dibatalkan **kembali tersedia** di stok (atomik) dan jejaknya
   tercatat di riwayat unit — bukan lenyap tanpa sebab.
5. Sebagai pemakai, pembatalan **DITOLAK dengan sebab** bila kontraknya sudah AJB/BAST, atau
   bila masih ada penerimaan yang belum terverifikasi — bukan tombol mati.
6. Sebagai pembeli di portal, saya membaca status pembatalan & refund saya apa adanya (nominal
   potongan, dasar aturannya, dan kapan refund dibayar).
7. Sebagai auditor, saya bisa menelusuri: dokumen pembatalan → jurnal → pembayaran refund →
   pelepasan unit, dengan siapa/kapan/kenapa.

**Langkah**
1. POC isolasi `poc/poc_56.py` (HTTP nyata) — hitungan potongan, gerbang penolakan, jurnal
   berimbang, idempotensi, pelepasan unit atomik.
2. Backend: `cancellation_engine.py` + router + Kamus Data (`cancel_block`, `cancel_state`) +
   jurnal GL + dokumen pembatalan.
3. Frontend: dialog pengajuan (alasan + pratinjau potongan), kartu keputusan untuk
   `finlead@`, riwayat pembatalan pada profil pembeli, dan panel portal pembeli.
4. Guardrail: gate baru `scripts/verify_cancellation_refund.py` (didaftarkan ke
   `run_all_gates.sh`) + `scripts/mutasi_56.py` — semua mutan wajib TERTANGKAP.
5. E2E `testing_agent_v3` multi-peran (sales_manager → finlead → finance → portal).

---

## 4) 56D — Dokumentasi & penutupan
- `CODEBASE_MAP.md` (bagian FASE 56), `docs/v2/50_CANCELLATION_REFUND_SPEC.md`,
  `memory/test_credentials.md` (perilaku yang DIUJI, jangan dianggap bug), `test_result.md`,
  dan arsip rencana ke `memory/plan_archive_fase56.md`.

---

## 5) Kriteria selesai Fase 56
- Rantai Fase 53 terbukti hidup di peramban oleh agen uji, bukan hanya oleh gate.
- Tidak ada kode kolom yang sampai ke mata pemakai maupun ke dokumen yang ditandatangani.
- Tidak ada layar yang mengatakan "tidak ada" untuk sesuatu yang "bukan lingkup Anda".
- Pembatalan & refund bisa dijalankan end-to-end, berjurnal, idempoten, dan unit kembali ke
  stok — dengan gate + uji-mutasi yang membuktikan penjaganya bergigi.
- `bash scripts/run_all_gates.sh` → OVERALL PASS (47 gates sesudah 56C).
