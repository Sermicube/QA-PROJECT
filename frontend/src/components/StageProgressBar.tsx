import { clsx } from "clsx";
import type { ActiveStages } from "@/lib/api/types";

const STAGE_ORDER = [
  "context", "testcases", "format", "data_request", "assignment",
  "execution", "analysis", "documentation", "review",
  // "closed" is a status, not a progress step — excluded from the bar
] as const;

const STAGE_LABELS: Record<string, string> = {
  context: "Contexto",
  testcases: "Casos",
  format: "Formato",
  data_request: "Solicitud",
  assignment: "Asignación",
  execution: "Ejecución",
  analysis: "Análisis",
  documentation: "Documentación",
  review: "Revisión",
};

interface StageProgressBarProps {
  /** Certification's actual current stage (workflow position) */
  current: string;
  /** Tab being viewed by the analyst (may differ from current) */
  viewing?: string;
  activeStages?: ActiveStages | null;
  onAddStage?: () => void;
}

export function StageProgressBar({
  current,
  viewing,
  activeStages,
  onAddStage,
}: StageProgressBarProps) {
  const stages = STAGE_ORDER.filter(
    (s) => !activeStages || activeStages[s] === "required" || activeStages[s] === "optional"
  );

  const currentIdx = stages.indexOf(current as typeof STAGE_ORDER[number]);

  return (
    <div className="flex items-center gap-0 flex-wrap">
      {stages.map((key, idx) => {
        const done = idx < currentIdx;
        const isCurrent = key === current;
        const isViewing = viewing ? key === viewing : false;
        const isViewingDifferent = isViewing && !isCurrent;

        const isOptional = activeStages?.[key] === "optional";
        return (
          <div key={key} className="flex items-center">
            <div className="flex flex-col items-center">
              <div
                title={`${STAGE_LABELS[key] ?? key}${isOptional ? " (opcional)" : ""}`}
                className={clsx(
                  "w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold transition-colors",
                  isOptional ? "border-dashed border-2" : "border-2",
                  done && "bg-blue-600 border-blue-600 text-white",
                  isCurrent && "bg-white border-blue-600 text-blue-600 ring-2 ring-blue-200",
                  isViewingDifferent && "bg-white border-blue-400 text-blue-400",
                  !done && !isCurrent && !isViewingDifferent && isOptional && "bg-white border-gray-300 text-gray-300",
                  !done && !isCurrent && !isViewingDifferent && !isOptional && "bg-white border-gray-300 text-gray-400",
                )}
              >
                {done ? "✓" : idx + 1}
              </div>
              <span
                className={clsx(
                  "mt-0.5 text-xs whitespace-nowrap",
                  isCurrent ? "text-blue-600 font-semibold" : isOptional ? "text-gray-300" : "text-gray-400",
                  isViewingDifferent && "text-blue-400",
                )}
              >
                {STAGE_LABELS[key] ?? key}
              </span>
            </div>
            {idx < stages.length - 1 && (
              <div
                className={clsx(
                  "h-0.5 w-5 mx-1 mb-5 transition-colors",
                  done ? "bg-blue-600" : "bg-gray-200",
                )}
              />
            )}
          </div>
        );
      })}

      {onAddStage && (
        <button
          onClick={onAddStage}
          title="Agregar etapa opcional"
          className="ml-3 mb-5 w-6 h-6 rounded-full border-2 border-dashed border-gray-300 text-gray-400 hover:border-blue-400 hover:text-blue-500 flex items-center justify-center text-sm transition-colors"
        >
          +
        </button>
      )}
    </div>
  );
}
