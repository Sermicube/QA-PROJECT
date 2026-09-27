"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, uploadFile } from "@/lib/api/client";
import type { Certification, ContextSource, Criterion } from "@/lib/api/types";
import { Tabs } from "@/components/ui/Tabs";
import { Textarea } from "@/components/ui/Textarea";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { TaskPoller } from "@/components/TaskPoller";
import { FileText, Trash2, Upload, Zap } from "lucide-react";

interface Props {
  cert: Certification;
  onNavigate?: (stage: string) => void;
}

export function ContextStage({ cert, onNavigate }: Props) {
  const qc = useQueryClient();
  const isBug = cert.type === "bug";

  const [analyzeTaskId, setAnalyzeTaskId] = useState<string | null>(null);
  const [generateTaskId, setGenerateTaskId] = useState<string | null>(null);
  const [quickFlowStep, setQuickFlowStep] = useState<"idle" | "analyzing" | "generating" | "done">("idle");

  const [bugForm, setBugForm] = useState({ bug_behavior: "", what_to_test: "", expected_result: "", fix: "" });
  const [brechaForm, setBrechaForm] = useState({ what_changes: "", what_to_test: "", expected_result: "" });
  const [incidentText, setIncidentText] = useState("");
  const [saveMsg, setSaveMsg] = useState("");

  const { data: sources } = useQuery<ContextSource[]>({
    queryKey: ["context", cert.id],
    queryFn: () =>
      api.get<{ sources: ContextSource[] }>(`/certifications/${cert.id}/context`).then((r) => r.sources ?? []),
  });

  const { data: criteria } = useQuery<Criterion[]>({
    queryKey: ["criteria", cert.id],
    queryFn: () => api.get<Criterion[]>(`/certifications/${cert.id}/criteria`),
    enabled: !!analyzeTaskId || quickFlowStep === "done",
  });

  const docSource = sources?.find((s) => s.kind === "requirement_document");
  const incidentSource = sources?.find((s) => s.kind === "incident_report");

  const saveDesc = useMutation({
    mutationFn: () =>
      api.put(`/certifications/${cert.id}/context/description`, {
        kind: isBug ? "bug" : "brecha",
        content: isBug ? bugForm : brechaForm,
      }),
    onSuccess: () => {
      setSaveMsg("Descripción guardada");
      qc.invalidateQueries({ queryKey: ["context", cert.id] });
    },
  });

  const saveIncident = useMutation({
    mutationFn: () =>
      api.put(`/certifications/${cert.id}/context/incident-report`, { text: incidentText }),
    onSuccess: () => {
      setSaveMsg("Reporte guardado");
      qc.invalidateQueries({ queryKey: ["context", cert.id] });
    },
  });

  const deleteSource = useMutation({
    mutationFn: (srcId: string) => api.delete(`/context-sources/${srcId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["context", cert.id] }),
  });

  const analyze = useMutation({
    mutationFn: () => api.post<{ task_id: string }>(`/certifications/${cert.id}/context/analyze`),
    onSuccess: (r) => setAnalyzeTaskId(r.task_id),
  });

  const generateCases = useMutation({
    mutationFn: () => api.post<{ task_id: string }>(`/certifications/${cert.id}/testcases/generate`),
    onSuccess: (r) => setGenerateTaskId(r.task_id),
  });

  // Flujo rápido: guardar reporte → analizar → generar casos → ir a etapa casos
  const runQuickFlow = async () => {
    if (!incidentText.trim()) return;
    setQuickFlowStep("analyzing");
    await saveIncident.mutateAsync();
    const { task_id } = await api.post<{ task_id: string }>(`/certifications/${cert.id}/context/analyze`);
    setAnalyzeTaskId(task_id);
  };

  const uploadDoc = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    await uploadFile(`/certifications/${cert.id}/context/document`, fd);
    qc.invalidateQueries({ queryKey: ["context", cert.id] });
  };

  const bugFields = [
    { key: "bug_behavior" as const, label: "¿Qué ocurría? (comportamiento reportado por el usuario)" },
    { key: "what_to_test" as const, label: "¿Qué se va a probar?" },
    { key: "expected_result" as const, label: "Resultado esperado después de la corrección" },
    { key: "fix" as const, label: "Corrección aplicada (changeset / ajuste)" },
  ];

  const brechaFields = [
    { key: "what_changes" as const, label: "¿Qué cambia en el sistema?" },
    { key: "what_to_test" as const, label: "¿Qué se va a probar?" },
    { key: "expected_result" as const, label: "Resultado esperado" },
  ];

  const incidentTab = {
    key: "incident",
    label: isBug ? "Reporte Aranda" : "Reporte del incidente",
    content: (
      <div className="space-y-4">
        {isBug && (
          <div className="rounded-md bg-blue-50 border border-blue-200 px-4 py-3 text-sm text-blue-700">
            <p className="font-medium mb-1">Flujo rápido desde Aranda</p>
            <p className="text-blue-600">
              Pega el texto del caso tal como lo envió el usuario. El sistema extrae los criterios
              de prueba y genera los casos automáticamente.
            </p>
          </div>
        )}

        <Textarea
          label={isBug ? "Descripción del caso Aranda (tal como la envió el usuario)" : "Texto del incidente o diagnóstico del desarrollador"}
          value={incidentSource?.content?.text as string ?? incidentText}
          onChange={(e) => setIncidentText(e.target.value)}
          rows={10}
          placeholder={
            isBug
              ? "Ej: «Al intentar excluir al beneficiario con cédula X del contrato Y, el sistema muestra el mensaje 'Error al procesar la solicitud'...»"
              : "Pegar aquí el reporte del incidente..."
          }
        />

        {quickFlowStep === "idle" && (
          <div className="flex flex-wrap gap-3">
            {isBug && (
              <Button
                onClick={runQuickFlow}
                loading={quickFlowStep !== "idle"}
                disabled={!incidentText.trim()}
                variant="primary"
                size="sm"
              >
                <Zap size={14} className="mr-1.5" />
                Analizar y generar casos
              </Button>
            )}
            <Button
              onClick={() => saveIncident.mutate()}
              loading={saveIncident.isPending}
              variant="secondary"
              size="sm"
            >
              Solo guardar
            </Button>
          </div>
        )}

        {(quickFlowStep === "analyzing" || analyzeTaskId) && (
          <TaskPoller
            taskId={analyzeTaskId!}
            label={quickFlowStep !== "idle" ? "Extrayendo criterios del reporte..." : "Analizando contexto..."}
            onSuccess={() => {
              setAnalyzeTaskId(null);
              qc.invalidateQueries({ queryKey: ["criteria", cert.id] });
              if (quickFlowStep === "analyzing") {
                setQuickFlowStep("generating");
                generateCases.mutate();
              }
            }}
          />
        )}

        {quickFlowStep === "generating" && generateTaskId && (
          <TaskPoller
            taskId={generateTaskId}
            label="Generando casos de prueba..."
            onSuccess={() => {
              setGenerateTaskId(null);
              setQuickFlowStep("done");
              qc.invalidateQueries({ queryKey: ["testcases", cert.id] });
            }}
          />
        )}

        {quickFlowStep === "done" && (
          <Alert variant="info">
            Casos generados.{" "}
            <button
              className="underline font-medium"
              onClick={() => onNavigate?.("testcases")}
            >
              Ver casos de prueba →
            </button>
          </Alert>
        )}

        {saveMsg && quickFlowStep === "idle" && (
          <p className="text-sm text-green-600">{saveMsg}</p>
        )}
      </div>
    ),
  };

  const descriptionTab = {
    key: "description",
    label: "Descripción del analista",
    content: (
      <div className="space-y-4">
        {isBug
          ? bugFields.map(({ key, label }) => (
              <Textarea
                key={key}
                label={label}
                value={bugForm[key]}
                onChange={(e) => setBugForm((p) => ({ ...p, [key]: e.target.value }))}
                rows={3}
              />
            ))
          : brechaFields.map(({ key, label }) => (
              <Textarea
                key={key}
                label={label}
                value={brechaForm[key]}
                onChange={(e) => setBrechaForm((p) => ({ ...p, [key]: e.target.value }))}
                rows={3}
              />
            ))}
        {saveMsg && <p className="text-sm text-green-600">{saveMsg}</p>}
        <Button onClick={() => saveDesc.mutate()} loading={saveDesc.isPending} size="sm">
          Guardar descripción
        </Button>
      </div>
    ),
  };

  const documentTab = {
    key: "document",
    label: "Documento de requerimiento",
    content: (
      <div className="space-y-4">
        {docSource ? (
          <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-md border">
            <FileText size={20} className="text-blue-500" />
            <span className="text-sm flex-1">{docSource.file_name}</span>
            <Button variant="ghost" size="sm" onClick={() => deleteSource.mutate(docSource.id)}>
              <Trash2 size={16} />
            </Button>
          </div>
        ) : (
          <label className="flex flex-col items-center justify-center border-2 border-dashed border-gray-300 rounded-lg p-8 cursor-pointer hover:border-blue-400 transition-colors">
            <Upload size={24} className="text-gray-400 mb-2" />
            <span className="text-sm text-gray-500">Subir .docx o .pdf</span>
            <input type="file" accept=".docx,.pdf" className="hidden" onChange={uploadDoc} />
          </label>
        )}
      </div>
    ),
  };

  // Para bugs: Aranda primero. Para brechas: descripción primero.
  const tabs = isBug
    ? [incidentTab, descriptionTab, documentTab]
    : [descriptionTab, documentTab, incidentTab];

  return (
    <div className="space-y-6">
      <Tabs tabs={tabs} />

      {/* Análisis manual (cuando no se usó el flujo rápido) */}
      {quickFlowStep === "idle" && (
        <div className="border-t pt-4">
          <div className="flex items-center gap-4">
            <Button
              onClick={() => analyze.mutate()}
              loading={analyze.isPending}
              variant="secondary"
            >
              Analizar contexto
            </Button>
            {analyzeTaskId && (
              <TaskPoller
                taskId={analyzeTaskId}
                label="Extrayendo criterios y detectando ambigüedades..."
                onSuccess={() => {
                  setAnalyzeTaskId(null);
                  qc.invalidateQueries({ queryKey: ["criteria", cert.id] });
                }}
              />
            )}
          </div>

          {criteria && criteria.length > 0 && (
            <div className="mt-4">
              <h4 className="text-sm font-medium text-gray-700 mb-2">
                Criterios extraídos ({criteria.length})
              </h4>
              <div className="space-y-2">
                {criteria.map((c) => (
                  <div key={c.id} className="flex gap-2 text-sm p-2 bg-blue-50 rounded">
                    <span className="font-mono text-blue-600 shrink-0">{c.code}</span>
                    <span className="text-gray-700">{c.text}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
