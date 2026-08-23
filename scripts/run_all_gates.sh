#!/usr/bin/env bash
# run_all_gates.sh — jalankan SEMUA guardrail SIPRO, tampilkan ringkasan.
# Exit !=0 bila ada gate GAGAL. Usage: bash scripts/run_all_gates.sh
cd "$(dirname "$0")/.."

GATES=(
  validate_compliance.py
  health_check.py
  verify_rbac.py
  verify_api_contract.py
  check_nav_map.py
  audit_endpoint_sweep.py
  verify_data_integrity.py
  ux_audit.py
  forensic_audit.py
  audit_forms_deep.py
  verify_business_invariants.py
  verify_ui_surfaces.py
  verify_31.py
  verify_32.py
  verify_33.py
  verify_34.py
  verify_35.py
  verify_36.py
  verify_37.py
  verify_settings.py
  verify_masterplan.py
  verify_39b.py
  verify_ia_v2.py
  verify_41.py
  verify_partner.py
  verify_rbac_ui.py
  verify_ads.py
  verify_analytics.py
  verify_budget_target.py
  verify_build_hub.py
  verify_bank_recon.py
  verify_portal_proof.py
  verify_quotation_labor.py
  verify_procurement_vendor.py
  verify_subcon_retention.py
  verify_stock_control.py
  verify_closing.py
  verify_tax_compliance.py
  verify_handover_warranty.py
  verify_offline_queue.py
  verify_retention_warranty.py
  verify_wa_reminders.py
  verify_portal_warranty.py
  # Fase 52 — gate ke-44: satu panel yang ditolak tidak boleh mematikan halaman, dan layar
  # tidak boleh berbohong tentang sebabnya (403 ≠ "belum ada data"), termasuk peta menu yang
  # tidak boleh mengaku menu HIDUP itu terkunci.
  verify_panel_resilience.py
  # Fase 54 — gate ke-45: sesi tidak boleh mati mendadak (ada /auth/refresh, cookie basi
  # tidak mengalahkan Bearer yang sah, sebab 401 bisa dibedakan mesin), perpanjangan bukan
  # pintu belakang bagi akun/penyewa yang dicabut dan tidak memindahkan penyewa diam-diam,
  # dan bila sesi memang berakhir ia berakhir JUJUR (React diberi tahu + tempat kerja
  # dipulihkan) tanpa membocorkan istilah internal ke layar.
  verify_session_resilience.py
  # Fase 53 — gate ke-46 (utang yang dibayar di Fase 54): rantai LEAD -> PEMBELI -> KONTRAK ->
  # AKAD -> DOKUMEN OWNER TERCETAK. Sebelum ini seluruh rantai hanya dijaga `poc/poc_53.py`
  # yang TIDAK terdaftar di sini, jadi siapa pun bisa merusaknya dan rangkaian gate tetap
  # hijau. Termasuk penjaga statis yang POC tidak bisa lakukan (label dari Kamus Data, testId
  # tidak mati, field Bank wajib dropdown).
  verify_contract_legal_docgen.py
)

fail=0
# Log gate ditaruh di dalam repo (BUKAN /tmp): /tmp bisa dibersihkan sistem di tengah run
# panjang, dan ringkasan "gate mana yang gagal" ikut hilang justru saat dibutuhkan.
LOGDIR="memory/gatelogs"
mkdir -p "$LOGDIR"
declare -a results
for g in "${GATES[@]}"; do
  if python3 "scripts/$g" > "$LOGDIR/gate_${g}.log" 2>&1; then
    results+=("  PASS  $g")
  else
    results+=("  FAIL  $g")
    fail=1
  fi
done

echo ""
echo "==================== GATE SUMMARY ===================="
for r in "${results[@]}"; do echo "$r"; done
echo "======================================================"
if [ $fail -ne 0 ]; then
  echo "OVERALL: FAIL — detail gate yang gagal:"
  for g in "${GATES[@]}"; do
    if ! grep -qE "PASSED|Total temuan perlu tindakan: 0" "$LOGDIR/gate_${g}.log" 2>/dev/null; then
      echo "----- $g -----"; tail -n 15 "$LOGDIR/gate_${g}.log";
    fi
  done
  exit 1
fi
echo "OVERALL: PASS (${#GATES[@]} gates)"
