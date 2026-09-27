"use client";
import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/hooks/useAuth";
import type { Certification } from "@/lib/api/types";
import { CertCard } from "@/components/CertCard";
import { Button } from "@/components/ui/Button";
import { Spinner } from "@/components/ui/Spinner";
import { LogOut, Plus, ShieldCheck } from "lucide-react";

export default function DashboardPage() {
  const router = useRouter();
  const { user, isLoading: authLoading, logout } = useAuth();

  useEffect(() => {
    if (!authLoading && !user) router.push("/login");
  }, [user, authLoading, router]);

  const { data: certs, isLoading } = useQuery<Certification[]>({
    queryKey: ["certifications"],
    queryFn: () => api.get<Certification[]>("/certifications"),
    enabled: !!user,
  });

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!user) return null;

  return (
    <div className="min-h-screen">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold text-gray-900">Copiloto de Certificación QA</h1>
            <p className="text-xs text-gray-500">{user.full_name} — {user.module ?? user.role}</p>
          </div>
          <div className="flex items-center gap-3">
            <Link href="/metrics">
              <Button variant="ghost" size="sm">Métricas</Button>
            </Link>
            <Link href="/knowledge">
              <Button variant="ghost" size="sm">Mapa Vivo</Button>
            </Link>
            <Link href="/settings">
              <Button variant="ghost" size="sm">Configuración</Button>
            </Link>
            {user.role === "admin" && (
              <Link href="/admin">
                <Button variant="ghost" size="sm">
                  <ShieldCheck size={15} />
                  Admin
                </Button>
              </Link>
            )}
            <Button variant="ghost" size="sm" onClick={() => logout()}>
              <LogOut size={16} />
              Salir
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-xl font-semibold text-gray-900">Certificaciones</h2>
          <Link href="/certifications/new">
            <Button size="sm">
              <Plus size={16} />
              Nueva certificación
            </Button>
          </Link>
        </div>

        {isLoading && (
          <div className="flex justify-center py-16">
            <Spinner size="lg" />
          </div>
        )}

        {!isLoading && (!certs || certs.length === 0) && (
          <div className="text-center py-16 bg-white rounded-lg border border-dashed border-gray-300">
            <p className="text-gray-500 mb-4">No hay certificaciones aún.</p>
            <Link href="/certifications/new">
              <Button>Crear primera certificación</Button>
            </Link>
          </div>
        )}

        {certs && certs.length > 0 && (
          <div className="grid gap-4">
            {certs.map((cert) => (
              <CertCard key={cert.id} cert={cert} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
