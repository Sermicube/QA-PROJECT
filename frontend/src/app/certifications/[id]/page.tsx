"use client";
import { useEffect } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/hooks/useAuth";
import type { Certification } from "@/lib/api/types";
import { StageProgressBar } from "@/components/StageProgressBar";
import { Badge } from "@/components/ui/Badge";
import { Spinner } from "@/components/ui/Spinner";
import { Button } from "@/components/ui/Button";
import { ContextStage } from "./stages/ContextStage";
import { AmbiguitiesStage } from "./stages/AmbiguitiesStage";
import { TestCasesStage } from "./stages/TestCasesStage";
import { TestDataStage } from "./stages/TestDataStage";
import { ExecutionStage } from "./stages/ExecutionStage";
import { DeliverablesStage } from "./stages/DeliverablesStage";
import { ArrowLeft } from "lucide-react";

const STAGES = [
  { key: "context", label: "Contexto" },
  { key: "ambiguities", label: "Ambigüedades" },
  { key: "testcases", label: "Casos de prueba" },
  { key: "testdata", label: "Datos de prueba" },
  { key: "execution", label: "Ejecución" },
  { key: "deliverables", label: "Entregables" },
  { key: "closed", label: "Cerrada" },
];

const certStatusColor: Record<string, "gray" | "blue" | "yellow" | "green" | "purple"> = {
  draft: "gray",
  context: "blue",
  ambiguities: "yellow",
  testcases: "blue",
  testdata: "blue",
  execution: "purple",
  deliverables: "purple",
  closed: "green",
};

export default function CertificationPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user, isLoading: authLoading } = useAuth();

  useEffect(() => {
    if (!authLoading && !user) router.push("/login");
  }, [user, authLoading, router]);

  const { data: cert, isLoading } = useQuery<Certification>({
    queryKey: ["certification", id],
    queryFn: () => api.get<Certification>(`/certifications/${id}`),
    enabled: !!user && !!id,
  });

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

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-center gap-3 mb-1">
            <Link href="/" className="text-gray-400 hover:text-gray-600">
              <ArrowLeft size={18} />
            </Link>
            <h1 className="text-base font-semibold text-gray-900 flex-1 truncate">{cert.title}</h1>
            <Badge color={certStatusColor[cert.status] ?? "gray"}>
              {STAGES.find((s) => s.key === cert.status)?.label ?? cert.status}
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
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-6">
        <StageProgressBar current={cert.stage ?? "context"} />

        {/* Stage tabs */}
        <div className="flex gap-1 mt-6 mb-6 border-b border-gray-200 overflow-x-auto">
          {STAGES.slice(0, -1).map((s) => (
            <button
              key={s.key}
              onClick={() => setStage(s.key)}
              className={`px-4 py-2 text-sm font-medium whitespace-nowrap border-b-2 transition-colors ${
                activeStage === s.key
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>

        {/* Stage content */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          {activeStage === "context" && <ContextStage cert={cert} />}
          {activeStage === "ambiguities" && <AmbiguitiesStage cert={cert} />}
          {activeStage === "testcases" && <TestCasesStage cert={cert} />}
          {activeStage === "testdata" && <TestDataStage cert={cert} />}
          {activeStage === "execution" && <ExecutionStage cert={cert} />}
          {activeStage === "deliverables" && <DeliverablesStage cert={cert} />}
        </div>

        {/* Stage navigation */}
        {cert.status !== "closed" && (
          <div className="flex justify-between mt-4">
            {(() => {
              const idx = STAGES.findIndex((s) => s.key === activeStage);
              const prev = idx > 0 ? STAGES[idx - 1] : null;
              const next = idx < STAGES.length - 2 ? STAGES[idx + 1] : null;
              return (
                <>
                  <div>
                    {prev && (
                      <Button variant="ghost" size="sm" onClick={() => setStage(prev.key)}>
                        ← {prev.label}
                      </Button>
                    )}
                  </div>
                  <div>
                    {next && (
                      <Button variant="secondary" size="sm" onClick={() => setStage(next.key)}>
                        {next.label} →
                      </Button>
                    )}
                  </div>
                </>
              );
            })()}
          </div>
        )}
      </main>
    </div>
  );
}
