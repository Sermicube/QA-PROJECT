"use client";
import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { api } from "@/lib/api/client";
import { useAuth } from "@/lib/hooks/useAuth";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Spinner } from "@/components/ui/Spinner";
import { Alert } from "@/components/ui/Alert";
import { ArrowLeft, Search, Trash2, Plus } from "lucide-react";

interface Term {
  name: string;
  definition: string;
  synonyms: string[];
}

interface QueryResult {
  results: Record<string, unknown>[];
}

export default function KnowledgePage() {
  const router = useRouter();
  const qc = useQueryClient();
  const { user, isLoading: authLoading } = useAuth();
  const [tab, setTab] = useState<"query" | "glossary">("query");

  useEffect(() => {
    if (!authLoading && !user) router.push("/login");
  }, [user, authLoading, router]);

  // ── Consulta al grafo ──────────────────────────────────────────────────────
  const [queryText, setQueryText] = useState("");
  const [moduleFilter, setModuleFilter] = useState("");
  const [queryResults, setQueryResults] = useState<Record<string, unknown>[] | null>(null);
  const [queryError, setQueryError] = useState("");

  const runQuery = useMutation({
    mutationFn: () =>
      api.post<QueryResult>("/knowledge/query", {
        text: queryText,
        module_filter: moduleFilter || null,
      }),
    onSuccess: (data) => {
      setQueryResults(data.results);
      setQueryError("");
    },
    onError: (err: Error) => setQueryError(err.message),
  });

  // ── Glosario ───────────────────────────────────────────────────────────────
  const { data: terms = [], isLoading: termsLoading } = useQuery<Term[]>({
    queryKey: ["glossary"],
    queryFn: () => api.get<Term[]>("/knowledge/glossary"),
    enabled: !!user,
  });

  const [showForm, setShowForm] = useState(false);
  const [termName, setTermName] = useState("");
  const [termDef, setTermDef] = useState("");
  const [termSyns, setTermSyns] = useState("");
  const [termError, setTermError] = useState("");

  const saveTerm = useMutation({
    mutationFn: () =>
      api.post<Term>("/knowledge/glossary", {
        name: termName,
        definition: termDef,
        synonyms: termSyns.split(",").map((s) => s.trim()).filter(Boolean),
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["glossary"] });
      setShowForm(false);
      setTermName("");
      setTermDef("");
      setTermSyns("");
      setTermError("");
    },
    onError: (err: Error) => setTermError(err.message),
  });

  const deleteTerm = useMutation({
    mutationFn: (name: string) =>
      api.delete(`/knowledge/glossary/${encodeURIComponent(name)}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["glossary"] }),
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
        <div className="max-w-5xl mx-auto flex items-center gap-3">
          <Link href="/" className="text-gray-400 hover:text-gray-600">
            <ArrowLeft size={18} />
          </Link>
          <h1 className="text-lg font-semibold text-gray-900">Mapa Vivo</h1>
        </div>
      </header>

      {/* Tabs */}
      <div className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-6 flex gap-0">
          {(["query", "glossary"] as const).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-4 py-3 text-sm font-medium border-b-2 transition-colors ${
                tab === t
                  ? "border-blue-600 text-blue-700"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {t === "query" ? "Consultar grafo" : "Glosario"}
            </button>
          ))}
        </div>
      </div>

      <main className="max-w-5xl mx-auto px-6 py-8">
        {/* ── Consulta al grafo ─────────────────────────────────────────────── */}
        {tab === "query" && (
          <div className="space-y-4">
            <p className="text-sm text-gray-500">
              Consulta el conocimiento acumulado de certificaciones anteriores en lenguaje natural.
            </p>
            <div className="flex gap-3">
              <div className="flex-1">
                <Input
                  label="Pregunta"
                  placeholder='Ej. "¿Qué reglas afectan la exclusión de beneficiario?"'
                  value={queryText}
                  onChange={(e) => setQueryText(e.target.value)}
                />
              </div>
              <div className="w-48">
                <Input
                  label="Módulo (opcional)"
                  placeholder="Afiliación"
                  value={moduleFilter}
                  onChange={(e) => setModuleFilter(e.target.value)}
                />
              </div>
            </div>
            <Button
              onClick={() => runQuery.mutate()}
              loading={runQuery.isPending}
              disabled={!queryText}
              size="sm"
            >
              <Search size={14} />
              Buscar en el grafo
            </Button>

            {queryError && <Alert variant="error">{queryError}</Alert>}

            {queryResults !== null && (
              queryResults.length === 0 ? (
                <p className="text-sm text-gray-400 py-4">Sin resultados.</p>
              ) : (
                <div className="bg-white rounded-lg border border-gray-200 overflow-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="bg-gray-50 text-xs text-gray-500 uppercase">
                        {Object.keys(queryResults[0]).map((k) => (
                          <th key={k} className="px-4 py-2 text-left font-medium">{k}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {queryResults.map((row, i) => (
                        <tr key={i} className="border-t border-gray-100">
                          {Object.values(row).map((v, j) => (
                            <td key={j} className="px-4 py-2 text-gray-700">
                              {String(v ?? "")}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )
            )}
          </div>
        )}

        {/* ── Glosario ─────────────────────────────────────────────────────── */}
        {tab === "glossary" && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="text-sm text-gray-500">
                Términos canónicos del dominio. El linter los usa para detectar terminología inconsistente (L09).
              </p>
              <Button size="sm" onClick={() => setShowForm(!showForm)}>
                <Plus size={14} />
                Agregar término
              </Button>
            </div>

            {showForm && (
              <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-3">
                <p className="text-sm font-medium text-gray-700">Nuevo término</p>
                <Input
                  label="Nombre canónico"
                  placeholder="exclusión"
                  value={termName}
                  onChange={(e) => setTermName(e.target.value)}
                />
                <Input
                  label="Definición"
                  placeholder="Exclusión de un beneficiario del contrato de salud"
                  value={termDef}
                  onChange={(e) => setTermDef(e.target.value)}
                />
                <Input
                  label="Sinónimos (separados por coma)"
                  placeholder="desvinculación, baja, retiro"
                  value={termSyns}
                  onChange={(e) => setTermSyns(e.target.value)}
                />
                {termError && <Alert variant="error">{termError}</Alert>}
                <div className="flex gap-2">
                  <Button size="sm" onClick={() => saveTerm.mutate()} loading={saveTerm.isPending} disabled={!termName}>
                    Guardar
                  </Button>
                  <Button size="sm" variant="ghost" onClick={() => setShowForm(false)}>
                    Cancelar
                  </Button>
                </div>
              </div>
            )}

            {termsLoading ? (
              <Spinner size="sm" />
            ) : terms.length === 0 ? (
              <p className="text-sm text-gray-400 py-8 text-center">No hay términos en el glosario.</p>
            ) : (
              <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-gray-50 text-xs text-gray-500 uppercase">
                      <th className="px-4 py-2 text-left font-medium">Término</th>
                      <th className="px-4 py-2 text-left font-medium">Definición</th>
                      <th className="px-4 py-2 text-left font-medium">Sinónimos</th>
                      <th className="px-4 py-2"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {terms.map((t) => (
                      <tr key={t.name} className="border-t border-gray-100 hover:bg-gray-50">
                        <td className="px-4 py-2 font-medium text-gray-800">{t.name}</td>
                        <td className="px-4 py-2 text-gray-600">{t.definition}</td>
                        <td className="px-4 py-2 text-gray-500">{t.synonyms.join(", ")}</td>
                        <td className="px-4 py-2 text-right">
                          <button
                            onClick={() => deleteTerm.mutate(t.name)}
                            className="text-gray-400 hover:text-red-500 transition-colors"
                          >
                            <Trash2 size={14} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
