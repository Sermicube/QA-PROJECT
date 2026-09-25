import { clsx } from "clsx";
import { AlertCircle, AlertTriangle, Info } from "lucide-react";
import type { ReactNode } from "react";

type Variant = "info" | "warning" | "error";

interface AlertProps {
  variant?: Variant;
  children: ReactNode;
  className?: string;
}

const styles: Record<Variant, { wrapper: string; icon: ReactNode }> = {
  info: {
    wrapper: "bg-blue-50 border-blue-200 text-blue-800",
    icon: <Info size={16} className="text-blue-500 shrink-0 mt-0.5" />,
  },
  warning: {
    wrapper: "bg-yellow-50 border-yellow-200 text-yellow-800",
    icon: <AlertTriangle size={16} className="text-yellow-500 shrink-0 mt-0.5" />,
  },
  error: {
    wrapper: "bg-red-50 border-red-200 text-red-800",
    icon: <AlertCircle size={16} className="text-red-500 shrink-0 mt-0.5" />,
  },
};

export function Alert({ variant = "info", children, className }: AlertProps) {
  const { wrapper, icon } = styles[variant];
  return (
    <div className={clsx("flex gap-2 rounded-md border p-3 text-sm", wrapper, className)}>
      {icon}
      <div>{children}</div>
    </div>
  );
}
