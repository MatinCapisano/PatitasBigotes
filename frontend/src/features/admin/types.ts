export type AdminSection = "catalogo" | "descuentos" | "turnos" | "ordenes" | "pagos";

export type ManualOrderItem = {
  variant_id: number;
  quantity: number;
  label: string;
};

export type VariantOption = {
  value: string;
  label: string;
};
