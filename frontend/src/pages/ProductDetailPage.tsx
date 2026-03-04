import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { addToCart } from "../lib/cart-storage";
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
  const navigate = useNavigate();
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

  function onBuy() {
    if (!product) return;
    if (!selectedOption || !selectedOption.in_stock) return;
    addToCart({
      product_id: product.id,
      product_name: product.name,
      variant_id: selectedOption.variant_id,
      option_label: selectedOption.label,
      unit_price: selectedOption.price,
      quantity: 1,
      img_url: selectedOption.effective_img_url ?? selectedOption.img_url ?? product.img_url
    });
    const goCheckout = window.confirm(
      "Producto agregado al carrito.\nAceptar: Finalizar compra\nCancelar: Seguir comprando"
    );
    if (goCheckout) {
      navigate("/checkout");
      return;
    }
    navigate("/home");
  }

  return (
    <section>
      <Link className="link-back" to="/home">
        Volver al catalogo
      </Link>

      <div className="product-detail-layout">
        <div>
          {currentImageUrl ? (
            <img className="product-image product-image-detail" src={currentImageUrl} alt={product.name} />
          ) : (
            <div className="image-placeholder image-placeholder-detail">Sin imagen</div>
          )}
        </div>

        <div>
          <h1 className="page-title">{product.name}</h1>
          <p className="page-subtitle">{product.description ?? "Sin descripcion"}</p>
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
                {option.has_discount && option.price_original !== undefined ? (
                  <span className="detail-option-price">
                    <span className="price-original">{formatArs(option.price_original)}</span>
                    <strong className="price-final">{formatArs(option.price_final ?? option.price)}</strong>
                  </span>
                ) : (
                  <strong>{formatArs(option.price_final ?? option.price)}</strong>
                )}
              </button>
            ))}
          </div>

          <div className="detail-actions">
            <button className="btn" type="button" disabled={!selectedOption?.in_stock} onClick={onBuy}>
              Comprar
            </button>
          </div>
        </div>
      </div>

      <div className="product-payment-note">
        Metodos de pago: Transferencia bancaria, MercadoPago y Efectivo.
      </div>
    </section>
  );
}
