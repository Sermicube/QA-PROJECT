"use client";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import type { Certification } from "@/lib/api/types";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

const schema = z.object({
  type: z.enum(["bug", "brecha"]),
  external_code: z.string().min(1, "Requerido"),
  module: z.string().min(1, "Requerido"),
  title: z.string().min(3, "Mínimo 3 caracteres"),
  description: z.string().optional(),
});

type FormData = z.infer<typeof schema>;

export default function NewCertificationPage() {
  const router = useRouter();
  const qc = useQueryClient();

  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { type: "bug" },
  });

  const create = useMutation({
    mutationFn: (data: FormData) => api.post<Certification>("/certifications", data),
    onSuccess: (cert) => {
      qc.invalidateQueries({ queryKey: ["certifications"] });
      router.push(`/certifications/${cert.id}`);
    },
  });

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-2xl mx-auto flex items-center gap-3">
          <Link href="/" className="text-gray-400 hover:text-gray-600">
            <ArrowLeft size={20} />
          </Link>
          <h1 className="text-lg font-semibold text-gray-900">Nueva certificación</h1>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-6 py-8">
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          {create.error && (
            <Alert variant="error" className="mb-4">
              Error al crear la certificación. Verificar los datos.
            </Alert>
          )}

          <form onSubmit={handleSubmit((d) => create.mutate(d))} className="space-y-5">
            <div>
              <span className="block text-sm font-medium text-gray-700 mb-2">Tipo</span>
              <div className="flex gap-6">
                {(["bug", "brecha"] as const).map((t) => (
                  <label key={t} className="flex items-center gap-2 cursor-pointer">
                    <input type="radio" value={t} {...register("type")} className="text-blue-600" />
                    <span className="text-sm text-gray-700 capitalize">{t}</span>
                  </label>
                ))}
              </div>
            </div>

            <Input
              label="Código externo"
              placeholder="IM-9142664"
              error={errors.external_code?.message}
              {...register("external_code")}
            />

            <Input
              label="Módulo de Beyond Health"
              placeholder="Novedades de afiliación"
              error={errors.module?.message}
              {...register("module")}
            />

            <Input
              label="Título"
              placeholder="Descripción corta de la certificación"
              error={errors.title?.message}
              {...register("title")}
            />

            <Textarea
              label="Descripción (opcional)"
              placeholder="Contexto adicional..."
              rows={3}
              {...register("description")}
            />

            <div className="flex gap-3 pt-2">
              <Link href="/">
                <Button variant="secondary">Cancelar</Button>
              </Link>
              <Button type="submit" loading={isSubmitting}>Crear certificación</Button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}
