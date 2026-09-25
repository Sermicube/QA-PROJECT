import Link from "next/link";
import type { Certification } from "@/lib/api/types";
import { Badge } from "@/components/ui/Badge";
import { StageProgressBar } from "@/components/StageProgressBar";

const stageColor = (stage: string) => {
  if (stage === "closed") return "green";
  if (stage === "deliverables") return "purple";
  if (stage === "execution") return "orange";
  return "blue";
};

interface CertCardProps {
  cert: Certification;
}

export function CertCard({ cert }: CertCardProps) {
  return (
    <Link href={`/certifications/${cert.id}`} className="block hover:shadow-md transition-shadow">
      <div className="bg-white rounded-lg border border-gray-200 p-5">
        <div className="flex items-start justify-between mb-3">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-mono text-gray-500">{cert.external_code}</span>
              <Badge color={cert.type === "bug" ? "red" : "blue"}>
                {cert.type === "bug" ? "Bug" : "Brecha"}
              </Badge>
              <Badge color={stageColor(cert.stage)}>{cert.stage}</Badge>
            </div>
            <h3 className="font-medium text-gray-900 text-sm leading-snug">{cert.title}</h3>
            <p className="text-xs text-gray-500 mt-0.5">{cert.module}</p>
          </div>
          <span className="text-xs text-gray-400 whitespace-nowrap ml-4">
            {new Date(cert.updated_at).toLocaleDateString("es-CO")}
          </span>
        </div>
        <div className="overflow-x-auto">
          <StageProgressBar current={cert.stage} />
        </div>
      </div>
    </Link>
  );
}
