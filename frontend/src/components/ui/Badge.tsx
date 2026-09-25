import { clsx } from "clsx";

type Color = "gray" | "blue" | "yellow" | "green" | "red" | "purple" | "orange";

interface BadgeProps {
  color?: Color;
  children: React.ReactNode;
  className?: string;
}

const colorClasses: Record<Color, string> = {
  gray: "bg-gray-100 text-gray-700",
  blue: "bg-blue-100 text-blue-700",
  yellow: "bg-yellow-100 text-yellow-700",
  green: "bg-green-100 text-green-700",
  red: "bg-red-100 text-red-700",
  purple: "bg-purple-100 text-purple-700",
  orange: "bg-orange-100 text-orange-700",
};

export function Badge({ color = "gray", children, className }: BadgeProps) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        colorClasses[color],
        className,
      )}
    >
      {children}
    </span>
  );
}
