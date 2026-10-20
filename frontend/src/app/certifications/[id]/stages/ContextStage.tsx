"use client";
import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, uploadFile } from "@/lib/api/client";
import type { Certification, ContextSource, Criterion, Ambiguity } from "@/lib/api/types";
import { Textarea } from "@/components/ui/Textarea";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { TaskPoller } from "@/components/TaskPoller";
import {
  FileText, Trash2, Upload, Sparkles,
  ChevronDown, ChevronRight, Copy, CheckCircle2,
} from "lucide-react";

interface Props {
  cert: Certification;
  onNavigate?: (stage: string) => void;
}

const BUG_LABELS: Record<string, string> = {
  bug_behavior: "¿Qué ocurría? (comportamiento reportado por el usuario)",
  what_to_test: "¿Qué se va a probar?",
  expected_result: "Resultado esperado después de la corrección",
  fix: "Corrección aplicada (changeset / ajuste, opcional)",
};

const BRECHA_LABELS: Record<string, string> = {
  what_changes: "¿Qué cambia en el sistema?",
  what_to_test: "¿Qué se va a probar?",
  expected_result: "Resultado esperado",
};

const AMB_GROUP_LABELS: Record<string, string> = {
  changes_cases: "Cambian los casos",
  execution_data: "Datos para ejecutar",
  other: "Otras",
};
const AMB_GROUP_ORDER = ["changes_cases", "execution_data", "other"] as const;
type AmbGroup = (typeof AMB_GROUP_ORDER)[number];

export function ContextStage({ cert, onNavigate }: Props) {
  const qc = useQueryClient();
  const isBug = cert.type === "bug";

  // Form state
  const [freeText, setFreeText] = useState("");
  const [incidentText, setIncidentText] = useState("");
  const [bugForm, setBugForm] = useState({ bug_behavior: "", what_to_test: "", expected_result: "", fix: "" });
  const [brechaForm, setBrechaForm] = useState({ what_changes: "", what_to_test: "", expected_result: "" });
  const [saveMsg, setSaveMsg] = useState("");
  const [proposeError, setProposeError] = useState<string | null>(null);

  // Analysis state
  const [analyzeTaskId, setAnalyzeTaskId] = useState<string | null>(null);
  const [analyzeCompleted, setAnalyzeCompleted] = useState(false);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);

  // UI state
  const [inputsCollapsed, setInputsCollapsed] = useState(false);
  const [expandedAmbs, setExpandedAmbs] = useState<Set<string>>(new Set());
  const [expandedGroups, setExpandedGroups] = useState<Record<AmbGroup, boolean>>({
    changes_cases: true,
    execution_data: false,
    other: false,
  });
  const [criteriaOpen, setCriteriaOpen] = useState(false);
  const [resolveTexts, setResolveTexts] = useState<Record<string, string>>({});
  const [resolvingId, setResolvingId] = useState<string | null>(null);
  const [copyMsg, setCopyMsg] = useState("");

  // ── Queries ──────────────────────────────────────────────────────────────────
  const { data: sources } = useQuery<ContextSource[]>({
    queryKey: ["context", cert.id],
    queryFn: () => api.get<ContextSource[]>(`/certifications/${cert.id}/context`),
  });
  const { data: criteria } = useQuery<Criterion[]>({
    queryKey: ["criteria", cert.id],
    queryFn: () => api.get<Criterion[]>(`/certifications/${cert.id}/criteria`),
  });
  const { data: ambiguities } = useQuery<Ambiguity[]>({
    queryKey: ["ambiguities", cert.id],
    queryFn: () => api.get<Ambiguity[]>(`/certifications/${cert.id}/ambiguities`),
  });

  // ── Hydrate forms ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!sources) return;
    const desc = sources.find((s) => s.kind === "analyst_description");
    const incident = sources.find((s) => s.kind === "incident_report");
    if (desc?.content) {
      const c = desc.content as Record<string, string>;
      setFreeText(c.free_text ?? "");
      if (isBug) {
        setBugForm({
          bug_behavior: c.bug_behavior ?? "",
          what_to_test: c.what_to_test ?? "",
          expected_result: c.expected_result ?? "",
          fix: c.fix ?? "",
        });
      } else {
        setBrechaForm({
          what_changes: c.what_changes ?? "",
          what_to_test: c.what_to_test ?? "",
          expected_result: c.expected_result ?? "",
        });
      }
    }
    if (incident?.extracted_text) setIncidentText(incident.extracted_text);
  }, [sources, isBug]);

  // Auto-collapse inputs when results exist from a previous session
  useEffect(() => {
    if ((criteria?.length ?? 0) > 0 || (ambiguities?.length ?? 0) > 0) {
      setInputsCollapsed(true);
    }
  }, [criteria, ambiguities]);

  // ── Derived ───────────────────────────────────────────────────────────────────
  const docSource = sources?.find((s) => s.kind === "requirement_document");
  const summarySource = sources?.find((s) => s.kind === "analysis_summary");
  const summaryContent = summarySource?.content as
    | { business_summary?: string; rules?: string[] }
    | null;

  const hasResults = (criteria?.length ?? 0) > 0 || (ambiguities?.length ?? 0) > 0;
  const showResultsPanel = hasResults || analyzeCompleted;
  const hasContext = !!sources && sources.length > 0;
  const hasEnoughToAnalyze = hasContext || freeText.trim().length > 10;
  const hasEnoughToPropose = freeText.trim().length >= 20;

  // Group ambiguities by category
  const ambsByGroup = (ambiguities ?? []).reduce<Record<AmbGroup, Ambiguity[]>>(
    (acc, a) => {
      const g = AMB_GROUP_ORDER.includes(a.category as AmbGroup)
        ? (a.category as AmbGroup)
        : "other";
      acc[g] = [...acc[g], a];
      return acc;
    },
    { changes_cases: [], execution_data: [], other: [] }
  );

  // ── Mutations ─────────────────────────────────────────────────────────────────
  const saveDesc = useMutation({
    mutationFn: () =>
      api.put(`/certifications/${cert.id}/context/description`, {
        cert_type: cert.type,
        content: isBug
          ? { ...bugForm, free_text: freeText }
          : { ...brechaForm, free_text: freeText },
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["context", cert.id] });
      setSaveMsg("Guardado");
      setTimeout(() => setSaveMsg(""), 2500);
    },
  });

  const saveIncident = useMutation({
    mutationFn: () =>
      api.put(`/certifications/${cert.id}/context/incident-report`, { text: incidentText }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["context", cert.id] }),
  });

  const deleteSource = useMutation({
    mutationFn: (srcId: string) => api.delete(`/context-sources/${srcId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["context", cert.id] }),
  });

  const analyze = useMutation({
    mutationFn: () =>
      api.post<{ task_id: string }>(`/certifications/${cert.id}/context/analyze`),
    onSuccess: (r) => {
      setAnalyzeError(null);
      setAnalyzeTaskId(r.task_id);
    },
    onError: (err: unknown) => {
      setAnalyzeError(
        err instanceof Error ? err.message : "Error al iniciar el análisis."
      );
    },
  });

  const propose = useMutation({
    mutationFn: () =>
      api.post<{ proposed: Record<string, string> }>(
        `/certifications/${cert.id}/context/propose-description`,
        { free_text: freeText, cert_type: cert.type }
      ),
    onSuccess: (r) => {
      setProposeError(null);
      const p = r.proposed;
      if (isBug) {
        setBugForm((prev) => ({
          bug_behavior: p.bug_behavior ?? prev.bug_behavior,
          what_to_test: p.what_to_test ?? prev.what_to_test,
          expected_result: p.expected_result ?? prev.expected_result,
          fix: p.fix ?? prev.fix,
        }));
      } else {
        setBrechaForm((prev) => ({
          what_changes: p.what_changes ?? prev.what_changes,
          what_to_test: p.what_to_test ?? prev.what_to_test,
          expected_result: p.expected_result ?? prev.expected_result,
        }));
      }
    },
    onError: () =>
      setProposeError("No se pudieron extraer los campos del texto. Intenta con más detalle."),
  });

  const resolveAmb = useMutation({
    mutationFn: ({ ambId, resolution }: { ambId: string; resolution: string }) =>
      api.patch<Ambiguity>(`/ambiguities/${ambId}?cert_id=${cert.id}`, {
        resolution,
        resolved_by: "analista",
      }),
    onSuccess: () => {
      setResolvingId(null);
      qc.invalidateQueries({ queryKey: ["ambiguities", cert.id] });
    },
  });

  // ── Handlers ──────────────────────────────────────────────────────────────────
  const handleSave = () => {
    saveDesc.mutate();
    if (isBug && incidentText.trim()) saveIncident.mutate();
  };

  const uploadDoc = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    await uploadFile(`/certifications/${cert.id}/context/document`, fd);
    qc.invalidateQueries({ queryKey: ["context", cert.id] });
    e.target.value = "";
  };

  const handleCopyMessage = (groups: AmbGroup[]) => {
    const items = groups.flatMap((g) => ambsByGroup[g]);
    if (!items.length) return;
    const qs = items.map((a, i) => `${i + 1}. ${a.question}`).join("\n");
    const text = `Hola,\n\nAntes de avanzar con la certificación necesito resolver estas dudas:\n\n${qs}\n\nGracias.`;
    navigator.clipboard.writeText(text).then(() => {
      setCopyMsg("Copiado");
      setTimeout(() => setCopyMsg(""), 2500);
    });
  };

  const toggleAmb = (id: string) =>
    setExpandedAmbs((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const toggleGroup = (g: AmbGroup) =>
    setExpandedGroups((prev) => ({ ...prev, [g]: !prev[g] }));

  return (
    <div className="space-y-4">
      {/* ── Results panel (top, shown after analysis) ─────────────────────────── */}
      {showResultsPanel && (
        <div className="space-y-4">
          {/* Summary + rules + criteria */}
          {(summaryContent?.business_summary || (criteria && criteria.length > 0)) && (
            <div className="p-3 bg-indigo-50 border border-indigo-200 rounded space-y-2">
              {summaryContent?.business_summary && (
                <p className="text-sm text-indigo-900">{summaryContent.business_summary}</p>
              )}
              {summaryContent?.rules && summaryContent.rules.length > 0 && (
                <ul className="space-y-0.5">
                  {summaryContent.rules.map((rule, i) => {
                    const isExternal = rule.startsWith("[Dep. externa]");
                    const text = isExternal ? rule.replace("[Dep. externa]", "").trim() : rule;
                    return (
                      <li key={i} className="flex gap-2 text-xs">
                        <span className={`shrink-0 mt-0.5 ${isExternal ? "text-amber-500" : "text-indigo-400"}`}>
                          {isExternal ? "⚠" : "•"}
                        </span>
                        <span className={isExternal ? "text-amber-800" : "text-indigo-800"}>
                          {isExternal && (
                            <span className="font-medium text-amber-700 mr-1">[Dep. externa]</span>
                          )}
                          {text}
                        </span>
                      </li>
                    );
                  })}
                </ul>
              )}
              {criteria && criteria.length > 0 && (
                <>
                  <button
                    className="flex items-center gap-1 text-xs text-indigo-600 hover:text-indigo-800"
                    onClick={() => setCriteriaOpen((v) => !v)}
                  >
                    {criteriaOpen ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
                    Criterios de prueba ({criteria.length})
                  </button>
                  {criteriaOpen && (
                    <div className="space-y-1 pl-3 border-l border-indigo-200">
                      {criteria.map((c) => (
                        <div key={c.id} className="flex gap-2 text-xs">
                          <span className="font-mono text-indigo-500 shrink-0">{c.code}</span>
                          <span className="text-indigo-800">{c.text}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </>
              )}
            </div>
          )}

          {/* Ambiguities grouped */}
          {ambiguities && ambiguities.length > 0 && (
            <div className="space-y-2">
              {AMB_GROUP_ORDER.map((group) => {
                const items = ambsByGroup[group];
                if (!items.length) return null;
                const isOpen = expandedGroups[group];
                const resolvedCount = items.filter((a) => a.resolution).length;
                return (
                  <div key={group} className="border border-gray-200 rounded-lg overflow-hidden">
                    {/* Group header */}
                    <div
                      className="flex items-center justify-between px-3 py-2 bg-gray-50 cursor-pointer select-none"
                      onClick={() => toggleGroup(group)}
                    >
                      <div className="flex items-center gap-2">
                        {isOpen ? (
                          <ChevronDown size={14} className="text-gray-500" />
                        ) : (
                          <ChevronRight size={14} className="text-gray-500" />
                        )}
                        <span className="text-sm font-medium text-gray-700">
                          {AMB_GROUP_LABELS[group]}
                        </span>
                        <span className="text-xs text-gray-500 bg-gray-200 rounded-full px-1.5 py-0.5 leading-none">
                          {resolvedCount}/{items.length}
                        </span>
                      </div>
                      {group === "changes_cases" && isOpen && (
                        <div
                          className="flex items-center gap-1"
                          onClick={(e) => e.stopPropagation()}
                        >
                          {copyMsg && (
                            <span className="text-xs text-green-600">{copyMsg}</span>
                          )}
                          <button
                            className="flex items-center gap-1 text-xs text-blue-600 hover:text-blue-800 px-2 py-0.5 rounded hover:bg-blue-50"
                            onClick={() => handleCopyMessage(["changes_cases", "execution_data"])}
                          >
                            <Copy size={12} />
                            Copiar como mensaje
                          </button>
                        </div>
                      )}
                    </div>

                    {/* Group items */}
                    {isOpen && (
                      <div className="divide-y divide-gray-100">
                        {items.map((a) => {
                          const isExpanded = expandedAmbs.has(a.id);
                          const isResolving = resolvingId === a.id;
                          return (
                            <div key={a.id} className={a.resolution ? "bg-green-50/50" : "bg-white"}>
                              {/* Question line */}
                              <div
                                className="flex items-start gap-2 px-3 py-2 cursor-pointer hover:bg-gray-50"
                                onClick={() => toggleAmb(a.id)}
                              >
                                <span className="shrink-0 mt-0.5 text-gray-400">
                                  {isExpanded ? (
                                    <ChevronDown size={13} />
                                  ) : (
                                    <ChevronRight size={13} />
                                  )}
                                </span>
                                <span className="text-sm text-gray-800 flex-1">{a.question}</span>
                                {a.resolution && (
                                  <CheckCircle2 size={14} className="shrink-0 text-green-500 mt-0.5" />
                                )}
                              </div>

                              {/* Expanded detail */}
                              {isExpanded && (
                                <div className="px-7 pb-3 space-y-2">
                                  <p className="text-xs text-gray-400 italic">"{a.fragment}"</p>
                                  <p className="text-xs text-gray-600">{a.explanation}</p>
                                  {a.resolution ? (
                                    <p className="text-xs text-green-700">
                                      <span className="font-medium">Resolución:</span> {a.resolution}
                                    </p>
                                  ) : isResolving ? (
                                    <div className="space-y-2">
                                      <Textarea
                                        value={resolveTexts[a.id] ?? ""}
                                        onChange={(e) =>
                                          setResolveTexts((p) => ({ ...p, [a.id]: e.target.value }))
                                        }
                                        rows={2}
                                        placeholder="Escribe la respuesta..."
                                      />
                                      <div className="flex gap-2">
                                        <Button
                                          size="sm"
                                          variant="secondary"
                                          loading={resolveAmb.isPending}
                                          disabled={!resolveTexts[a.id]?.trim()}
                                          onClick={() =>
                                            resolveAmb.mutate({
                                              ambId: a.id,
                                              resolution: resolveTexts[a.id] ?? "",
                                            })
                                          }
                                        >
                                          Guardar
                                        </Button>
                                        <Button
                                          size="sm"
                                          variant="ghost"
                                          onClick={() => setResolvingId(null)}
                                        >
                                          Cancelar
                                        </Button>
                                      </div>
                                    </div>
                                  ) : (
                                    <button
                                      className="text-xs text-blue-600 hover:text-blue-800"
                                      onClick={() => setResolvingId(a.id)}
                                    >
                                      + Registrar respuesta
                                    </button>
                                  )}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {analyzeCompleted && !hasResults && (
            <Alert variant="info">
              El análisis no encontró criterios ni ambigüedades detectables. Agrega más contexto y vuelve a analizar.
            </Alert>
          )}

          <Button
            variant="secondary"
            size="sm"
            onClick={() => onNavigate?.("testcases")}
          >
            Ir a Casos de prueba →
          </Button>
        </div>
      )}

      {/* ── Input accordion ────────────────────────────────────────────────────── */}
      <div className="border border-gray-200 rounded-lg overflow-hidden">
        <button
          className="w-full flex items-center justify-between px-4 py-3 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
          onClick={() => setInputsCollapsed((v) => !v)}
        >
          <span className="text-sm font-medium text-gray-700">
            {inputsCollapsed ? "Editar descripción del contexto" : "Descripción del contexto"}
          </span>
          {inputsCollapsed ? (
            <ChevronRight size={16} className="text-gray-500" />
          ) : (
            <ChevronDown size={16} className="text-gray-500" />
          )}
        </button>

        {!inputsCollapsed && (
          <div className="p-4 space-y-5">
            {/* Free text + propose */}
            <div>
              <Textarea
                label={
                  isBug
                    ? "Descripción del bug (o pega el reporte Aranda)"
                    : "Descripción de la brecha funcional"
                }
                value={freeText}
                onChange={(e) => setFreeText(e.target.value)}
                rows={5}
                placeholder={
                  isBug
                    ? "Ej: Al excluir a un beneficiario del contrato Y, el sistema muestra 'Error al procesar la solicitud'. La corrección consiste en..."
                    : "Ej: Se debe agregar validación que impida retroactividades mayores a 6 meses en exclusiones de afiliados..."
                }
              />
              <div className="mt-2 flex items-center gap-2 flex-wrap">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => propose.mutate()}
                  loading={propose.isPending}
                  disabled={!hasEnoughToPropose}
                  title={
                    !hasEnoughToPropose
                      ? "Escribe al menos 20 caracteres para proponer"
                      : undefined
                  }
                >
                  <Sparkles size={14} className="mr-1" />
                  Proponer estructura
                </Button>
                {proposeError && (
                  <span className="text-xs text-red-600">{proposeError}</span>
                )}
                {propose.isSuccess && (
                  <span className="text-xs text-green-600">
                    Campos completados — revisa y ajusta antes de guardar
                  </span>
                )}
              </div>

              {isBug && (
                <div className="mt-3">
                  <Textarea
                    label="Reporte Aranda completo (opcional)"
                    value={incidentText}
                    onChange={(e) => setIncidentText(e.target.value)}
                    rows={3}
                    placeholder="Pega el texto del caso tal como lo envió el usuario..."
                  />
                </div>
              )}

              {/* Document */}
              <div className="mt-3">
                <p className="text-xs text-gray-500 mb-2">
                  Documento de requerimiento (opcional)
                </p>
                {docSource ? (
                  <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-md border border-gray-200">
                    <FileText size={16} className="text-blue-500 shrink-0" />
                    <span className="text-sm flex-1 truncate">{docSource.file_name}</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => deleteSource.mutate(docSource.id)}
                    >
                      <Trash2 size={14} />
                    </Button>
                  </div>
                ) : (
                  <label className="flex items-center gap-3 p-3 border border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-blue-400 transition-colors">
                    <Upload size={16} className="text-gray-400" />
                    <span className="text-sm text-gray-500">Subir .docx o .pdf</span>
                    <input
                      type="file"
                      accept=".docx,.pdf"
                      className="hidden"
                      onChange={uploadDoc}
                    />
                  </label>
                )}
              </div>
            </div>

            {/* Structured form */}
            <div>
              <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
                Descripción estructurada
              </h4>
              <div className="space-y-3">
                {isBug
                  ? Object.entries(BUG_LABELS).map(([key, label]) => (
                      <Textarea
                        key={key}
                        label={label}
                        value={bugForm[key as keyof typeof bugForm]}
                        onChange={(e) =>
                          setBugForm((p) => ({ ...p, [key]: e.target.value }))
                        }
                        rows={2}
                      />
                    ))
                  : Object.entries(BRECHA_LABELS).map(([key, label]) => (
                      <Textarea
                        key={key}
                        label={label}
                        value={brechaForm[key as keyof typeof brechaForm]}
                        onChange={(e) =>
                          setBrechaForm((p) => ({ ...p, [key]: e.target.value }))
                        }
                        rows={2}
                      />
                    ))}
              </div>
            </div>

            {/* Save */}
            <div className="flex items-center gap-3">
              <Button onClick={handleSave} loading={saveDesc.isPending} size="sm">
                Guardar
              </Button>
              {saveMsg && <span className="text-sm text-green-600">{saveMsg}</span>}
            </div>
          </div>
        )}
      </div>

      {/* ── Analyze — outside accordion, always accessible ───────────────────── */}
      <div className="flex items-center gap-3 flex-wrap">
        <Button
          onClick={() => analyze.mutate()}
          loading={analyze.isPending}
          variant="secondary"
          size="sm"
          disabled={!hasEnoughToAnalyze}
        >
          Analizar contexto
        </Button>
        {!hasEnoughToAnalyze && (
          <span className="text-xs text-amber-600">
            Guarda al menos una descripción antes de analizar
          </span>
        )}
        {analyzeError && (
          <span className="text-xs text-red-600">{analyzeError}</span>
        )}
      </div>

      {analyzeTaskId && (
        <TaskPoller
          taskId={analyzeTaskId}
          label="Extrayendo criterios y detectando ambigüedades..."
          onSuccess={() => {
            setAnalyzeTaskId(null);
            setAnalyzeCompleted(true);
            setInputsCollapsed(true);
            qc.invalidateQueries({ queryKey: ["criteria", cert.id] });
            qc.invalidateQueries({ queryKey: ["ambiguities", cert.id] });
            qc.invalidateQueries({ queryKey: ["context", cert.id] });
          }}
          onFailure={(errMsg) => {
            setAnalyzeTaskId(null);
            const isKnown =
              errMsg.includes("no_sources") || errMsg.includes("no sources");
            setAnalyzeError(
              isKnown
                ? "El contexto está vacío. Guarda al menos una descripción antes de analizar."
                : `El análisis falló: ${errMsg}`
            );
          }}
        />
      )}
    </div>
  );
}
