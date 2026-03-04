import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import type { StorefrontProduct } from "../../../types";
import { fetchStorefrontCategories, fetchStorefrontProducts } from "../../../services/storefront-api";
import type { CategoryItem } from "../types";

export function useStorefrontPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState("");
  const [categories, setCategories] = useState<CategoryItem[]>([]);
  const [products, setProducts] = useState<StorefrontProduct[]>([]);
  const [sortBy, setSortBy] = useState<"price" | "name">("price");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load(currentQuery?: string) {
    setLoading(true);
    setError("");
    try {
      const rawCategoryId = searchParams.get("category_id");
      const categoryId = rawCategoryId ? Number(rawCategoryId) : undefined;
      const payload = await fetchStorefrontProducts({
        q: currentQuery?.trim() || undefined,
        category_id: Number.isFinite(categoryId) ? categoryId : undefined
      });
      setProducts(payload.data);
    } catch {
      setError("No se pudo cargar el catalogo.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, [searchParams]);

  useEffect(() => {
    async function run() {
      try {
        const payload = await fetchStorefrontCategories();
        setCategories(payload.data);
      } catch {
        setCategories([]);
      }
    }
    void run();
  }, []);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void load(query);
  }

  const selectedCategoryId = Number(searchParams.get("category_id") || 0) || null;

  function onCategoryClick(categoryId: number | null) {
    const next = new URLSearchParams(searchParams);
    if (categoryId === null) {
      next.delete("category_id");
    } else {
      next.set("category_id", String(categoryId));
    }
    setSearchParams(next);
  }

  const sortedProducts = useMemo(() => {
    const rows = [...products];
    rows.sort((a, b) => {
      if (sortBy === "name") {
        const aName = (a.name || "").toLocaleLowerCase();
        const bName = (b.name || "").toLocaleLowerCase();
        if (aName < bName) return sortDir === "asc" ? -1 : 1;
        if (aName > bName) return sortDir === "asc" ? 1 : -1;
        return 0;
      }
      const aPrice = a.min_var_price ?? Number.MAX_SAFE_INTEGER;
      const bPrice = b.min_var_price ?? Number.MAX_SAFE_INTEGER;
      if (aPrice < bPrice) return sortDir === "asc" ? -1 : 1;
      if (aPrice > bPrice) return sortDir === "asc" ? 1 : -1;
      return 0;
    });
    return rows;
  }, [products, sortBy, sortDir]);

  return {
    query,
    setQuery,
    categories,
    sortBy,
    setSortBy,
    sortDir,
    setSortDir,
    loading,
    error,
    onSubmit,
    selectedCategoryId,
    onCategoryClick,
    sortedProducts
  };
}
