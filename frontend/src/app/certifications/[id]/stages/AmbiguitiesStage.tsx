"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import type { Certification, Ambiguity } from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import { Textarea } from "@/components/ui/Textarea";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";

const typeColor: Record<string, "yellow" | "orange" | "red" | "blue" | "purple"> = {
  boundary_undefined: "yellow",
  implicit_unit: "orange",
  vague_term: "red",
  missing_branch: "blue",
  contradiction: "red",
  undefined_result: "orange",
  incomplete_context: "purple",
};

const typeLabel: Record<string, string> = {
  boundary_undefined: "Frontera sin definir",
  implicit_unit: "Unidad implícita",
  vague_term: "Término vago",
  missing_branch: "Rama faltante",
  contradiction: "Contradicción",
  undefined_result: "Resultado no definido",
  incomplete_context: "Contexto incompleto",
};

interface Props { cert: Certification; }

export function AmbiguitiesStage({ cert }: Props) {
  const qc = useQueryClient();
  const [resolutions, setResolutions] = useState<Record<string, string>>({});

  const { data: ambiguities, isLoading } = useQuery<Ambiguity[]>({
    queryKey: ["ambiguities", cert.id],
    queryFn: () => api.get<Ambiguity[]>(`/certifications/${cert.id}/ambiguities`),
  });

  const resolve = useMutation({
    mutationFn: ({ id, resolution }: { id: string; resolution: string }) =>
      api.patch(`/ambiguities/${id}`, { resolution }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["ambiguities", cert.id] }),
  });

  if (isLoading) return <div className="flex justify-center py-8"><Spinner /></div>;

  if (!ambiguities || ambiguities.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500">
        <p>No se detectaron ambigüedades en el contexto.</p>
        <p className="text-sm mt-1">Puedes continuar a la siguiente etapa.</p>
      </div>
    );
  }

  const pending = ambiguities.filter((a) => !a.resolution);
  const resolved = ambiguities.filter((a) => a.resolution);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3 text-sm text-gray-600">
        <span>{ambiguities.length} detectadas</span>
        <span>·</span>
        <span className="text-green-600">{resolved.length} resueltas</span>
        {pending.length > 0 && (
          <>
            <span>·</span>
            <span className="text-yellow-600">{pending.length} pendientes</span>
          </>
        )}
      </div>

      {ambiguities.map((amb) => (
        <div key={amb.id} className="bg-white rounded-lg border border-gray-200 p-4">
          <div className="flex items-start gap-3 mb-3">
            <Badge color={typeColor[amb.type] ?? "gray"}>{typeLabel[amb.type] ?? amb.type}</Badge>
            <span className="text-xs text-gray-400">{amb.location}</span>
            {amb.resolution && <Badge color="green" className="ml-auto">Resuelta</Badge>}
          </div>

          <blockquote className="border-l-4 border-gray-200 pl-3 text-sm text-gray-600 italic mb-3">
            {amb.fragment}
          </blockquote>

          <p className="text-sm text-gray-800 font-medium mb-3">{amb.question}</p>

          {amb.resolution ? (
            <div className="text-sm text-gray-600 bg-green-50 border border-green-200 rounded p-2">
              <span className="font-medium">Resolución: </span>{amb.resolution}
            </div>
          ) : (
            <div className="flex gap-2">
              <Textarea
                placeholder="Escribir la resolución acordada..."
                value={resolutions[amb.id] ?? ""}
                onChange={(e) => setResolutions((p) => ({ ...p, [amb.id]: e.target.value }))}
                rows={2}
                className="flex-1"
              />
              <Button
                size="sm"
                variant="secondary"
                onClick={() => resolve.mutate({ id: amb.id, resolution: resolutions[amb.id] ?? "" })}
                disabled={!resolutions[amb.id]?.trim()}
              >
                Resolver
              </Button>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
