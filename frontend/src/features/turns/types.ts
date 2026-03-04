export const DAYS = [
  "Lunes",
  "Martes",
  "Miercoles",
  "Jueves",
  "Viernes",
  "Sabados (10am a 2pm y 4pm a 8pm)"
] as const;

export const DOG_SIZES = ["Pequeno", "Mediano", "Grande"] as const;

export type TurnDay = (typeof DAYS)[number];
export type DogSize = (typeof DOG_SIZES)[number];
