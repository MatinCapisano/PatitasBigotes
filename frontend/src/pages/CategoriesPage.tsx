import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { fetchStorefrontCategories } from "../services/storefront-api";

type CategoryItem = {
  id: number;
  name: string;
};

export function CategoriesPage() {
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

  return (
    <section>
      <h1 className="page-title">Categorias</h1>
      <p className="page-subtitle">Elegi una categoria para explorar productos.</p>

      {loading && <p>Cargando...</p>}
      {error && <p className="error">{error}</p>}

      <div className="admin-grid">
        {categories.map((category) => (
          <article className="card" key={category.id}>
            <h2>{category.name}</h2>
            <p>Ver productos de esta categoria en la tienda.</p>
            <Link className="btn btn-small" to={`/?category_id=${category.id}`}>
              Ver en home
            </Link>
          </article>
        ))}
      </div>
    </section>
  );
}
