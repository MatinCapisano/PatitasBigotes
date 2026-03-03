import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import type { StorefrontProductDetail } from "../types";
import { fetchStorefrontProductById } from "../services/storefront-api";

function formatArs(cents: number) {
  return new Intl.NumberFormat("es-AR", {
    style: "currency",
    currency: "ARS",
    maximumFractionDigits: 0
  }).format(cents / 100);
}

export function ProductDetailPage() {
  const params = useParams();
  const [product, setProduct] = useState<StorefrontProductDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedVariantId, setSelectedVariantId] = useState<number | null>(null);

  useEffect(() => {
    async function run() {
      setLoading(true);
      setError("");
      try {
        const id = Number(params.productId);
        const payload = await fetchStorefrontProductById(id);
        setProduct(payload.data);
        setSelectedVariantId(payload.data.options[0]?.variant_id ?? null);
      } catch {
        setError("No se pudo cargar el producto.");
      } finally {
        setLoading(false);
      }
    }
    void run();
  }, [params.productId]);

  if (loading) return <p>Cargando...</p>;
  if (error) return <p className="error">{error}</p>;
  if (!product) return <p>No encontrado.</p>;

  const selectedOption =
    product.options.find((option) => option.variant_id === selectedVariantId) ?? product.options[0];
  const currentImageUrl =
    selectedOption?.effective_img_url ?? selectedOption?.img_url ?? product.img_url ?? null;

  return (
    <section>
      <Link className="link-back" to="/">
        Volver al catalogo
      </Link>
      <h1 className="page-title">{product.name}</h1>
      <p className="page-subtitle">{product.description ?? "Sin descripcion"}</p>
      {currentImageUrl ? (
        <img className="product-image product-image-detail" src={currentImageUrl} alt={product.name} />
      ) : (
        <div className="image-placeholder image-placeholder-detail">Sin imagen</div>
      )}
      {!product.in_stock && <p className="warning">Este producto no tiene stock disponible.</p>}

      <h2 className="section-title">Opciones ({product.option_axis})</h2>
      <div className="options-grid">
        {product.options.map((option) => (
          <button
            key={option.variant_id}
            className={`chip ${option.in_stock ? "" : "chip-disabled"} ${
              selectedVariantId === option.variant_id ? "chip-selected" : ""
            }`}
            type="button"
            disabled={!option.in_stock}
            onClick={() => setSelectedVariantId(option.variant_id)}
          >
            <span>{option.label}</span>
            <strong>{formatArs(option.price)}</strong>
          </button>
        ))}
      </div>
    </section>
  );
}
