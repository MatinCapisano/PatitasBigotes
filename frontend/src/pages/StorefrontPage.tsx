import { Link } from "react-router-dom";
import { formatArs, useStorefrontPage } from "../features/storefront";

export function StorefrontPage() {
  const storefront = useStorefrontPage();

  return (
    <section>
      <h1 className="page-title">Catalogo</h1>
      <p className="page-subtitle">Productos disponibles para mascotas.</p>

      <div className="categories-inline">
        <button
          type="button"
          className={storefront.selectedCategoryId === null ? "chip chip-selected" : "chip"}
          onClick={() => storefront.onCategoryClick(null)}
        >
          Todas
        </button>
        {storefront.categories.map((category) => (
          <button
            key={category.id}
            type="button"
            className={storefront.selectedCategoryId === category.id ? "chip chip-selected" : "chip"}
            onClick={() => storefront.onCategoryClick(category.id)}
          >
            {category.name}
          </button>
        ))}
      </div>

      <form className="search-row" onSubmit={storefront.onSubmit}>
        <input
          className="input"
          value={storefront.query}
          onChange={(event) => storefront.setQuery(event.target.value)}
          placeholder="Buscar por nombre..."
        />
        <button className="btn" type="submit">
          Buscar
        </button>
      </form>

      <div className="search-row">
        <label>
          Ordenar por
          <select className="input" value={storefront.sortBy} onChange={(event) => storefront.setSortBy(event.target.value as "price" | "name")}>
            <option value="price">Precio</option>
            <option value="name">Alfabetico</option>
          </select>
        </label>
        <label>
          Direccion
          <select className="input" value={storefront.sortDir} onChange={(event) => storefront.setSortDir(event.target.value as "asc" | "desc")}>
            <option value="asc">Ascendente</option>
            <option value="desc">Descendente</option>
          </select>
        </label>
      </div>

      {storefront.loading && <p>Cargando...</p>}
      {storefront.error && <p className="error">{storefront.error}</p>}

      <div className="products-grid">
        {storefront.sortedProducts.map((product) => (
          <article className="card" key={product.id}>
            {product.img_url ? (
              <img className="product-image" src={product.img_url} alt={product.name} />
            ) : (
              <div className="image-placeholder">Sin imagen</div>
            )}
            <p className="category">{product.category_name ?? "Sin categoria"}</p>
            <h2>{product.name}</h2>
            <p>{product.description ?? "Sin descripcion"}</p>
            {product.has_discount && product.min_var_price_original !== null && product.min_var_price_original !== undefined ? (
              <p className="price">
                <span className="price-original">{formatArs(product.min_var_price_original)}</span>{" "}
                <span className="price-final">{formatArs(product.min_var_price_final ?? product.min_var_price)}</span>
              </p>
            ) : (
              <p className="price">{formatArs(product.min_var_price_final ?? product.min_var_price)}</p>
            )}
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
