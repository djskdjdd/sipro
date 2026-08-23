import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Ban, Banknote } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table";
import EmptyState from "@/components/patterns/EmptyState";
import MetricCard from "@/components/patterns/MetricCard";
import MoneyText from "@/components/patterns/MoneyText";
import StatusPill from "@/components/patterns/StatusPill";
import { ErrorState, LoadingCards } from "@/components/patterns/StateViews";
import { useAuth } from "@/context/AuthContext";
import api from "@/services/apiClient";
import { formatDateTimeWIB } from "@/utils/formatters";
import { P56 } from "@/constants/testIds";

/**
 * CancellationsPanel (tab Keuangan → "Pembatalan & Refund") — Fase 56C.
 *
 * Kenapa daftar ini perlu ada di Keuangan, bukan hanya di profil pembeli: yang MEMUTUSKAN
 * dan yang MEMBAYAR bekerja dari sisi uang, bukan dari sisi satu pembeli. Tanpa daftar ini,
 * Manajer Keuangan harus menghafal pembeli mana yang mengajukan pembatalan — dan utang
 * refund yang belum dibayar tidak punya tempat untuk terlihat.
 *
 * Kejujuran yang dipegang: nominal yang belum dibayar ditampilkan sebagai SISA (bukan 0),
 * dan setiap baris yang tertahan menyebut sebabnya (mis. menunggu unit terjual kembali).
 */
export default function CancellationsPanel() {
  const { can } = useAuth();
  const mayView = can("cancellation", "view");
  const [state, setState] = useState({ loading: true, error: "", reason: "" });
  const [rows, setRows] = useState([]);
  const [counts, setCounts] = useState({});

  const load = useCallback(async () => {
    setState({ loading: true, error: "", reason: "" });
    try {
      const res = await api.get("/cancellations", { params: { limit: 100 } });
      setRows(res.data.data || []);
      setCounts(res.data.counts || {});
      setState({ loading: false, error: "", reason: res.data.reason || "" });
    } catch (e) {
      setState({ loading: false, reason: "",
        error: e?.response?.data?.detail || "Gagal memuat daftar pembatalan." });
    }
  }, []);

  useEffect(() => { if (mayView) load(); }, [mayView, load]);

  const utang = useMemo(
    () => rows.reduce((a, r) => a + (r.refund_outstanding || 0), 0), [rows]);
  const tertahan = useMemo(
    () => rows.filter((r) => r.refund_hold
      && r.refund_hold.code === "menunggu_penjualan_ulang").length, [rows]);

  if (!mayView) {
    return (
      <div data-testid="cancellations-access-denied"
        className="rounded-lg border border-rose-200 bg-rose-50 p-4 text-sm text-rose-900">
        <p className="font-medium">AKSES DITOLAK</p>
        <p className="mt-1 text-xs">
          Daftar pembatalan & refund dibuka untuk Manajer Sales/Marketing, Keuangan, dan
          Manajer Proyek. Hubungi admin sistem bila Anda memang perlu membacanya.
        </p>
      </div>
    );
  }
  if (state.loading) return <LoadingCards count={3} />;
  if (state.error) return <ErrorState message={state.error} onRetry={load} />;

  return (
    <div data-testid={P56.financePanel} className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <MetricCard label="Menunggu keputusan" value={counts.diajukan || 0}
          hint="Diajukan Manajer Sales, diputus Manajer Keuangan" />
        <MetricCard label="Utang refund belum dibayar"
          value={<MoneyText value={utang} />}
          hint="Akun 2-1460 — kewajiban nyata kepada pembeli" />
        <MetricCard label="Tertahan menunggu penjualan ulang" value={tertahan}
          hint="Ketentuan SPR; bisa diabaikan Manajer Keuangan dengan alasan" />
      </div>

      {state.reason ? (
        <p className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-xs text-slate-700">
          {state.reason}
        </p>
      ) : null}

      {rows.length ? (
        <div className="overflow-x-auto rounded-lg border bg-card">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Nomor</TableHead>
                <TableHead>Pembeli / unit</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Diterima</TableHead>
                <TableHead className="text-right">Potongan</TableHead>
                <TableHead className="text-right">Sisa refund</TableHead>
                <TableHead>Keadaan</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map((r) => {
                const st = r.settlement || r.basis_at_request || {};
                return (
                  <TableRow key={r.id} data-testid={P56.financeRow} data-state={r.state}>
                    <TableCell className="font-mono text-xs">
                      {r.number}
                      <p className="mt-0.5 text-[11px] text-muted-foreground">
                        {formatDateTimeWIB(r.requested_at)}
                      </p>
                    </TableCell>
                    <TableCell className="text-sm">
                      {r.customer_id ? (
                        <Link className="text-primary hover:underline"
                          to={`/customers/${r.customer_id}?tab=kontrak53`}>
                          {r.customer_name}
                        </Link>
                      ) : r.customer_name}
                      <p className="text-[11px] text-muted-foreground">
                        unit {r.unit_code} · {r.contract_number}
                      </p>
                    </TableCell>
                    <TableCell><StatusPill status={r.state} group="cancel_state" /></TableCell>
                    <TableCell className="text-right">
                      <MoneyText value={st.received_total} />
                    </TableCell>
                    <TableCell className="text-right">
                      <MoneyText value={st.cut_amount} />
                      <p className="text-[11px] text-muted-foreground">{st.cut_pct}%</p>
                    </TableCell>
                    <TableCell className="text-right">
                      <MoneyText value={r.refund_outstanding} />
                    </TableCell>
                    <TableCell className="max-w-[18rem] text-xs text-muted-foreground">
                      {r.refund_hold ? r.refund_hold.detail
                        : (r.can_pay_refund ? "Siap dibayar Keuangan." : "—")}
                    </TableCell>
                    <TableCell className="text-right">
                      {r.customer_id ? (
                        <Button size="sm" variant="outline" asChild>
                          <Link to={`/customers/${r.customer_id}?tab=kontrak53`}>
                            <Banknote className="mr-1.5 h-3.5 w-3.5" /> Buka
                          </Link>
                        </Button>
                      ) : null}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </div>
      ) : (
        <EmptyState icon={Ban} title="Belum ada pembatalan"
          description={state.reason
            || "Pembatalan diajukan dari profil pembeli (tab Kontrak & Legal) oleh Manajer "
               + "Sales, lalu diputus Manajer Keuangan di sini."} />
      )}
    </div>
  );
}
