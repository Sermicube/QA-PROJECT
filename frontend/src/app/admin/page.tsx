"use client";
import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/hooks/useAuth";
import type { User } from "@/lib/api/types";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Select } from "@/components/ui/Select";
import { Badge } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { ArrowLeft, Plus, UserX } from "lucide-react";

const ROLES = ["analyst", "lead", "admin"] as const;
type Role = (typeof ROLES)[number];

const roleBadge: Record<Role, "gray" | "blue" | "purple"> = {
  analyst: "gray",
  lead: "blue",
  admin: "purple",
};

interface AdminUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

interface NewUserForm {
  email: string;
  full_name: string;
  password: string;
  role: Role;
}

const emptyForm: NewUserForm = { email: "", full_name: "", password: "", role: "analyst" };

export default function AdminPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { user, isLoading: authLoading } = useAuth();

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<NewUserForm>(emptyForm);
  const [createError, setCreateError] = useState("");

  useEffect(() => {
    if (!authLoading && !user) router.push("/login");
    if (!authLoading && user && user.role !== "admin") router.push("/");
  }, [user, authLoading, router]);

  const { data: users = [], isLoading } = useQuery<AdminUser[]>({
    queryKey: ["admin-users"],
    queryFn: () => api.get<AdminUser[]>("/admin/users"),
    enabled: !!user && user.role === "admin",
  });

  const createUser = useMutation({
    mutationFn: () => api.post<AdminUser>("/admin/users", form),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["admin-users"] });
      setShowForm(false);
      setForm(emptyForm);
      setCreateError("");
    },
    onError: (err: Error) => setCreateError(err.message),
  });

  const updateUser = useMutation({
    mutationFn: ({ id, ...body }: { id: string; role?: string; is_active?: boolean }) =>
      api.patch<AdminUser>(`/admin/users/${id}`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin-users"] }),
  });

  const deactivate = (u: AdminUser) => {
    if (!confirm(`¿Desactivar a ${u.full_name}? No podrá iniciar sesión.`)) return;
    updateUser.mutate({ id: u.id, is_active: false });
  };

  if (authLoading || isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-4xl mx-auto flex items-center gap-3">
          <Link href="/" className="text-gray-400 hover:text-gray-600">
            <ArrowLeft size={18} />
          </Link>
          <h1 className="text-lg font-semibold text-gray-900 flex-1">Administración de usuarios</h1>
          <Button size="sm" onClick={() => setShowForm((v) => !v)}>
            <Plus size={14} />
            Nuevo usuario
          </Button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8 space-y-6">
        {/* Form nuevo usuario */}
        {showForm && (
          <section className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
            <h2 className="text-sm font-semibold text-gray-800">Nuevo usuario</h2>
            <div className="grid grid-cols-2 gap-4">
              <Input
                label="Correo electrónico"
                type="email"
                value={form.email}
                onChange={(e) => setForm((p) => ({ ...p, email: e.target.value }))}
              />
              <Input
                label="Nombre completo"
                value={form.full_name}
                onChange={(e) => setForm((p) => ({ ...p, full_name: e.target.value }))}
              />
              <Input
                label="Contraseña"
                type="password"
                value={form.password}
                onChange={(e) => setForm((p) => ({ ...p, password: e.target.value }))}
              />
              <Select
                label="Rol"
                value={form.role}
                onChange={(e) => setForm((p) => ({ ...p, role: e.target.value as Role }))}
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </Select>
            </div>
            {createError && <Alert variant="error">{createError}</Alert>}
            <div className="flex gap-3">
              <Button onClick={() => createUser.mutate()} loading={createUser.isPending} size="sm">
                Crear usuario
              </Button>
              <Button variant="ghost" size="sm" onClick={() => { setShowForm(false); setCreateError(""); }}>
                Cancelar
              </Button>
            </div>
          </section>
        )}

        {/* Tabla de usuarios */}
        <section className="bg-white rounded-lg border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-xs text-gray-500 uppercase">
                <th className="px-4 py-3 text-left font-medium">Usuario</th>
                <th className="px-4 py-3 text-left font-medium">Rol</th>
                <th className="px-4 py-3 text-left font-medium">Estado</th>
                <th className="px-4 py-3 text-right font-medium">Acciones</th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id} className={`border-t border-gray-100 ${!u.is_active ? "opacity-50" : ""}`}>
                  <td className="px-4 py-3">
                    <p className="font-medium text-gray-900">{u.full_name}</p>
                    <p className="text-xs text-gray-400">{u.email}</p>
                  </td>
                  <td className="px-4 py-3">
                    <Select
                      value={u.role}
                      onChange={(e) => updateUser.mutate({ id: u.id, role: e.target.value })}
                      className="w-28 text-xs py-1"
                    >
                      {ROLES.map((r) => (
                        <option key={r} value={r}>{r}</option>
                      ))}
                    </Select>
                  </td>
                  <td className="px-4 py-3">
                    <Badge color={u.is_active ? "green" : "gray"}>
                      {u.is_active ? "Activo" : "Inactivo"}
                    </Badge>
                  </td>
                  <td className="px-4 py-3 text-right">
                    {u.is_active && u.id !== user?.id && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => deactivate(u)}
                        className="text-red-500 hover:text-red-700"
                      >
                        <UserX size={14} />
                      </Button>
                    )}
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-4 py-8 text-center text-gray-400">
                    No hay usuarios
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </section>
      </main>
    </div>
  );
}
