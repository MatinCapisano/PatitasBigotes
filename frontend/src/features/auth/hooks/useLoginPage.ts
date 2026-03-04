import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { toUserMessage } from "../../../services/http-errors";

export function useLoginPage(login: (email: string, password: string) => Promise<boolean>) {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      const admin = await login(email, password);
      navigate(admin ? "/admin" : "/profile");
    } catch (err: unknown) {
      setError(toUserMessage(err, "login"));
    } finally {
      setLoading(false);
    }
  }

  return {
    email,
    setEmail,
    password,
    setPassword,
    loading,
    error,
    onSubmit
  };
}
