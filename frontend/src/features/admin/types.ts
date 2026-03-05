export type AdminSection = "catalogo" | "descuentos" | "turnos" | "ordenes" | "pagos" | "registrar_venta" | "registrar_pago";

export type ManualOrderItem = {
  variant_id: number;
  quantity: number;
  label: string;
};

export type VariantOption = {
  value: string;
  label: string;
  priceCents?: number;
};
