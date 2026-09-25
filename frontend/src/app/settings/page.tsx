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
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import { ArrowLeft } from "lucide-react";

const LLM_PROVIDERS = [
  { value: "anthropic", label: "Anthropic (Claude)" },
  { value: "ollama", label: "Ollama (local)" },
];

interface LLMConfig {
  provider: string;
  model: string;
}

export default function SettingsPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { user, isLoading: authLoading } = useAuth();

  const [fullName, setFullName] = useState("");
  const [module, setModule] = useState("");
  const [nameSaved, setNameSaved] = useState(false);

  const [llmProvider, setLlmProvider] = useState("anthropic");
  const [llmModel, setLlmModel] = useState("");
  const [llmSaved, setLlmSaved] = useState(false);

  useEffect(() => {
    if (!authLoading && !user) router.push("/login");
    if (user) {
      setFullName(user.full_name ?? "");
      setModule(user.module ?? "");
    }
  }, [user, authLoading, router]);

  const { data: llmConfig } = useQuery<LLMConfig>({
    queryKey: ["llm-config"],
    queryFn: () => api.get<LLMConfig>("/settings/llm"),
    enabled: !!user,
  });

  useEffect(() => {
    if (llmConfig) {
      setLlmProvider(llmConfig.provider);
      setLlmModel(llmConfig.model);
    }
  }, [llmConfig]);

  const updateProfile = useMutation({
    mutationFn: () => api.patch<User>("/users/me", { full_name: fullName, module }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["me"] });
      setNameSaved(true);
      setTimeout(() => setNameSaved(false), 3000);
    },
  });

  const updateLLM = useMutation({
    mutationFn: () => api.put("/settings/llm", { provider: llmProvider, model: llmModel }),
    onSuccess: () => {
      setLlmSaved(true);
      setTimeout(() => setLlmSaved(false), 3000);
    },
  });

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Spinner size="lg" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="max-w-2xl mx-auto flex items-center gap-3">
          <Link href="/" className="text-gray-400 hover:text-gray-600">
            <ArrowLeft size={18} />
          </Link>
          <h1 className="text-lg font-semibold text-gray-900">Configuración</h1>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-6 py-8 space-y-6">
        {/* Profile */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-sm font-semibold text-gray-800 mb-4">Perfil</h2>
          <div className="space-y-4">
            <Input
              label="Nombre completo"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
            <Input
              label="Módulo principal"
              placeholder="Ej. Novedades de afiliación"
              value={module}
              onChange={(e) => setModule(e.target.value)}
            />
            {user && (
              <Input
                label="Correo electrónico"
                value={user.email}
                disabled
                helper="El correo no se puede modificar"
              />
            )}
            {nameSaved && <Alert variant="info">Perfil guardado</Alert>}
            <Button
              onClick={() => updateProfile.mutate()}
              loading={updateProfile.isPending}
              size="sm"
            >
              Guardar perfil
            </Button>
          </div>
        </div>

        {/* LLM */}
        <div className="bg-white rounded-lg border border-gray-200 p-6">
          <h2 className="text-sm font-semibold text-gray-800 mb-1">Proveedor de IA</h2>
          <p className="text-xs text-gray-500 mb-4">
            El proveedor se puede cambiar sin reiniciar. La API key debe estar en las variables de entorno del servidor.
          </p>
          <div className="space-y-4">
            <Select
              label="Proveedor"
              value={llmProvider}
              onChange={(e) => setLlmProvider(e.target.value)}
            >
              {LLM_PROVIDERS.map((p) => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </Select>
            <Input
              label="Modelo"
              placeholder={llmProvider === "anthropic" ? "claude-sonnet-4-6" : "llama3.2"}
              value={llmModel}
              onChange={(e) => setLlmModel(e.target.value)}
            />
            {llmSaved && <Alert variant="info">Configuración de IA guardada</Alert>}
            <Button
              onClick={() => updateLLM.mutate()}
              loading={updateLLM.isPending}
              size="sm"
            >
              Guardar configuración de IA
            </Button>
          </div>
        </div>
      </main>
    </div>
  );
}
