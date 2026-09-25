"use client";
import { useState, type ReactNode } from "react";
import { clsx } from "clsx";

interface Tab {
  key: string;
  label: string;
  content: ReactNode;
}

interface TabsProps {
  tabs: Tab[];
  defaultTab?: string;
}

export function Tabs({ tabs, defaultTab }: TabsProps) {
  const [active, setActive] = useState(defaultTab ?? tabs[0]?.key);
  const current = tabs.find((t) => t.key === active);

  return (
    <div>
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex gap-4">
          {tabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActive(tab.key)}
              className={clsx(
                "pb-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap",
                active === tab.key
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300",
              )}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>
      <div className="pt-4">{current?.content}</div>
    </div>
  );
}
