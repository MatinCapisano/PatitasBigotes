import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import type { StorefrontProduct } from "../types";
import { fetchStorefrontProducts } from "../services/storefront-api";

function formatArs(cents: number | null) {
  if (cents === null) return "-";
  return new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    maximumFractionDigits: 0
  }).format(cents / 100);
}

export function StorefrontPage() {
  const [query, setQuery] = useState("");
  const [products, setProducts] = useState<StorefrontProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function load(currentQuery?: string) {
    setLoading(true);
    setError("");
    try {
      const payload = await fetchStorefrontProducts({
        q: currentQuery?.trim() || undefined
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
  }, []);

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    void load(query);
  }

  return (
    <section>
      <h1 className="page-title">Catalogo</h1>
      <p className="page-subtitle">Productos disponibles para mascotas.</p>

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

      {loading && <p>Cargando...</p>}
      {error && <p className="error">{error}</p>}

      <div className="products-grid">
        {products.map((product) => (
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
