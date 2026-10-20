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
import {
  CheckCircle, AlertTriangle, ChevronDown, ChevronRight,
  Pencil, Trash2, ArrowUp, ArrowDown, X, Save,
} from "lucide-react";

interface EditForm {
  name: string;
  preconditions: string;
  steps: string;
  expected_result: string;
  boundary: string;
  // flags
  is_suggestion: boolean;
  pending_assumption: boolean;
  assumption_note: string;
  requires_db_verification: boolean;
  db_verification_note: string;
}

function tcToForm(tc: TestCase): EditForm {
  return {
    name: tc.name,
    preconditions: tc.preconditions.join("\n"),
    steps: tc.steps.join("\n"),
    expected_result: tc.expected_result,
    boundary: tc.boundary ?? "",
    is_suggestion: tc.flags?.is_suggestion ?? false,
    pending_assumption: tc.flags?.pending_assumption ?? false,
    assumption_note: tc.flags?.assumption_note ?? "",
    requires_db_verification: tc.flags?.requires_db_verification ?? false,
    db_verification_note: tc.flags?.db_verification_note ?? "",
  };
}

interface Props { cert: Certification; }

export function TestCasesStage({ cert }: Props) {
  const qc = useQueryClient();
  const [generateTaskId, setGenerateTaskId] = useState<string | null>(null);
  const [lintResults, setLintResults] = useState<Record<string, LintIssue[]>>({});
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editForms, setEditForms] = useState<Record<string, EditForm>>({});
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [approveErrors, setApproveErrors] = useState<Record<string, string>>({});
  // "replace" | "add" | null — confirm dialog when cases already exist
  const [regenConfirm, setRegenConfirm] = useState<boolean>(false);

  const BOUNDARY_LABEL: Record<string, string> = { before: "Anterior", equal: "Igual", after: "Posterior" };

  const isConsultStyle =
    cert.case_style === "consult_service" ||
    cert.recipe_code === "service_rest_json" ||
    cert.recipe_code === "service_soap_xml";

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
    onSuccess: (_tc, tcId) => {
      qc.invalidateQueries({ queryKey: ["testcases", cert.id] });
      setApproveErrors((p) => { const n = { ...p }; delete n[tcId]; return n; });
    },
    onError: (err: unknown, tcId: string) => {
      const msg =
        err instanceof Error ? err.message : "No se pudo aprobar el caso.";
      setApproveErrors((p) => ({ ...p, [tcId]: msg }));
    },
  });

  const updateCase = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Record<string, unknown> }) =>
      api.patch<TestCase>(`/testcases/${id}?cert_id=${cert.id}`, data),
    onSuccess: (_tc, { id }) => {
      qc.invalidateQueries({ queryKey: ["testcases", cert.id] });
      setEditingId(null);
      setLintResults((p) => { const next = { ...p }; delete next[id]; return next; });
    },
  });

  const deleteCase = useMutation({
    mutationFn: (id: string) => api.delete<void>(`/testcases/${id}?cert_id=${cert.id}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["testcases", cert.id] });
      setDeleteConfirm(null);
    },
  });

  const reorderCase = useMutation({
    mutationFn: async ({ tc, direction }: { tc: TestCase; direction: "up" | "down" }) => {
      const sorted = [...(cases ?? [])].sort((a, b) =>
        a.order !== b.order ? a.order - b.order : a.code.localeCompare(b.code)
      );
      const idx = sorted.findIndex((c) => c.id === tc.id);
      const targetIdx = direction === "up" ? idx - 1 : idx + 1;
      if (targetIdx < 0 || targetIdx >= sorted.length) return;
      const target = sorted[targetIdx];
      await api.patch(`/testcases/${tc.id}?cert_id=${cert.id}`, { order: targetIdx });
      await api.patch(`/testcases/${target.id}?cert_id=${cert.id}`, { order: idx });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["testcases", cert.id] }),
  });

  const deleteAllCases = useMutation({
    mutationFn: async () => {
      const all = cases ?? [];
      for (const tc of all) {
        await api.delete<void>(`/testcases/${tc.id}?cert_id=${cert.id}`);
      }
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["testcases", cert.id] });
      generate.mutate();
    },
  });

  const startEdit = (tc: TestCase) => {
    setEditForms((p) => ({ ...p, [tc.id]: tcToForm(tc) }));
    setEditingId(tc.id);
    setExpandedId(tc.id);
  };

  const cancelEdit = () => setEditingId(null);

  const saveEdit = (tc: TestCase) => {
    const form = editForms[tc.id];
    if (!form) return;
    const data: Record<string, unknown> = {
      name: form.name,
      preconditions: isConsultStyle
        ? []
        : form.preconditions.split("\n").map((s) => s.trim()).filter(Boolean),
      steps: form.steps.split("\n").map((s) => s.trim()).filter(Boolean),
      expected_result: form.expected_result,
      flags: {
        is_suggestion: form.is_suggestion,
        pending_assumption: form.pending_assumption,
        assumption_note: form.assumption_note || null,
        requires_db_verification: form.requires_db_verification,
        db_verification_note: form.db_verification_note || null,
      },
    };
    if (form.boundary) data.boundary = form.boundary;
    updateCase.mutate({ id: tc.id, data });
  };

  const updateForm = (id: string, field: keyof EditForm, value: string | boolean) =>
    setEditForms((p) => ({ ...p, [id]: { ...p[id], [field]: value } }));

  const handleGenerateClick = () => {
    if (cases && cases.length > 0) {
      setRegenConfirm(true);
    } else {
      generate.mutate();
    }
  };

  if (isLoading) return <div className="flex justify-center py-8"><Spinner /></div>;

  const sortedCases = cases
    ? [...cases].sort((a, b) =>
        a.order !== b.order ? a.order - b.order : a.code.localeCompare(b.code)
      )
    : [];
  const uncoveredCriteria = traceability?.filter((r) => r.case_codes.length === 0) ?? [];

  return (
    <div className="space-y-6">
      {/* ── Acciones globales ────────────────────────────────────────────── */}
      <div className="flex items-center gap-3 flex-wrap">
        <Button
          onClick={handleGenerateClick}
          loading={generate.isPending || deleteAllCases.isPending}
          variant="secondary"
        >
          Generar casos con IA
        </Button>

        {/* Confirm regen dialog */}
        {regenConfirm && (
          <span className="flex items-center gap-2 text-sm text-gray-700 bg-amber-50 border border-amber-200 rounded px-3 py-1.5">
            <AlertTriangle size={14} className="text-amber-600 shrink-0" />
            Ya existen {cases?.length} caso(s).
            <button
              className="px-2 py-0.5 bg-red-600 text-white rounded text-xs hover:bg-red-700"
              onClick={() => { setRegenConfirm(false); deleteAllCases.mutate(); }}
            >
              Reemplazar
            </button>
            <button
              className="px-2 py-0.5 bg-blue-600 text-white rounded text-xs hover:bg-blue-700"
              onClick={() => { setRegenConfirm(false); generate.mutate(); }}
            >
              Añadir
            </button>
            <button
              className="px-2 py-0.5 border border-gray-300 rounded text-xs hover:bg-gray-50"
              onClick={() => setRegenConfirm(false)}
            >
              Cancelar
            </button>
          </span>
        )}

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

      {sortedCases.length === 0 && (
        <div className="text-center py-12 text-gray-500">
          No hay casos de prueba aún. Genera con IA o importa manualmente.
        </div>
      )}

      {/* ── Lista de casos ───────────────────────────────────────────────── */}
      {sortedCases.length > 0 && (
        <div className="space-y-3">
          {sortedCases.map((tc, idx) => {
            const issues = lintResults[tc.id] ?? [];
            const wasLinted = tc.id in lintResults;
            const hasErrors = issues.some((i) => i.severity === "error");
            const isExpanded = expandedId === tc.id;
            const isEditing = editingId === tc.id;
            const form = editForms[tc.id];
            const isFirst = idx === 0;
            const isLast = idx === sortedCases.length - 1;
            const approveErr = approveErrors[tc.id];

            return (
              <div
                key={tc.id}
                data-testid={`case-${tc.code}`}
                className="bg-white border border-gray-200 rounded-lg overflow-hidden"
              >
                {/* Cabecera */}
                <div className="flex items-start gap-2 p-4">
                  <button
                    className="mt-0.5 text-gray-400 hover:text-gray-600 shrink-0"
                    onClick={() => setExpandedId(isExpanded ? null : tc.id)}
                    title={isExpanded ? "Colapsar" : "Ver detalle"}
                  >
                    {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                  </button>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="font-mono text-xs text-gray-500">{tc.code}</span>
                      <Badge color={tc.status === "approved" ? "green" : "gray"}>
                        {tc.status === "approved" ? "Aprobado" : "Borrador"}
                      </Badge>
                      {tc.boundary && <Badge color="blue">{BOUNDARY_LABEL[tc.boundary] ?? tc.boundary}</Badge>}
                      {tc.flags?.is_suggestion && (
                        <Badge color="gray">Sugerencia</Badge>
                      )}
                      {tc.flags?.pending_assumption && (
                        <Badge color="yellow">Supuesto pendiente</Badge>
                      )}
                      {tc.flags?.requires_db_verification && (
                        <Badge color="orange">Verificar BD</Badge>
                      )}
                    </div>
                    <p className={`text-sm text-gray-800 ${tc.flags?.is_suggestion ? "italic text-gray-500" : ""}`}>
                      {tc.name}
                    </p>
                    {approveErr && (
                      <p className="text-xs text-red-600 mt-1">{approveErr}</p>
                    )}
                  </div>

                  <div className="flex items-center gap-1 shrink-0">
                    {/* Reordenar */}
                    {!isFirst && (
                      <button
                        className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30"
                        onClick={() => reorderCase.mutate({ tc, direction: "up" })}
                        disabled={reorderCase.isPending}
                        title="Mover arriba"
                      >
                        <ArrowUp size={14} />
                      </button>
                    )}
                    {!isLast && (
                      <button
                        className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30"
                        onClick={() => reorderCase.mutate({ tc, direction: "down" })}
                        disabled={reorderCase.isPending}
                        title="Mover abajo"
                      >
                        <ArrowDown size={14} />
                      </button>
                    )}

                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => lintCase.mutate(tc.id)}
                      loading={lintCase.isPending}
                    >
                      Lintear
                    </Button>

                    {tc.status !== "approved" && (
                      <>
                        <button
                          className="p-1 text-gray-500 hover:text-blue-600"
                          onClick={() => startEdit(tc)}
                          title="Editar"
                        >
                          <Pencil size={14} />
                        </button>
                        <Button
                          variant="secondary"
                          size="sm"
                          onClick={() => approve.mutate(tc.id)}
                          loading={approve.isPending}
                        >
                          Aprobar
                        </Button>
                      </>
                    )}

                    {deleteConfirm !== tc.id ? (
                      <button
                        className="p-1 text-gray-400 hover:text-red-500"
                        onClick={() => setDeleteConfirm(tc.id)}
                        title="Eliminar"
                      >
                        <Trash2 size={14} />
                      </button>
                    ) : (
                      <span className="flex items-center gap-1 text-xs text-red-600">
                        <span>¿Eliminar?</span>
                        <button
                          className="px-1.5 py-0.5 bg-red-600 text-white rounded text-xs hover:bg-red-700"
                          onClick={() => deleteCase.mutate(tc.id)}
                        >
                          Sí
                        </button>
                        <button
                          className="px-1.5 py-0.5 border border-gray-300 rounded text-xs hover:bg-gray-50 text-gray-700"
                          onClick={() => setDeleteConfirm(null)}
                        >
                          No
                        </button>
                      </span>
                    )}
                  </div>
                </div>

                {/* Detalle expandido — modo lectura */}
                {isExpanded && !isEditing && (
                  <div className="border-t border-gray-100 px-4 pb-4 pt-3 space-y-3 bg-gray-50 text-sm">
                    {tc.flags?.pending_assumption && tc.flags?.assumption_note && (
                      <div className="flex gap-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
                        <AlertTriangle size={12} className="shrink-0 mt-0.5" />
                        <span><strong>Supuesto asumido:</strong> {tc.flags.assumption_note}</span>
                      </div>
                    )}
                    {tc.flags?.requires_db_verification && (
                      <div className="flex gap-2 p-2 bg-orange-50 border border-orange-200 rounded text-xs text-orange-800">
                        <AlertTriangle size={12} className="shrink-0 mt-0.5" />
                        <span>
                          <strong>Verificación en BD requerida.</strong>{" "}
                          {tc.flags.db_verification_note
                            ? `Consultar: ${tc.flags.db_verification_note}.`
                            : "Ver detalle en el caso."}
                          {" "}Considera verificar mediante la respuesta del servicio como alternativa.
                        </span>
                      </div>
                    )}
                    {isConsultStyle ? (
                      /* Short format: no preconditions, steps shown as "Descripción" */
                      <div>
                        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                          Descripción
                        </p>
                        <p className="text-gray-700 whitespace-pre-wrap">
                          {tc.steps.join("\n") || "—"}
                        </p>
                      </div>
                    ) : (
                      /* Full format */
                      <>
                        {tc.preconditions.length > 0 && (
                          <div>
                            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                              Precondiciones
                            </p>
                            <ul className="list-disc list-inside space-y-0.5 text-gray-700">
                              {tc.preconditions.map((p, i) => <li key={i}>{p}</li>)}
                            </ul>
                          </div>
                        )}
                        {tc.steps.length > 0 && (
                          <div>
                            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                              Pasos
                            </p>
                            <ol className="list-decimal list-inside space-y-0.5 text-gray-700">
                              {tc.steps.map((s, i) => <li key={i}>{s}</li>)}
                            </ol>
                          </div>
                        )}
                      </>
                    )}
                    <div>
                      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">
                        Resultado esperado
                      </p>
                      <p className="text-gray-700">{tc.expected_result}</p>
                    </div>
                  </div>
                )}

                {/* Formulario de edición */}
                {isEditing && form && (
                  <div className="border-t border-blue-100 px-4 pb-4 pt-3 bg-blue-50 space-y-3">
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Nombre del caso
                      </label>
                      <textarea
                        className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400 resize-none bg-white"
                        rows={2}
                        value={form.name}
                        onChange={(e) => updateForm(tc.id, "name", e.target.value)}
                      />
                    </div>
                    {isConsultStyle ? (
                      <div>
                        <label className="block text-xs font-medium text-gray-700 mb-1">
                          Descripción{" "}
                          <span className="font-normal text-gray-400">(llamada al servicio y parámetros)</span>
                        </label>
                        <textarea
                          className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400 resize-none bg-white"
                          rows={4}
                          value={form.steps}
                          onChange={(e) => updateForm(tc.id, "steps", e.target.value)}
                          placeholder="Se invoca el servicio mediante GET /api/... con los parámetros..."
                        />
                      </div>
                    ) : (
                      <>
                        <div>
                          <label className="block text-xs font-medium text-gray-700 mb-1">
                            Precondiciones{" "}
                            <span className="font-normal text-gray-400">(una por línea)</span>
                          </label>
                          <textarea
                            className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400 resize-none bg-white"
                            rows={3}
                            value={form.preconditions}
                            onChange={(e) => updateForm(tc.id, "preconditions", e.target.value)}
                            placeholder={"Precondición 1\nPrecondición 2"}
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-gray-700 mb-1">
                            Pasos{" "}
                            <span className="font-normal text-gray-400">(uno por línea)</span>
                          </label>
                          <textarea
                            className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400 resize-none bg-white"
                            rows={4}
                            value={form.steps}
                            onChange={(e) => updateForm(tc.id, "steps", e.target.value)}
                            placeholder={"Se accede a Beyond Health...\nSe ingresa la fecha..."}
                          />
                        </div>
                      </>
                    )}
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Resultado esperado
                      </label>
                      <textarea
                        className="w-full border border-gray-300 rounded px-2 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-blue-400 resize-none bg-white"
                        rows={2}
                        value={form.expected_result}
                        onChange={(e) => updateForm(tc.id, "expected_result", e.target.value)}
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-gray-700 mb-1">
                        Frontera
                      </label>
                      <select
                        className="border border-gray-300 rounded px-2 py-1 text-sm bg-white focus:outline-none focus:ring-1 focus:ring-blue-400"
                        value={form.boundary}
                        onChange={(e) => updateForm(tc.id, "boundary", e.target.value)}
                      >
                        <option value="">— sin frontera —</option>
                        <option value="before">Anterior</option>
                        <option value="equal">Igual</option>
                        <option value="after">Posterior</option>
                      </select>
                    </div>

                    {/* ── Marcas ────────────────────────────────────────── */}
                    <div className="border-t border-blue-200 pt-3 space-y-2">
                      <p className="text-xs font-semibold text-gray-600 uppercase tracking-wide">Marcas</p>

                      <label className="flex items-center gap-2 text-xs text-gray-700 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={form.is_suggestion}
                          onChange={(e) => updateForm(tc.id, "is_suggestion", e.target.checked)}
                          className="rounded"
                        />
                        Sugerencia (no entra por defecto en el formato)
                      </label>

                      <label className="flex items-center gap-2 text-xs text-gray-700 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={form.pending_assumption}
                          onChange={(e) => updateForm(tc.id, "pending_assumption", e.target.checked)}
                          className="rounded"
                        />
                        Supuesto pendiente de confirmar
                      </label>
                      {form.pending_assumption && (
                        <textarea
                          className="w-full border border-yellow-300 rounded px-2 py-1 text-xs bg-yellow-50 focus:outline-none focus:ring-1 focus:ring-yellow-400 resize-none"
                          rows={2}
                          placeholder="¿Qué supuesto se asumió? (máx. 80 caracteres)"
                          maxLength={80}
                          value={form.assumption_note}
                          onChange={(e) => updateForm(tc.id, "assumption_note", e.target.value)}
                        />
                      )}

                      <label className="flex items-center gap-2 text-xs text-gray-700 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={form.requires_db_verification}
                          onChange={(e) => updateForm(tc.id, "requires_db_verification", e.target.checked)}
                          className="rounded"
                        />
                        Requiere verificación en BD
                      </label>
                      {form.requires_db_verification && (
                        <textarea
                          className="w-full border border-orange-300 rounded px-2 py-1 text-xs bg-orange-50 focus:outline-none focus:ring-1 focus:ring-orange-400 resize-none"
                          rows={2}
                          placeholder="Tabla y campo a consultar (máx. 100 caracteres)"
                          maxLength={100}
                          value={form.db_verification_note}
                          onChange={(e) => updateForm(tc.id, "db_verification_note", e.target.value)}
                        />
                      )}
                    </div>

                    <div className="flex gap-2 pt-1">
                      <Button
                        size="sm"
                        onClick={() => saveEdit(tc)}
                        loading={updateCase.isPending}
                      >
                        <Save size={13} className="mr-1" />
                        Guardar
                      </Button>
                      <Button variant="ghost" size="sm" onClick={cancelEdit}>
                        <X size={13} className="mr-1" />
                        Cancelar
                      </Button>
                    </div>
                  </div>
                )}

                {/* Resultados del linter */}
                {wasLinted && issues.length === 0 && (
                  <div className="border-t border-gray-100 px-4 pb-3 pt-2 flex gap-1 text-xs text-green-700 items-center">
                    <CheckCircle size={12} />
                    <span>Sin observaciones</span>
                  </div>
                )}
                {issues.length > 0 && (
                  <div className="border-t border-gray-100 px-4 pb-3 pt-2 space-y-1 bg-white">
                    {issues.map((issue) => (
                      <div
                        key={issue.code}
                        className={`flex gap-2 text-xs p-2 rounded ${
                          issue.severity === "error"
                            ? "bg-red-50 text-red-700"
                            : "bg-yellow-50 text-yellow-700"
                        }`}
                      >
                        <AlertTriangle size={12} className="shrink-0 mt-0.5" />
                        <span>
                          <strong>{issue.code}</strong> — {issue.message}
                        </span>
                      </div>
                    ))}
                  </div>
                )}

                {issues.length > 0 && !hasErrors && (
                  <div className="px-4 pb-3 flex gap-1 text-xs text-green-600 items-center">
                    <CheckCircle size={12} />
                    <span>Sin errores — listo para aprobar</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* ── Matriz de trazabilidad ───────────────────────────────────────── */}
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
                  <tr
                    key={row.criterion_id}
                    className={row.case_codes.length === 0 ? "bg-red-50" : ""}
                  >
                    <td className="border border-gray-200 px-3 py-2">
                      <span className="font-mono text-blue-600">{row.criterion_code}</span>
                      <span className="ml-2 text-gray-600">{row.criterion_text}</span>
                    </td>
                    <td className="border border-gray-200 px-3 py-2">
                      {row.case_codes.length > 0 ? (
                        row.case_codes.join(", ")
                      ) : (
                        <span className="text-red-500">Sin caso</span>
                      )}
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
