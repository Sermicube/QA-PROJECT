"use client";
import { useState, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, uploadFile } from "@/lib/api/client";
import type { Certification, Evidence, Execution } from "@/lib/api/types";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { Badge } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";
import { Select } from "@/components/ui/Select";
import { Upload, CheckCircle, XCircle, AlertTriangle } from "lucide-react";

interface Props { cert: Certification; }

const resultOptions = [
  { value: "pass", label: "Pasa" },
  { value: "fail", label: "Falla" },
  { value: "blocked", label: "Bloqueado" },
  { value: "not_run", label: "No ejecutado" },
];

export function ExecutionStage({ cert }: Props) {
  const qc = useQueryClient();
  const [uploading, setUploading] = useState<Record<string, boolean>>({});
  const fileRefs = useRef<Record<string, HTMLInputElement | null>>({});

  const { data: executions, isLoading } = useQuery<Execution[]>({
    queryKey: ["executions", cert.id],
    queryFn: () => api.get<Execution[]>(`/certifications/${cert.id}/executions`),
  });

  const { data: evidences } = useQuery<Evidence[]>({
    queryKey: ["evidences", cert.id],
    queryFn: () => api.get<Evidence[]>(`/certifications/${cert.id}/evidences`),
  });

  const updateExecution = useMutation({
    mutationFn: ({ execId, result }: { execId: string; result: string }) =>
      api.patch<Execution>(`/executions/${execId}`, { result }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["executions", cert.id] }),
  });

  const uploadScreenshot = async (execId: string, file: File) => {
    setUploading((p) => ({ ...p, [execId]: true }));
    try {
      const fd = new FormData();
      fd.append("file", file);
      fd.append("execution_id", execId);
      await uploadFile(`/certifications/${cert.id}/evidences`, fd);
      qc.invalidateQueries({ queryKey: ["evidences", cert.id] });
    } finally {
      setUploading((p) => ({ ...p, [execId]: false }));
    }
  };

  if (isLoading) return <div className="flex justify-center py-8"><Spinner /></div>;

  const getEvidencesForExec = (execId: string) =>
    evidences?.filter((e) => e.execution_id === execId) ?? [];

  return (
    <div className="space-y-4">
      <p className="text-sm text-gray-600">
        Registrar el resultado de cada caso y adjuntar los pantallazos de evidencia (deben mostrar la hora del sistema y la URL).
      </p>

      {executions && executions.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          No hay ejecuciones. Las ejecuciones se crean automáticamente al aprobar los casos de prueba.
        </div>
      )}

      {executions && executions.map((exec) => {
        const execs_evidences = getEvidencesForExec(exec.id);
        const allOk = execs_evidences.every((e) => e.validation_status === "ok");
        const hasWarnings = execs_evidences.some((e) => e.validation_status === "warning");

        return (
          <div key={exec.id} className="bg-white border border-gray-200 rounded-lg p-4">
            <div className="flex items-start justify-between gap-3 mb-3">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <span className="font-mono text-xs text-gray-500">{exec.test_case_code}</span>
                  <Badge
                    color={
                      exec.result === "pass" ? "green" :
                      exec.result === "fail" ? "red" :
                      exec.result === "blocked" ? "orange" : "gray"
                    }
                  >
                    {resultOptions.find((o) => o.value === exec.result)?.label ?? exec.result}
                  </Badge>
                </div>
                <p className="text-sm text-gray-800">{exec.test_case_name}</p>
              </div>
              <Select
                value={exec.result}
                onChange={(e) => updateExecution.mutate({ execId: exec.id, result: e.target.value })}
                className="w-36"
              >
                {resultOptions.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </Select>
            </div>

            {/* Evidence section */}
            <div className="border-t border-gray-100 pt-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-gray-600">Evidencias ({execs_evidences.length})</span>
                <label className="cursor-pointer">
                  <span className="text-xs text-blue-600 flex items-center gap-1 hover:underline">
                    {uploading[exec.id] ? <Spinner size="sm" /> : <Upload size={12} />}
                    Adjuntar pantallazo
                  </span>
                  <input
                    ref={(el) => { fileRefs.current[exec.id] = el; }}
                    type="file"
                    accept="image/*,.png,.jpg,.jpeg"
                    className="hidden"
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) uploadScreenshot(exec.id, file);
                    }}
                  />
                </label>
              </div>

              {execs_evidences.length === 0 && (
                <p className="text-xs text-gray-400 italic">Sin evidencias adjuntas</p>
              )}

              <div className="space-y-2">
                {execs_evidences.map((ev) => (
                  <div key={ev.id} className="flex items-center gap-2 text-xs p-2 bg-gray-50 rounded">
                    {ev.validation_status === "ok" && <CheckCircle size={12} className="text-green-500 shrink-0" />}
                    {ev.validation_status === "warning" && <AlertTriangle size={12} className="text-yellow-500 shrink-0" />}
                    {ev.validation_status === "error" && <XCircle size={12} className="text-red-500 shrink-0" />}
                    <span className="flex-1 truncate text-gray-700">{ev.file_name}</span>
                    <Badge
                      color={
                        ev.validation_status === "ok" ? "green" :
                        ev.validation_status === "warning" ? "yellow" : "red"
                      }
                    >
                      {ev.validation_status}
                    </Badge>
                  </div>
                ))}
              </div>

              {hasWarnings && (
                <Alert variant="warning" className="mt-2 text-xs">
                  Algunos pantallazos no pudieron validarse por OCR (sin Tesseract). Se aceptarán en modo manual.
                </Alert>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
