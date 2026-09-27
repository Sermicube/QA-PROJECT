"use client";
import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, downloadFile } from "@/lib/api/client";
import { useAuth } from "@/lib/hooks/useAuth";
import { Spinner } from "@/components/ui/Spinner";
import { Button } from "@/components/ui/Button";
import { ArrowLeft, Download } from "lucide-react";

interface MetricsSummaryOut {
  by_module: ModuleMetrics[];
  total_certifications: number;
  total_rework: number;
  overall_avg_minutes: number | null;
  baseline_avg_minutes: number | null;
}

interface ModuleMetrics {
  type: string;
  module: string;
  avg_duration_minutes: number | null;
  baseline_avg_minutes: number | null;
  total_certifications: number;
  total_rework: number;
}

interface TypeMetrics {
  type: string;
  total: number;
  avg_minutes: number | null;
  total_rework: number;
}

interface ModuleMetricsOut {
  module: string;
  total: number;
  avg_minutes: number | null;
  total_rework: number;
}

interface BaselineItem {
  module: string;
  with_tool_avg: number | null;
  baseline_avg: number | null;
  delta_pct: number | null;
}

const fmt = (n: number | null | undefined, decimals = 1) =>
  n != null ? n.toFixed(decimals) : "—";

const deltaColor = (pct: number | null) => {
  if (pct == null) return "text-gray-500";
  if (pct < -5) return "text-green-600 font-medium";
  if (pct > 5) return "text-red-600 font-medium";
  return "text-yellow-600 font-medium";
};

const deltaLabel = (pct: number | null) => {
  if (pct == null) return "—";
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}%`;
};

type Tab = "resumen" | "por-tipo-modulo" | "vs-linea-base";

export default function MetricsPage() {
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuth();
  const [tab, setTab] = useState<Tab>("resumen");

  useEffect(() => {
    if (!authLoading && !user) router.push("/login");
  }, [user, authLoading, router]);

  const { data: summary, isLoading: summaryLoading } = useQuery<MetricsSummaryOut>({
    queryKey: ["metrics-summary"],
    queryFn: () => api.get<MetricsSummaryOut>("/metrics/summary"),
    enabled: !!user,
  });

  const { data: byType, isLoading: byTypeLoading } = useQuery<{ items: TypeMetrics[] }>({
    queryKey: ["metrics-by-type"],
    queryFn: () => api.get<{ items: TypeMetrics[] }>("/metrics/by-type"),
    enabled: !!user && tab === "por-tipo-modulo",
  });

  const { data: byModule, isLoading: byModuleLoading } = useQuery<{ items: ModuleMetricsOut[] }>({
    queryKey: ["metrics-by-module"],
    queryFn: () => api.get<{ items: ModuleMetricsOut[] }>("/metrics/by-module"),
    enabled: !!user && tab === "por-tipo-modulo",
  });

  const { data: baseline, isLoading: baselineLoading } = useQuery<{ items: BaselineItem[] }>({
    queryKey: ["metrics-baseline"],
    queryFn: () => api.get<{ items: BaselineItem[] }>("/metrics/baseline-comparison"),
    enabled: !!user && tab === "vs-linea-base",
  });

  if (authLoading) return <div className="min-h-screen flex items-center justify-center"><Spinner size="lg" /></div>;

  const stat = (label: string, value: string | number, sub?: string) => (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-2xl font-semibold text-gray-900 mt-1">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );

  const tabs: { key: Tab; label: string }[] = [
    { key: "resumen", label: "Resumen" },
    { key: "por-tipo-modulo", label: "Por tipo / módulo" },
    { key: "vs-linea-base", label: "Vs línea base" },
  ];

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center gap-3">
          <Link href="/" className="text-gray-400 hover:text-gray-600"><ArrowLeft size={18} /></Link>
          <h1 className="text-lg font-semibold text-gray-900 flex-1">Métricas</h1>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => downloadFile("/metrics/export/excel", "metricas.xlsx")}
          >
            <Download size={14} />
            Exportar Excel
          </Button>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-6">
        {/* Tabs */}
        <div className="flex gap-1 border-b border-gray-200 mb-6">
          {tabs.map((t) => (
            <button
              key={t.key}
              onClick={() => setTab(t.key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                tab === t.key
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        {/* ── Resumen ── */}
        {tab === "resumen" && (
          <>
            {summaryLoading ? (
              <div className="flex justify-center py-16"><Spinner size="lg" /></div>
            ) : !summary ? (
              <p className="text-center py-12 text-gray-500">Sin métricas disponibles aún.</p>
            ) : (
              <>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
                  {stat("Certificaciones", summary.total_certifications)}
                  {stat("Tiempo promedio", `${fmt(summary.overall_avg_minutes, 0)} min`, "por certificación")}
                  {stat("Línea base", summary.baseline_avg_minutes != null ? `${fmt(summary.baseline_avg_minutes, 0)} min` : "—", "promedio sin herramienta")}
                  {stat("Devoluciones totales", summary.total_rework)}
                </div>

                {summary.by_module.length > 0 && (
                  <>
                    <h3 className="text-sm font-semibold text-gray-700 mb-3">Por tipo y módulo</h3>
                    <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                      <table className="w-full text-sm">
                        <thead>
                          <tr className="bg-gray-50 text-xs text-gray-500 uppercase">
                            <th className="px-4 py-3 text-left font-medium">Tipo</th>
                            <th className="px-4 py-3 text-left font-medium">Módulo</th>
                            <th className="px-4 py-3 text-right font-medium">Certs.</th>
                            <th className="px-4 py-3 text-right font-medium">Promedio</th>
                            <th className="px-4 py-3 text-right font-medium">Baseline</th>
                            <th className="px-4 py-3 text-right font-medium">Devoluciones</th>
                          </tr>
                        </thead>
                        <tbody>
                          {summary.by_module.map((m, i) => (
                            <tr key={i} className="border-t border-gray-100">
                              <td className="px-4 py-3 text-gray-600">{m.type}</td>
                              <td className="px-4 py-3 font-medium text-gray-800">{m.module}</td>
                              <td className="px-4 py-3 text-right text-gray-600">{m.total_certifications}</td>
                              <td className="px-4 py-3 text-right text-gray-600">{fmt(m.avg_duration_minutes, 0)} min</td>
                              <td className="px-4 py-3 text-right text-gray-400">{fmt(m.baseline_avg_minutes, 0)}</td>
                              <td className="px-4 py-3 text-right text-gray-600">{m.total_rework}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </>
                )}
              </>
            )}
          </>
        )}

        {/* ── Por tipo / módulo ── */}
        {tab === "por-tipo-modulo" && (
          <div className="space-y-6">
            {byTypeLoading || byModuleLoading ? (
              <div className="flex justify-center py-16"><Spinner size="lg" /></div>
            ) : (
              <div className="grid md:grid-cols-2 gap-6">
                {/* Por tipo */}
                <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                  <h3 className="text-sm font-semibold text-gray-800 px-4 py-3 border-b border-gray-100">Por tipo</h3>
                  {!byType || byType.items.length === 0 ? (
                    <p className="px-4 py-6 text-sm text-gray-400">Sin datos</p>
                  ) : (
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-xs text-gray-500 uppercase bg-gray-50">
                          <th className="px-4 py-2 text-left font-medium">Tipo</th>
                          <th className="px-4 py-2 text-right font-medium">Total</th>
                          <th className="px-4 py-2 text-right font-medium">Promedio</th>
                          <th className="px-4 py-2 text-right font-medium">Retrabajo</th>
                        </tr>
                      </thead>
                      <tbody>
                        {byType.items.map((t) => (
                          <tr key={t.type} className="border-t border-gray-100">
                            <td className="px-4 py-3 font-medium">{t.type}</td>
                            <td className="px-4 py-3 text-right text-gray-600">{t.total}</td>
                            <td className="px-4 py-3 text-right text-gray-600">{fmt(t.avg_minutes, 0)} min</td>
                            <td className="px-4 py-3 text-right text-gray-600">{t.total_rework}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>

                {/* Por módulo (top 5) */}
                <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                  <h3 className="text-sm font-semibold text-gray-800 px-4 py-3 border-b border-gray-100">Por módulo (top 5 por tiempo)</h3>
                  {!byModule || byModule.items.length === 0 ? (
                    <p className="px-4 py-6 text-sm text-gray-400">Sin datos</p>
                  ) : (
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-xs text-gray-500 uppercase bg-gray-50">
                          <th className="px-4 py-2 text-left font-medium">Módulo</th>
                          <th className="px-4 py-2 text-right font-medium">Total</th>
                          <th className="px-4 py-2 text-right font-medium">Promedio</th>
                        </tr>
                      </thead>
                      <tbody>
                        {byModule.items.slice(0, 5).map((m) => (
                          <tr key={m.module} className="border-t border-gray-100">
                            <td className="px-4 py-3 font-medium text-gray-800">{m.module}</td>
                            <td className="px-4 py-3 text-right text-gray-600">{m.total}</td>
                            <td className="px-4 py-3 text-right text-gray-600">{fmt(m.avg_minutes, 0)} min</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* ── Vs línea base ── */}
        {tab === "vs-linea-base" && (
          <>
            {baselineLoading ? (
              <div className="flex justify-center py-16"><Spinner size="lg" /></div>
            ) : !baseline || baseline.items.length === 0 ? (
              <div className="bg-white rounded-lg border border-gray-200 p-8 text-center text-gray-500">
                <p className="font-medium mb-1">Aún no hay datos de línea base registrados</p>
                <p className="text-sm text-gray-400">
                  Agrega certificaciones de referencia desde la sección de métricas para comparar el tiempo con y sin la herramienta.
                </p>
              </div>
            ) : (
              <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 text-xs text-gray-500 uppercase">
                      <th className="px-4 py-3 text-left font-medium">Módulo</th>
                      <th className="px-4 py-3 text-right font-medium">Con herramienta</th>
                      <th className="px-4 py-3 text-right font-medium">Sin herramienta</th>
                      <th className="px-4 py-3 text-right font-medium">Diferencia</th>
                    </tr>
                  </thead>
                  <tbody>
                    {baseline.items.map((b) => (
                      <tr key={b.module} className="border-t border-gray-100">
                        <td className="px-4 py-3 font-medium text-gray-800">{b.module}</td>
                        <td className="px-4 py-3 text-right text-gray-600">
                          {b.with_tool_avg != null ? `${fmt(b.with_tool_avg, 0)} min` : "—"}
                        </td>
                        <td className="px-4 py-3 text-right text-gray-500">
                          {b.baseline_avg != null ? `${fmt(b.baseline_avg, 0)} min` : "—"}
                        </td>
                        <td className={`px-4 py-3 text-right ${deltaColor(b.delta_pct)}`}>
                          {deltaLabel(b.delta_pct)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <p className="px-4 py-2 text-xs text-gray-400 border-t border-gray-100">
                  Verde = mejora · Rojo = más lento · Amarillo = sin diferencia significativa
                </p>
              </div>
            )}
          </>
        )}
      </main>
    </div>
  );
}
