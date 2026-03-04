import { useEffect, useState } from "react";
import { listAdminTurns, updateAdminTurnStatus, type AdminTurn } from "../../../services/turns-api";
import type { AdminSection } from "../types";

export function useAdminTurns(adminSection: AdminSection) {
  const [turns, setTurns] = useState<AdminTurn[]>([]);
  const [turnsFilter, setTurnsFilter] = useState<"all" | "pending" | "confirmed" | "cancelled">("all");
  const [turnsError, setTurnsError] = useState("");

  async function loadTurns() {
    setTurnsError("");
    try {
      const rows = await listAdminTurns(turnsFilter === "all" ? undefined : turnsFilter);
      setTurns(rows);
    } catch {
      setTurnsError("No se pudieron cargar los turnos.");
    }
  }

  async function onUpdateTurnStatus(turnId: number, status: "confirmed" | "cancelled") {
    setTurnsError("");
    try {
      await updateAdminTurnStatus(turnId, status);
      await loadTurns();
    } catch {
      setTurnsError("No se pudo actualizar el estado del turno.");
    }
  }

  useEffect(() => {
    if (adminSection === "turnos") {
      void loadTurns();
    }
  }, [adminSection, turnsFilter]);

  return {
    turns,
    turnsFilter,
    setTurnsFilter,
    turnsError,
    loadTurns,
    onUpdateTurnStatus
  };
}
