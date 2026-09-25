"use client";
import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import type { TaskStatus } from "@/lib/api/types";
import { Spinner } from "@/components/ui/Spinner";

interface TaskPollerProps {
  taskId: string;
  onSuccess?: (result: Record<string, unknown>) => void;
  onFailure?: (error: string) => void;
  label?: string;
}

export function TaskPoller({ taskId, onSuccess, onFailure, label = "Procesando..." }: TaskPollerProps) {
  const { data } = useQuery<TaskStatus>({
    queryKey: ["task", taskId],
    queryFn: () => api.get<TaskStatus>(`/tasks/${taskId}`),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "pending" ? 2000 : false;
    },
  });

  useEffect(() => {
    if (data?.status === "success" && onSuccess) onSuccess(data.result ?? {});
    if (data?.status === "failure" && onFailure) onFailure(JSON.stringify(data.result));
  }, [data?.status]);

  if (data?.status === "success" || data?.status === "failure") return null;

  return (
    <div className="flex items-center gap-2 text-sm text-gray-600 py-2">
      <Spinner size="sm" />
      <span>{label}</span>
    </div>
  );
}
