"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, uploadFile } from "@/lib/api/client";
import type { Certification, UserBase, UserBasePreview, CaseConditions, Assignment, DomainField } from "@/lib/api/types";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { Alert } from "@/components/ui/Alert";
import { Badge } from "@/components/ui/Badge";
import { TaskPoller } from "@/components/TaskPoller";
import { Upload, CheckCircle, Users, AlertTriangle } from "lucide-react";

interface Props { cert: Certification; }

export function TestDataStage({ cert }: Props) {
  const qc = useQueryClient();
  const [taskId, setTaskId] = useState<string | null>(null);
  const [assignTaskId, setAssignTaskId] = useState<string | null>(null);

  const { data: userBase } = useQuery<UserBase | null>({
    queryKey: ["userbase", cert.id],
    queryFn: () => api.get<UserBase | null>(`/certifications/${cert.id}/user-base`).catch(() => null),
  });

  const { data: preview } = useQuery<UserBasePreview>({
    queryKey: ["userbase-preview", cert.id],
    queryFn: () => api.get<UserBasePreview>(`/certifications/${cert.id}/user-base/preview`),
    enabled: !!userBase,
  });

  const { data: conditions } = useQuery<CaseConditions[]>({
    queryKey: ["conditions", cert.id],
    queryFn: () => api.get<CaseConditions[]>(`/certifications/${cert.id}/conditions`),
  });

  const { data: assignments } = useQuery<Assignment[]>({
    queryKey: ["assignments", cert.id],
    queryFn: () => api.get<Assignment[]>(`/certifications/${cert.id}/assignments`),
  });

  const { data: domainFields } = useQuery<DomainField[]>({
    queryKey: ["domain-fields", cert.id],
    queryFn: () => api.get<DomainField[]>(`/certifications/${cert.id}/domain-fields`),
  });

  const uploadBase = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const fd = new FormData();
    fd.append("file", file);
    const res = await uploadFile<{ task_id: string }>(`/certifications/${cert.id}/user-base`, fd);
    setTaskId(res.task_id);
  };

  const suggestConditions = useMutation({
    mutationFn: (tcId: string) =>
      api.post<{ task_id: string }>(`/certifications/${cert.id}/testcases/${tcId}/suggest-conditions`),
    onSuccess: (r) => setTaskId(r.task_id),
  });

  const confirmMapping = useMutation({
    mutationFn: (payload: Record<string, string>) =>
      api.post(`/certifications/${cert.id}/user-base/confirm-mapping`, payload),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["domain-fields", cert.id] }),
  });

  const runAssignment = useMutation({
    mutationFn: () =>
      api.post<{ task_id: string }>(`/certifications/${cert.id}/assignments/run`),
    onSuccess: (r) => setAssignTaskId(r.task_id),
  });

  return (
    <div className="space-y-6">
      {/* Step 1 – Upload user base */}
      <section>
        <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
          <span className="w-5 h-5 rounded-full bg-blue-600 text-white text-xs flex items-center justify-center">1</span>
          Base de usuarios de prueba
        </h4>

        {userBase ? (
          <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-md border">
            <CheckCircle size={18} className="text-green-500" />
            <div className="flex-1 text-sm">
              <p className="font-medium text-gray-800">{userBase.file_name}</p>
              <p className="text-xs text-gray-500">{userBase.row_count} filas · {userBase.columns.length} columnas</p>
            </div>
            <label className="cursor-pointer">
              <span className="text-xs text-blue-600 hover:underline">Reemplazar</span>
              <input type="file" accept=".xlsx,.xls,.txt,.csv" className="hidden" onChange={uploadBase} />
            </label>
          </div>
        ) : (
          <label className="flex flex-col items-center justify-center border-2 border-dashed border-gray-300 rounded-lg p-6 cursor-pointer hover:border-blue-400 transition-colors">
            <Upload size={20} className="text-gray-400 mb-2" />
            <span className="text-sm text-gray-500">Subir Excel o txt con usuarios de prueba</span>
            <span className="text-xs text-gray-400 mt-1">.xlsx · .xls · .txt · .csv</span>
            <input type="file" accept=".xlsx,.xls,.txt,.csv" className="hidden" onChange={uploadBase} />
          </label>
        )}

        {taskId && (
          <TaskPoller
            taskId={taskId}
            label="Procesando base de usuarios..."
            onSuccess={() => {
              setTaskId(null);
              qc.invalidateQueries({ queryKey: ["userbase", cert.id] });
              qc.invalidateQueries({ queryKey: ["userbase-preview", cert.id] });
            }}
          />
        )}

        {preview && (
          <div className="mt-3 overflow-x-auto">
            <p className="text-xs text-gray-500 mb-1">Vista previa (primeras 3 filas)</p>
            <table className="text-xs border-collapse min-w-full">
              <thead>
                <tr className="bg-gray-50">
                  {preview.columns.map((col) => (
                    <th key={col} className="border border-gray-200 px-2 py-1 text-left font-medium">{col}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.sample.map((row, i) => (
                  <tr key={i}>
                    {preview.columns.map((col) => (
                      <td key={col} className="border border-gray-200 px-2 py-1 text-gray-600">{row[col]}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Step 2 – Column mapping */}
      {userBase && domainFields && (
        <section>
          <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <span className="w-5 h-5 rounded-full bg-blue-600 text-white text-xs flex items-center justify-center">2</span>
            Mapeo de columnas
          </h4>
          <div className="space-y-2">
            {userBase.columns.map((col) => {
              const mapped = domainFields.find((f) => f.column_name === col);
              return (
                <div key={col} className="flex items-center gap-3 text-sm">
                  <span className="font-mono text-xs bg-gray-100 px-2 py-0.5 rounded w-40 truncate">{col}</span>
                  <span className="text-gray-400">→</span>
                  {mapped ? (
                    <Badge color="green">{mapped.key}</Badge>
                  ) : (
                    <Badge color="gray">sin mapear</Badge>
                  )}
                </div>
              );
            })}
          </div>
          <p className="text-xs text-gray-400 mt-2">El mapeo se confirma automáticamente al sugerir condiciones.</p>
        </section>
      )}

      {/* Step 3 – Conditions per test case */}
      {conditions && conditions.length > 0 && (
        <section>
          <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <span className="w-5 h-5 rounded-full bg-blue-600 text-white text-xs flex items-center justify-center">3</span>
            Condiciones por caso
          </h4>
          <div className="space-y-2">
            {conditions.map((cc) => (
              <div key={cc.test_case_id} className="bg-white border border-gray-200 rounded-lg p-3">
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <span className="font-mono text-xs text-gray-500">{cc.test_case_code}</span>
                    <p className="text-sm text-gray-800 mt-0.5">{cc.test_case_name}</p>
                  </div>
                  {!cc.conditions && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => suggestConditions.mutate(cc.test_case_id)}
                      loading={suggestConditions.isPending}
                    >
                      Sugerir con IA
                    </Button>
                  )}
                </div>
                {cc.conditions && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {Object.entries(cc.conditions).map(([k, v]) => (
                      <span key={k} className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded font-mono">
                        {k}: {String(v)}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* Step 4 – Run assignment */}
      {conditions && conditions.length > 0 && (
        <section>
          <h4 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
            <span className="w-5 h-5 rounded-full bg-blue-600 text-white text-xs flex items-center justify-center">4</span>
            Asignación de usuarios
          </h4>

          <Button
            variant="secondary"
            onClick={() => runAssignment.mutate()}
            loading={runAssignment.isPending}
          >
            <Users size={16} />
            Asignar usuarios
          </Button>

          {assignTaskId && (
            <TaskPoller
              taskId={assignTaskId}
              label="Ejecutando asignación óptima..."
              onSuccess={() => {
                setAssignTaskId(null);
                qc.invalidateQueries({ queryKey: ["assignments", cert.id] });
              }}
            />
          )}

          {assignments && assignments.length > 0 && (
            <div className="mt-3 space-y-2">
              {assignments.map((a) => (
                <div key={a.test_case_id} className="bg-white border border-gray-200 rounded-lg p-3">
                  <div className="flex items-center justify-between flex-wrap gap-2">
                    <div>
                      <span className="font-mono text-xs text-gray-500">{a.test_case_code}</span>
                      <p className="text-sm text-gray-800">{a.test_case_name}</p>
                    </div>
                    <Badge color={a.primary_user ? "green" : "red"}>
                      {a.primary_user ? "Asignado" : "Sin usuario"}
                    </Badge>
                  </div>
                  {a.primary_user && (
                    <div className="mt-2 text-xs text-gray-600">
                      <span className="font-medium">Principal:</span>{" "}
                      {Object.entries(a.primary_user)
                        .slice(0, 3)
                        .map(([k, v]) => `${k}: ${v}`)
                        .join(" · ")}
                    </div>
                  )}
                  {a.explanation && (
                    <p className="mt-1 text-xs text-gray-500 italic">{a.explanation}</p>
                  )}
                  {a.missing_data_request && (
                    <Alert variant="warning" className="mt-2 text-xs">
                      {a.missing_data_request}
                    </Alert>
                  )}
                  {a.backup_users && a.backup_users.length > 0 && (
                    <p className="mt-1 text-xs text-gray-400">
                      +{a.backup_users.length} usuario(s) suplente(s)
                    </p>
                  )}
                </div>
              ))}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
