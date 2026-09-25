"use client";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useAuth } from "@/lib/hooks/useAuth";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";

const schema = z.object({
  email: z.string().email("Correo inválido"),
  password: z.string().min(1, "Contraseña requerida"),
});

type FormData = z.infer<typeof schema>;

export default function LoginPage() {
  const { login, loginError, isLoading } = useAuth();
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: FormData) => {
    await login(data).catch(() => {});
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="bg-white rounded-xl shadow-lg border border-gray-200 w-full max-w-sm p-8">
        <div className="mb-8 text-center">
          <h1 className="text-2xl font-bold text-gray-900">Copiloto QA</h1>
          <p className="text-sm text-gray-500 mt-1">Beyond Health — Certificación</p>
        </div>

        {loginError && (
          <Alert variant="error" className="mb-4">
            Credenciales inválidas. Verificar correo y contraseña.
          </Alert>
        )}

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <Input
            label="Correo electrónico"
            type="email"
            placeholder="analista@sonda.com"
            error={errors.email?.message}
            {...register("email")}
          />
          <Input
            label="Contraseña"
            type="password"
            placeholder="••••••••"
            error={errors.password?.message}
            {...register("password")}
          />
          <Button type="submit" loading={isSubmitting || isLoading} className="w-full">
            Iniciar sesión
          </Button>
        </form>
      </div>
    </div>
  );
}
