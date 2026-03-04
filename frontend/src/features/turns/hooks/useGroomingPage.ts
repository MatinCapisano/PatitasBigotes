import { useState, type FormEvent } from "react";
import { createTurnRequest } from "../../../services/turns-api";
import { toUserMessage } from "../../../services/http-errors";
import { DAYS, DOG_SIZES, type DogSize, type TurnDay } from "../types";

export function useGroomingPage(params: { authLoading: boolean; isAuthenticated: boolean }) {
  const { authLoading, isAuthenticated } = params;
  const [day, setDay] = useState<TurnDay>(DAYS[0]);
  const [dogSize, setDogSize] = useState<DogSize>(DOG_SIZES[1]);
  const [hourText, setHourText] = useState("");
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState("");
  const [error, setError] = useState("");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (authLoading || !isAuthenticated) return;
    setLoading(true);
    setError("");
    setSuccess("");
    try {
      const notes = `Solicitud de peluqueria canina. Tamano perro: ${dogSize}. Dia: ${day}. Horario propuesto: ${hourText.trim()}.`;
      await createTurnRequest({
        scheduled_at: null,
        notes
      });
      setSuccess("Turno solicitado. Te confirmamos por WhatsApp.");
      setHourText("");
    } catch (apiError: unknown) {
      setError(toUserMessage(apiError, "turns"));
    } finally {
      setLoading(false);
    }
  }

  return {
    day,
    setDay,
    dogSize,
    setDogSize,
    hourText,
    setHourText,
    loading,
    success,
    error,
    onSubmit
  };
}
