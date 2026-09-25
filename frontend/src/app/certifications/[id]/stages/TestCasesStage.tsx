"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import type { Certification, TestCase, LintIssue, TraceabilityRow } from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { Alert } from "@/components/ui/Alert";
import { TaskPoller } from "@/components/TaskPoller";
import { CheckCircle, AlertTriangle } from "lucide-react";

interface Props { cert: Certification; }

export function TestCasesStage({ cert }: Props) {
  const qc = useQueryClient();
  const [generateTaskId, setGenerateTaskId] = useState<string | null>(null);
  const [lintResults, setLintResults] = useState<Record<string, LintIssue[]>>({});

  const { data: cases, isLoading } = useQuery<TestCase[]>({
    queryKey: ["testcases", cert.id],
    queryFn: () => api.get<TestCase[]>(`/certifications/${cert.id}/testcases`),
  });

  const { data: traceability } = useQuery<TraceabilityRow[]>({
    queryKey: ["traceability", cert.id],
    queryFn: () => api.get<TraceabilityRow[]>(`/certifications/${cert.id}/traceability`),
    enabled: !!cases && cases.length > 0,
  });

  const generate = useMutation({
    mutationFn: () => api.post<{ task_id: string }>(`/certifications/${cert.id}/testcases/generate`),
    onSuccess: (r) => setGenerateTaskId(r.task_id),
  });

  const lintCase = useMutation({
    mutationFn: (tcId: string) =>
      api.post<LintIssue[]>(`/testcases/${tcId}/lint?cert_id=${cert.id}`),
    onSuccess: (issues, tcId) => setLintResults((p) => ({ ...p, [tcId]: issues })),
  });

  const approve = useMutation({
    mutationFn: (tcId: string) =>
      api.post<TestCase>(`/testcases/${tcId}/approve?cert_id=${cert.id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["testcases", cert.id] }),
  });

  if (isLoading) return <div className="flex justify-center py-8"><Spinner /></div>;

  const uncoveredCriteria = traceability?.filter((r) => r.case_codes.length === 0) ?? [];

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button
          onClick={() => generate.mutate()}
          loading={generate.isPending}
          variant="secondary"
        >
          Generar casos con IA
        </Button>
        {generateTaskId && (
          <TaskPoller
            taskId={generateTaskId}
            label="Generando casos de prueba..."
            onSuccess={() => {
              setGenerateTaskId(null);
              qc.invalidateQueries({ queryKey: ["testcases", cert.id] });
            }}
          />
        )}
      </div>

      {uncoveredCriteria.length > 0 && (
        <Alert variant="warning">
          {uncoveredCriteria.length} criterio(s) sin caso de prueba:{" "}
          {uncoveredCriteria.map((r) => r.criterion_code).join(", ")}
        </Alert>
      )}

      {cases && cases.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          No hay casos de prueba aún. Generar con IA o importar manualmente.
        </div>
      )}

      {cases && cases.length > 0 && (
        <div className="space-y-3">
          {cases.map((tc) => {
            const issues = lintResults[tc.id] ?? [];
            const hasErrors = issues.some((i) => i.severity === "error");
            return (
              <div key={tc.id} className="bg-white border border-gray-200 rounded-lg p-4">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="font-mono text-xs text-gray-500">{tc.code}</span>
                      <Badge color={tc.status === "approved" ? "green" : "gray"}>
                        {tc.status === "approved" ? "Aprobado" : "Borrador"}
                      </Badge>
                      {tc.boundary && (
                        <Badge color="blue">{tc.boundary}</Badge>
                      )}
                    </div>
                    <p className="text-sm text-gray-800">{tc.name}</p>
                  </div>
                  <div className="flex gap-2 shrink-0">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => lintCase.mutate(tc.id)}
                      loading={lintCase.isPending}
                    >
                      Lintear
                    </Button>
                    {tc.status !== "approved" && !hasErrors && (
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => approve.mutate(tc.id)}
                        loading={approve.isPending}
                      >
                        Aprobar
                      </Button>
                    )}
                  </div>
                </div>

                {issues.length > 0 && (
                  <div className="mt-3 space-y-1">
                    {issues.map((issue) => (
                      <div
                        key={issue.code}
                        className={`flex gap-2 text-xs p-2 rounded ${
                          issue.severity === "error" ? "bg-red-50 text-red-700" : "bg-yellow-50 text-yellow-700"
                        }`}
                      >
                        {issue.severity === "error"
                          ? <AlertTriangle size={12} className="shrink-0 mt-0.5" />
                          : <AlertTriangle size={12} className="shrink-0 mt-0.5" />
                        }
                        <span><strong>{issue.code}</strong> — {issue.message}</span>
                      </div>
                    ))}
                  </div>
                )}

                {issues.length > 0 && !hasErrors && (
                  <div className="mt-2 flex gap-1 text-xs text-green-600 items-center">
                    <CheckCircle size={12} />
                    <span>Sin errores — listo para aprobar</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {traceability && traceability.length > 0 && (
        <div className="mt-6">
          <h4 className="text-sm font-medium text-gray-700 mb-3">Matriz de trazabilidad</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead>
                <tr className="bg-gray-50">
                  <th className="border border-gray-200 px-3 py-2 text-left">Criterio</th>
                  <th className="border border-gray-200 px-3 py-2 text-left">Casos</th>
                </tr>
              </thead>
              <tbody>
                {traceability.map((row) => (
                  <tr key={row.criterion_id} className={row.case_codes.length === 0 ? "bg-red-50" : ""}>
                    <td className="border border-gray-200 px-3 py-2">
                      <span className="font-mono text-blue-600">{row.criterion_code}</span>
                      <span className="ml-2 text-gray-600">{row.criterion_text}</span>
                    </td>
                    <td className="border border-gray-200 px-3 py-2">
                      {row.case_codes.length > 0
                        ? row.case_codes.join(", ")
                        : <span className="text-red-500">Sin caso</span>
                      }
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
