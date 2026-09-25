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
import { ArrowLeft, Trash2, KeyRound } from "lucide-react";

const LLM_PROVIDERS = [
  { value: "anthropic", label: "Anthropic (Claude)" },
  { value: "ollama", label: "Ollama (local)" },
];

interface LlmConfigOut {
  provider: string;
  model: string | null;
  base_url: string | null;
  key_hint: string;
}

export default function SettingsPage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { user, isLoading: authLoading } = useAuth();

  // ── Perfil ──────────────────────────────────────────────────────────────────
  const [fullName, setFullName] = useState("");
  const [nameSaved, setNameSaved] = useState(false);

  useEffect(() => {
    if (!authLoading && !user) router.push("/login");
    if (user) setFullName(user.full_name ?? "");
  }, [user, authLoading, router]);

  const updateProfile = useMutation({
    mutationFn: () => api.patch<User>("/auth/me", { full_name: fullName }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["me"] });
      setNameSaved(true);
      setTimeout(() => setNameSaved(false), 3000);
    },
  });

  // ── Configuración de IA por usuario ────────────────────────────────────────
  const [provider, setProvider] = useState("anthropic");
  const [apiKey, setApiKey] = useState("");
  const [model, setModel] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [llmError, setLlmError] = useState("");
  const [llmSaved, setLlmSaved] = useState(false);

  const { data: llmConfigs = [], isLoading: llmLoading } = useQuery<LlmConfigOut[]>({
    queryKey: ["llm-config"],
    queryFn: () => api.get<LlmConfigOut[]>("/auth/me/llm-config"),
    enabled: !!user,
  });

  const saveLlm = useMutation({
    mutationFn: () =>
      api.put<LlmConfigOut>("/auth/me/llm-config", {
        provider,
        api_key: apiKey,
        model: model || null,
        base_url: baseUrl || null,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["llm-config"] });
      setApiKey("");
      setLlmError("");
      setLlmSaved(true);
      setTimeout(() => setLlmSaved(false), 3000);
    },
    onError: (err: Error) => setLlmError(err.message),
  });

  const deleteLlm = useMutation({
    mutationFn: (prov: string) =>
      api.delete(`/auth/me/llm-config/${encodeURIComponent(prov)}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["llm-config"] }),
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
        {/* ── Perfil ─────────────────────────────────────────────────────────── */}
        <section className="bg-white rounded-lg border border-gray-200 p-6 space-y-4">
          <h2 className="text-sm font-semibold text-gray-800">Perfil</h2>
          <Input
            label="Nombre completo"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
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
        </section>

        {/* ── API Keys de IA ─────────────────────────────────────────────────── */}
        <section className="bg-white rounded-lg border border-gray-200 p-6 space-y-5">
          <div>
            <h2 className="text-sm font-semibold text-gray-800">API key del proveedor de IA</h2>
            <p className="text-xs text-gray-500 mt-1">
              Tu clave se cifra antes de guardarse. Nunca se envía a modelos de IA ni se muestra completa.
            </p>
          </div>

          {/* Claves guardadas */}
          {llmLoading ? (
            <Spinner size="sm" />
          ) : llmConfigs.length > 0 ? (
            <ul className="space-y-2">
              {llmConfigs.map((cfg) => (
                <li
                  key={cfg.provider}
                  className="flex items-center justify-between rounded border border-gray-100 bg-gray-50 px-3 py-2 text-sm"
                >
                  <div className="flex items-center gap-2 text-gray-700">
                    <KeyRound size={14} className="text-gray-400" />
                    <span className="font-medium">{cfg.provider}</span>
                    {cfg.model && (
                      <span className="text-gray-400">· {cfg.model}</span>
                    )}
                    <span className="font-mono text-gray-400">{cfg.key_hint}</span>
                  </div>
                  <button
                    onClick={() => deleteLlm.mutate(cfg.provider)}
                    className="text-gray-400 hover:text-red-500 transition-colors"
                    title="Eliminar clave"
                  >
                    <Trash2 size={14} />
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-xs text-gray-400">No hay claves configuradas.</p>
          )}

          {/* Formulario para agregar / actualizar clave */}
          <div className="space-y-3 pt-2 border-t border-gray-100">
            <p className="text-xs font-medium text-gray-600">
              Agregar o reemplazar clave
            </p>
            <Select
              label="Proveedor"
              value={provider}
              onChange={(e) => setProvider(e.target.value)}
            >
              {LLM_PROVIDERS.map((p) => (
                <option key={p.value} value={p.value}>{p.label}</option>
              ))}
            </Select>
            <Input
              label="API key"
              type="password"
              placeholder="sk-ant-..."
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              helper="Solo ingresas la clave al guardar. No se almacena en texto plano."
            />
            <Input
              label="Modelo (opcional)"
              placeholder={provider === "anthropic" ? "claude-sonnet-4-6" : "llama3.2"}
              value={model}
              onChange={(e) => setModel(e.target.value)}
            />
            {provider === "ollama" && (
              <Input
                label="URL base de Ollama"
                placeholder="http://localhost:11434"
                value={baseUrl}
                onChange={(e) => setBaseUrl(e.target.value)}
              />
            )}
            {llmError && <Alert variant="error">{llmError}</Alert>}
            {llmSaved && <Alert variant="info">Clave guardada correctamente</Alert>}
            <Button
              onClick={() => saveLlm.mutate()}
              loading={saveLlm.isPending}
              disabled={!apiKey}
              size="sm"
            >
              Guardar clave
            </Button>
          </div>
        </section>
      </main>
    </div>
  );
}
