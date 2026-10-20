"use client";
import { useEffect } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api/client";
import type { Certification, Recipe } from "@/lib/api/types";
import { Input } from "@/components/ui/Input";
import { Textarea } from "@/components/ui/Textarea";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Spinner } from "@/components/ui/Spinner";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

const STAGE_ORDER = [
  "context", "testcases", "format", "data_request", "assignment",
  "execution", "analysis", "documentation", "review", "closed",
] as const;

const STAGE_LABELS: Record<string, string> = {
  context: "Contexto", testcases: "Casos", format: "Formato",
  data_request: "Solicitud", assignment: "Asignación", execution: "Ejecución",
  analysis: "Análisis", documentation: "Documentación", review: "Revisión",
  closed: "Cerrada",
};

const DATA_ORIGIN_OPTIONS: { value: string; label: string }[] = [
  { value: "developer_case", label: "Caso del desarrollador" },
  { value: "colleague_request", label: "Solicitud a colega" },
  { value: "factory_request", label: "Solicitud a fábrica" },
  { value: "manual_search", label: "Búsqueda manual" },
  { value: "client_file", label: "Archivo del cliente" },
  { value: "created_records", label: "Registros creados por el analista" },
  { value: "report_search", label: "Búsqueda en reporte" },
];

// Recipes applicable per type (bug-only, brecha-only, both)
const BUG_ONLY_RECIPES = new Set(["bug_simple", "bug_before_after", "bug_negative_control"]);
const BRECHA_ONLY_RECIPES = new Set(["brecha_date_rule"]);

function recipeFitsType(code: string, type: "bug" | "brecha"): boolean {
  if (type === "bug") return !BRECHA_ONLY_RECIPES.has(code);
  if (type === "brecha") return !BUG_ONLY_RECIPES.has(code);
  return true;
}

function defaultRecipeForType(type: "bug" | "brecha"): string {
  return type === "brecha" ? "brecha_date_rule" : "bug_simple";
}

const schema = z.object({
  type: z.enum(["bug", "brecha"]),
  external_code: z.string().min(1, "Requerido"),
  module: z.string().min(1, "Requerido"),
  title: z.string().min(3, "Mínimo 3 caracteres"),
  description: z.string().optional(),
  recipe_code: z.string().min(1, "Selecciona una receta"),
  data_origin: z.string().min(1, "Requerido"),
});

type FormData = z.infer<typeof schema>;

function RecipeStagesBadges({ stages }: { stages: Record<string, string> }) {
  const active = STAGE_ORDER.filter(
    (s) => s !== "closed" && (stages[s] === "required" || stages[s] === "optional")
  );
  return (
    <div className="flex flex-wrap gap-1 mt-2">
      {active.map((s) => (
        <span
          key={s}
          className={`text-xs px-1.5 py-0.5 rounded-full ${
            stages[s] === "required"
              ? "bg-blue-100 text-blue-700"
              : "bg-gray-100 text-gray-500"
          }`}
        >
          {STAGE_LABELS[s] ?? s}
          {stages[s] === "optional" && " (opc)"}
        </span>
      ))}
    </div>
  );
}

export default function NewCertificationPage() {
  const router = useRouter();
  const qc = useQueryClient();

  const { data: recipes, isLoading: recipesLoading } = useQuery<Recipe[]>({
    queryKey: ["recipes"],
    queryFn: () => api.get<Recipe[]>("/recipes"),
  });

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      type: "bug",
      recipe_code: "bug_simple",
      data_origin: "developer_case",
    },
  });

  const selectedType = watch("type");
  const selectedCode = watch("recipe_code");

  const filteredRecipes = (recipes ?? []).filter((r) =>
    recipeFitsType(r.code, selectedType)
  );

  const selectedRecipe = filteredRecipes.find((r) => r.code === selectedCode);

  // When type changes: reset recipe to the right default, then set data_origin from it
  useEffect(() => {
    const newRecipe = defaultRecipeForType(selectedType);
    setValue("recipe_code", newRecipe);
  }, [selectedType, setValue]);

  // When recipe changes: update data_origin default
  useEffect(() => {
    if (selectedRecipe) {
      setValue("data_origin", selectedRecipe.default_data_origin);
    }
  }, [selectedCode, selectedRecipe, setValue]);

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
              Error al crear la certificación. Verifica los datos.
            </Alert>
          )}

          <form onSubmit={handleSubmit((d) => create.mutate(d))} className="space-y-5">
            {/* Tipo */}
            <div>
              <span className="block text-sm font-medium text-gray-700 mb-2">Tipo</span>
              <div className="flex gap-6">
                {(["bug", "brecha"] as const).map((t) => (
                  <label key={t} className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="radio"
                      name="type"
                      value={t}
                      checked={selectedType === t}
                      onChange={() => setValue("type", t)}
                      className="text-blue-600"
                    />
                    <span className="text-sm text-gray-700 capitalize">{t}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Selector de receta */}
            <div>
              <span className="block text-sm font-medium text-gray-700 mb-2">
                Receta de certificación
              </span>
              {recipesLoading ? (
                <div className="flex items-center gap-2 text-sm text-gray-500">
                  <Spinner size="sm" /> Cargando recetas…
                </div>
              ) : (
                <div className="space-y-2">
                  {filteredRecipes.map((recipe) => {
                    const isSelected = selectedCode === recipe.code;
                    return (
                      <label
                        key={recipe.code}
                        className={`flex items-start gap-3 p-3 rounded-lg border-2 cursor-pointer transition-colors ${
                          isSelected
                            ? "border-blue-500 bg-blue-50"
                            : "border-gray-200 hover:border-gray-300"
                        }`}
                      >
                        <input
                          type="radio"
                          name="recipe_code"
                          value={recipe.code}
                          checked={isSelected}
                          onChange={() =>
                            setValue("recipe_code", recipe.code, { shouldValidate: true })
                          }
                          className="mt-0.5 text-blue-600 shrink-0"
                        />
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-medium text-gray-900">{recipe.name}</div>
                          {recipe.description && (
                            <div className="text-xs text-gray-500 mt-0.5">{recipe.description}</div>
                          )}
                          <RecipeStagesBadges stages={recipe.stages} />
                        </div>
                      </label>
                    );
                  })}
                </div>
              )}
              {errors.recipe_code && (
                <p className="mt-1 text-xs text-red-600">{errors.recipe_code.message}</p>
              )}
            </div>

            {/* Origen de datos */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Origen de datos de prueba
              </label>
              <select
                {...register("data_origin")}
                className="w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                {DATA_ORIGIN_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
              {errors.data_origin && (
                <p className="mt-1 text-xs text-red-600">{errors.data_origin.message}</p>
              )}
            </div>

            <Input
              label="Código externo"
              placeholder="IM-9142664 / TFS-173200"
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
              <Button type="submit" loading={isSubmitting || create.isPending}>
                Crear certificación
              </Button>
            </div>
          </form>
        </div>
      </main>
    </div>
  );
}
