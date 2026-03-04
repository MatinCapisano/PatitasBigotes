import { useEffect, useState } from "react";
import { fetchStorefrontCategories } from "../../../services/storefront-api";
import type { CategoryItem } from "../types";

export function useCategoriesPage() {
  const [categories, setCategories] = useState<CategoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    async function run() {
      setLoading(true);
      setError("");
      try {
        const payload = await fetchStorefrontCategories();
        setCategories(payload.data);
      } catch {
        setError("No se pudieron cargar las categorias.");
      } finally {
        setLoading(false);
      }
    }
    void run();
  }, []);

  return {
    categories,
    loading,
    error
  };
}
