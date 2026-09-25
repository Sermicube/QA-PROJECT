"use client";
import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/hooks/useAuth";
import { Spinner } from "@/components/ui/Spinner";
import { ArrowLeft } from "lucide-react";

interface MetricsSummary {
  total_certifications: number;
  avg_time_minutes: number;
  avg_time_finding_data_minutes: number;
  avg_cases_per_cert: number;
  pct_cases_auto_assigned: number;
  avg_ambiguities_detected: number;
  avg_lint_issues_per_cert: number;
  avg_evidences_rejected_ocr: number;
  recent: RecentCert[];
}

interface RecentCert {
  id: string;
  title: string;
  external_code: string;
  closed_at: string;
  total_minutes: number;
  cases: number;
  ambiguities: number;
  auto_assigned_pct: number;
}

export default function MetricsPage() {
  const router = useRouter();
  const { user, isLoading: authLoading } = useAuth();

  useEffect(() => {
    if (!authLoading && !user) router.push("/login");
  }, [user, authLoading, router]);

  const { data: metrics, isLoading } = useQuery<MetricsSummary>({
    queryKey: ["metrics-summary"],
    queryFn: () => api.get<MetricsSummary>("/metrics/summary"),
    enabled: !!user,
  });

  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  const stat = (label: string, value: string | number, sub?: string) => (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="text-2xl font-semibold text-gray-900 mt-1">{value}</p>
      {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center gap-3">
          <Link href="/" className="text-gray-400 hover:text-gray-600">
            <ArrowLeft size={18} />
          </Link>
          <h1 className="text-lg font-semibold text-gray-900">Métricas</h1>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        {!metrics ? (
          <div className="text-center py-12 text-gray-500">Sin métricas disponibles aún.</div>
        ) : (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
              {stat("Certificaciones totales", metrics.total_certifications)}
              {stat("Tiempo promedio", `${metrics.avg_time_minutes.toFixed(0)} min`, "por certificación")}
              {stat("Tiempo buscando datos", `${metrics.avg_time_finding_data_minutes.toFixed(0)} min`, "promedio")}
              {stat("Asignación automática", `${(metrics.pct_cases_auto_assigned * 100).toFixed(0)}%`, "de casos")}
              {stat("Ambigüedades detectadas", metrics.avg_ambiguities_detected.toFixed(1), "promedio por cert.")}
              {stat("Casos promedio", metrics.avg_cases_per_cert.toFixed(1), "por certificación")}
              {stat("Issues de lint", metrics.avg_lint_issues_per_cert.toFixed(1), "promedio por cert.")}
              {stat("Evidencias rechazadas OCR", metrics.avg_evidences_rejected_ocr.toFixed(1), "promedio por cert.")}
            </div>

            {metrics.recent.length > 0 && (
              <>
                <h3 className="text-sm font-semibold text-gray-700 mb-3">Certificaciones recientes</h3>
                <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-gray-50 text-xs text-gray-500 uppercase">
                        <th className="px-4 py-3 text-left font-medium">Código</th>
                        <th className="px-4 py-3 text-left font-medium">Título</th>
                        <th className="px-4 py-3 text-right font-medium">Tiempo</th>
                        <th className="px-4 py-3 text-right font-medium">Casos</th>
                        <th className="px-4 py-3 text-right font-medium">Ambigüedades</th>
                        <th className="px-4 py-3 text-right font-medium">Auto</th>
                      </tr>
                    </thead>
                    <tbody>
                      {metrics.recent.map((c) => (
                        <tr key={c.id} className="border-t border-gray-100 hover:bg-gray-50">
                          <td className="px-4 py-3 font-mono text-xs text-gray-500">{c.external_code}</td>
                          <td className="px-4 py-3">
                            <Link href={`/certifications/${c.id}`} className="text-blue-600 hover:underline">
                              {c.title}
                            </Link>
                          </td>
                          <td className="px-4 py-3 text-right text-gray-600">{c.total_minutes} min</td>
                          <td className="px-4 py-3 text-right text-gray-600">{c.cases}</td>
                          <td className="px-4 py-3 text-right text-gray-600">{c.ambiguities}</td>
                          <td className="px-4 py-3 text-right text-gray-600">{(c.auto_assigned_pct * 100).toFixed(0)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </>
        )}
      </main>
    </div>
  );
}
