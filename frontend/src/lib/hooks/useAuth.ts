"use client";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api/client";
import type { User } from "@/lib/api/types";

export function useAuth() {
  const router = useRouter();
  const qc = useQueryClient();

  const { data: user, isLoading } = useQuery<User | null>({
    queryKey: ["me"],
    queryFn: () => api.get<User>("/auth/me").catch(() => null),
    staleTime: 60_000,
  });

  const loginMutation = useMutation({
    mutationFn: ({ email, password }: { email: string; password: string }) =>
      api.post<User>("/auth/login", { email, password }),
    onSuccess: (u) => {
      qc.setQueryData(["me"], u);
      router.push("/");
    },
  });

  const logoutMutation = useMutation({
    mutationFn: () => api.post("/auth/logout"),
    onSuccess: () => {
      qc.clear();
      router.push("/login");
    },
  });

  return {
    user: user ?? null,
    isLoading,
    login: loginMutation.mutateAsync,
    loginError: loginMutation.error,
    logout: logoutMutation.mutate,
  };
}
