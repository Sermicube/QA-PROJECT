"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, downloadFile } from "@/lib/api/client";
import type { Certification, Deliverable } from "@/lib/api/types";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { Badge } from "@/components/ui/Badge";
import { TaskPoller } from "@/components/TaskPoller";
import { Download, FileText, FileSpreadsheet, Mail, CheckCircle } from "lucide-react";

interface Props { cert: Certification; }

const deliverableIcon: Record<string, React.ReactNode> = {
  co_fr_vra_03: <FileSpreadsheet size={18} className="text-green-600" />,
  tfs_note: <FileText size={18} className="text-blue-600" />,
  cert_email: <Mail size={18} className="text-purple-600" />,
  zip: <Download size={18} className="text-gray-600" />,
};

const deliverableLabel: Record<string, string> = {
  co_fr_vra_03: "CO-FR-VRA-03 (Excel)",
  tfs_note: "Nota TFS",
  cert_email: "Correo de certificación",
  zip: "Paquete ZIP completo",
};

export function DeliverablesStage({ cert }: Props) {
  const qc = useQueryClient();
  const [genTaskId, setGenTaskId] = useState<string | null>(null);

  const { data: deliverables, isLoading } = useQuery<Deliverable[]>({
    queryKey: ["deliverables", cert.id],
    queryFn: () => api.get<Deliverable[]>(`/certifications/${cert.id}/deliverables`),
  });

  const generate = useMutation({
    mutationFn: () => api.post<{ task_id: string }>(`/certifications/${cert.id}/deliverables/generate`),
    onSuccess: (r) => setGenTaskId(r.task_id),
  });

  const close = useMutation({
    mutationFn: () => api.post(`/certifications/${cert.id}/close`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["certification", cert.id] }),
  });

  if (isLoading) return <div className="flex justify-center py-8"><Spinner /></div>;

  const hasDeliverables = deliverables && deliverables.length > 0;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button
          onClick={() => generate.mutate()}
          loading={generate.isPending}
          variant="secondary"
        >
          Generar entregables
        </Button>
        {genTaskId && (
          <TaskPoller
            taskId={genTaskId}
            label="Generando entregables..."
            onSuccess={() => {
              setGenTaskId(null);
              qc.invalidateQueries({ queryKey: ["deliverables", cert.id] });
            }}
          />
        )}
      </div>

      {!hasDeliverables && (
        <div className="text-center py-10 text-gray-500">
          Los entregables se generan una vez aprobados los casos y ejecutadas las pruebas.
        </div>
      )}

      {hasDeliverables && (
        <div className="space-y-3">
          {deliverables.map((d) => (
            <div key={d.id} className="bg-white border border-gray-200 rounded-lg p-4 flex items-center gap-3">
              {deliverableIcon[d.kind] ?? <FileText size={18} className="text-gray-400" />}
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-800">
                  {deliverableLabel[d.kind] ?? d.kind}
                </p>
                <p className="text-xs text-gray-500 truncate">{d.file_name}</p>
              </div>
              <Badge color="green">Listo</Badge>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => downloadFile(`/deliverables/${d.id}/download`, d.file_name)}
              >
                <Download size={14} />
                Descargar
              </Button>
            </div>
          ))}
        </div>
      )}

      {hasDeliverables && cert.status !== "closed" && (
        <div className="border-t pt-4">
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <CheckCircle size={20} className="text-green-600 shrink-0 mt-0.5" />
              <div>
                <p className="text-sm font-medium text-gray-800">Certificación lista para cerrar</p>
                <p className="text-xs text-gray-600 mt-0.5">
                  Todos los entregables están generados. Al cerrar, la certificación queda archivada y sus casos alimentan el Mapa Vivo.
                </p>
              </div>
            </div>
            <Button
              className="mt-3"
              onClick={() => close.mutate()}
              loading={close.isPending}
            >
              Cerrar certificación
            </Button>
          </div>
        </div>
      )}

      {cert.status === "closed" && (
        <div className="border-t pt-4">
          <div className="flex items-center gap-2 text-green-600">
            <CheckCircle size={16} />
            <span className="text-sm font-medium">Certificación cerrada</span>
          </div>
        </div>
      )}
    </div>
  );
}
