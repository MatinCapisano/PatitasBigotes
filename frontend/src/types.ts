export type StorefrontProduct = {
  id: number;
  name: string;
  description: string | null;
  img_url: string | null;
  category_id: number;
  category_name: string | null;
  min_var_price: number | null;
  in_stock: boolean;
};

export type StorefrontOption = {
  variant_id: number;
  label: string;
  size: string | null;
  color: string | null;
  img_url: string | null;
  effective_img_url?: string | null;
  price: number;
  in_stock: boolean;
};

export type StorefrontProductDetail = StorefrontProduct & {
  option_axis: "size" | "color" | "variant";
  options: StorefrontOption[];
};

export type ApiEnvelope<T> = {
  data: T;
  meta?: Record<string, unknown>;
};

export type LoginResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  access_expires_in_seconds: number;
  access_expires_in_minutes: number;
};
