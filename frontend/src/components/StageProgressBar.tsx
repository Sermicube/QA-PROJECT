import { clsx } from "clsx";
import type { CertStage } from "@/lib/api/types";

const STAGES: { key: CertStage; label: string }[] = [
  { key: "context", label: "Contexto" },
  { key: "ambiguities", label: "Ambigüedades" },
  { key: "testcases", label: "Casos" },
  { key: "testdata", label: "Datos" },
  { key: "execution", label: "Ejecución" },
  { key: "deliverables", label: "Entregables" },
  { key: "closed", label: "Cerrada" },
];

interface StageProgressBarProps {
  current: CertStage;
}

export function StageProgressBar({ current }: StageProgressBarProps) {
  const currentIdx = STAGES.findIndex((s) => s.key === current);

  return (
    <div className="flex items-center gap-0">
      {STAGES.map((stage, idx) => {
        const done = idx < currentIdx;
        const active = idx === currentIdx;
        return (
          <div key={stage.key} className="flex items-center">
            <div className="flex flex-col items-center">
              <div
                className={clsx(
                  "w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold border-2 transition-colors",
                  done && "bg-blue-600 border-blue-600 text-white",
                  active && "bg-white border-blue-600 text-blue-600",
                  !done && !active && "bg-white border-gray-300 text-gray-400",
                )}
              >
                {done ? "✓" : idx + 1}
              </div>
              <span
                className={clsx(
                  "mt-1 text-xs whitespace-nowrap",
                  active ? "text-blue-600 font-medium" : "text-gray-500",
                )}
              >
                {stage.label}
              </span>
            </div>
            {idx < STAGES.length - 1 && (
              <div
                className={clsx(
                  "h-0.5 w-8 mx-1 mb-4 transition-colors",
                  done ? "bg-blue-600" : "bg-gray-200",
                )}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}
