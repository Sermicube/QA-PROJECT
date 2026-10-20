"use client";
import { useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/hooks/useAuth";
import type { Certification } from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { ContextStage } from "./stages/ContextStage";
import { TestCasesStage } from "./stages/TestCasesStage";
import { ExecutionStage } from "./stages/ExecutionStage";
import { ArrowLeft, Plus } from "lucide-react";

const STAGE_ORDER = [
  "context", "testcases", "format", "data_request", "assignment",
  "execution", "analysis", "documentation", "review", "closed",
] as const;

const STAGE_LABELS: Record<string, string> = {
  context: "Contexto", testcases: "Casos", format: "Formato",
  data_request: "Solicitud datos", assignment: "Asignación", execution: "Ejecución",
  analysis: "Análisis", documentation: "Documentación", review: "Revisión",
  closed: "Cerrada",
};

const certStatusColor: Record<string, "gray" | "blue" | "yellow" | "green" | "purple"> = {
  draft: "gray", context: "blue", testcases: "blue", format: "blue",
  data_request: "yellow", assignment: "yellow", execution: "purple",
  analysis: "purple", documentation: "purple", review: "yellow",
  closed: "green",
};

function getActiveStages(cert: Certification): string[] {
  if (!cert.active_stages) return [...STAGE_ORDER];
  return STAGE_ORDER.filter(
    (s) => cert.active_stages![s] === "required" || cert.active_stages![s] === "optional"
  );
}

function getAddableStages(cert: Certification): string[] {
  if (!cert.active_stages) return [];
  return STAGE_ORDER.filter((s) => cert.active_stages![s] === "not_applicable");
}

export default function CertificationPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const qc = useQueryClient();
  const { user, isLoading: authLoading } = useAuth();
  const [addStageOpen, setAddStageOpen] = useState(false);

  useEffect(() => {
    if (!authLoading && !user) router.push("/login");
  }, [user, authLoading, router]);

  const { data: cert, isLoading } = useQuery<Certification>({
    queryKey: ["certification", id],
    queryFn: () => api.get<Certification>(`/certifications/${id}`),
    enabled: !!user && !!id,
  });

  const addStageMutation = useMutation({
    mutationFn: (stage: string) =>
      api.post<Certification>(`/certifications/${id}/stages/add`, { stage }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["certification", id] });
      setAddStageOpen(false);
    },
  });

  const activeStages = cert ? getActiveStages(cert) : [];
  const addableStages = cert ? getAddableStages(cert) : [];

  // Active tab = URL param ?? cert's current stage
  const activeStage = searchParams.get("stage") ?? (cert?.stage ?? "context");

  const setStage = (stage: string) => {
    router.push(`/certifications/${id}?stage=${stage}`, { scroll: false });
  };

  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!cert) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-500">
        Certificación no encontrada
      </div>
    );
  }

  // Tabs = active stages except "closed" (closed is a state, not a navigation tab)
  const navTabs = activeStages.filter((s) => s !== "closed");

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-center gap-3 mb-1">
            <Link href="/" className="text-gray-400 hover:text-gray-600">
              <ArrowLeft size={18} />
            </Link>
            <h1 className="text-base font-semibold text-gray-900 flex-1 truncate">
              {cert.title}
            </h1>
            <Badge color={certStatusColor[cert.stage] ?? "gray"}>
              {STAGE_LABELS[cert.stage] ?? cert.stage}
            </Badge>
          </div>
          <div className="flex items-center gap-3 text-xs text-gray-500 ml-7">
            <span className="font-mono">{cert.external_code}</span>
            <span>·</span>
            <span>{cert.module}</span>
            <span>·</span>
            <Badge color={cert.type === "bug" ? "red" : "blue"} className="text-xs">
              {cert.type}
            </Badge>
            {cert.recipe_code && (
              <>
                <span>·</span>
                <span className="text-gray-400">{cert.recipe_code}</span>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-6">
        {/* Tab navigation (primary navigation) — closed excluded */}
        <div className="flex gap-0 border-b border-gray-200 overflow-x-auto mb-6">
          {navTabs.map((s) => {
            const isOptional = cert.active_stages?.[s as keyof typeof cert.active_stages] === "optional";
            return (
              <button
                key={s}
                onClick={() => setStage(s)}
                className={`px-4 py-2.5 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                  activeStage === s
                    ? "border-blue-600 text-blue-600"
                    : s === cert.stage
                    ? "border-transparent text-gray-700 font-semibold"
                    : "border-transparent text-gray-500 hover:text-gray-700"
                }`}
              >
                {STAGE_LABELS[s] ?? s}
                {isOptional && (
                  <span className="ml-1 text-xs font-normal text-gray-400">(opc)</span>
                )}
                {s === cert.stage && (
                  <span className="ml-1.5 inline-block w-1.5 h-1.5 rounded-full bg-blue-500 align-middle" />
                )}
              </button>
            );
          })}

          {/* Agregar etapa — at end of tab row */}
          {cert.status !== "closed" && addableStages.length > 0 && (
            <button
              onClick={() => setAddStageOpen(true)}
              title="Agregar etapa opcional"
              className="ml-1 px-2.5 py-2.5 text-gray-400 hover:text-blue-500 border-b-2 border-transparent transition-colors"
            >
              <Plus size={16} />
            </button>
          )}
        </div>

        {/* Stage content */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          {activeStage === "context" && <ContextStage cert={cert} onNavigate={setStage} />}
          {activeStage === "testcases" && <TestCasesStage cert={cert} />}
          {activeStage === "execution" && <ExecutionStage cert={cert} />}
          {!["context", "testcases", "execution"].includes(activeStage) && (
            <div className="text-center py-12 text-gray-400">
              <p className="text-sm">
                Módulo <strong>{STAGE_LABELS[activeStage] ?? activeStage}</strong> en construcción
              </p>
            </div>
          )}
        </div>

        {/* Navigation buttons */}
        {cert.status !== "closed" && (
          <div className="flex justify-between mt-4">
            {(() => {
              const idx = navTabs.indexOf(activeStage);
              const prev = idx > 0 ? navTabs[idx - 1] : null;
              const next = idx < navTabs.length - 1 ? navTabs[idx + 1] : null;
              return (
                <>
                  <div>
                    {prev && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setStage(prev)}
                      >
                        ← {STAGE_LABELS[prev] ?? prev}
                      </Button>
                    )}
                  </div>
                  <div>
                    {next && (
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setStage(next)}
                      >
                        {STAGE_LABELS[next] ?? next} →
                      </Button>
                    )}
                  </div>
                </>
              );
            })()}
          </div>
        )}
      </main>

      {/* Modal: agregar etapa */}
      <Modal open={addStageOpen} title="Agregar etapa" onClose={() => setAddStageOpen(false)}>
        <p className="text-sm text-gray-600 mb-4">
          Selecciona una etapa para activarla en esta certificación. Quedará como opcional.
        </p>
        <div className="space-y-2">
          {addableStages.map((stage) => (
            <button
              key={stage}
              onClick={() => addStageMutation.mutate(stage)}
              disabled={addStageMutation.isPending}
              className="w-full text-left px-4 py-2.5 rounded-lg border border-gray-200 hover:border-blue-400 hover:bg-blue-50 text-sm font-medium text-gray-700 transition-colors disabled:opacity-50"
            >
              {STAGE_LABELS[stage] ?? stage}
            </button>
          ))}
        </div>
        {addStageMutation.isError && (
          <p className="mt-3 text-xs text-red-600">
            Error al agregar la etapa. Intenta de nuevo.
          </p>
        )}
      </Modal>
    </div>
  );
}
