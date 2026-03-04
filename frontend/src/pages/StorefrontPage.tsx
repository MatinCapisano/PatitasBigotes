import { FormEvent, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useSearchParams } from "react-router-dom";
import type { StorefrontProduct } from "../types";
import { fetchStorefrontCategories, fetchStorefrontProducts } from "../services/storefront-api";

function formatArs(cents: number | null) {
  if (cents === null) return "-";
  return new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    maximumFractionDigits: 0
  }).format(cents / 100);
}

export function StorefrontPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState("");
  const [categories, setCategories] = useState<Array<{ id: number; name: string }>>([]);
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

  return (
    <section>
      <h1 className="page-title">Catalogo</h1>
      <p className="page-subtitle">Productos disponibles para mascotas.</p>

      <div className="categories-inline">
        <button
          type="button"
          className={selectedCategoryId === null ? "chip chip-selected" : "chip"}
          onClick={() => onCategoryClick(null)}
        >
          Todas
        </button>
        {categories.map((category) => (
          <button
            key={category.id}
            type="button"
            className={selectedCategoryId === category.id ? "chip chip-selected" : "chip"}
            onClick={() => onCategoryClick(category.id)}
          >
            {category.name}
          </button>
        ))}
      </div>

      <form className="search-row" onSubmit={onSubmit}>
        <input
          className="input"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Buscar por nombre..."
        />
        <button className="btn" type="submit">
          Buscar
        </button>
      </form>

      <div className="search-row">
        <label>
          Ordenar por
          <select className="input" value={sortBy} onChange={(event) => setSortBy(event.target.value as "price" | "name")}>
            <option value="price">Precio</option>
            <option value="name">Alfabetico</option>
          </select>
        </label>
        <label>
          Direccion
          <select className="input" value={sortDir} onChange={(event) => setSortDir(event.target.value as "asc" | "desc")}>
            <option value="asc">Ascendente</option>
            <option value="desc">Descendente</option>
          </select>
        </label>
      </div>

      {loading && <p>Cargando...</p>}
      {error && <p className="error">{error}</p>}

      <div className="products-grid">
        {sortedProducts.map((product) => (
          <article className="card" key={product.id}>
            {product.img_url ? (
              <img className="product-image" src={product.img_url} alt={product.name} />
            ) : (
              <div className="image-placeholder">Sin imagen</div>
            )}
            <p className="category">{product.category_name ?? "Sin categoria"}</p>
            <h2>{product.name}</h2>
            <p>{product.description ?? "Sin descripcion"}</p>
            <p className="price">{formatArs(product.min_var_price)}</p>
            {!product.in_stock && <p className="warning">Sin stock por ahora</p>}
            <Link className="btn btn-small" to={`/products/${product.id}`}>
              Ver detalle
            </Link>
          </article>
        ))}
      </div>
    </section>
  );
}
