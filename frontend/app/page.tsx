"use client";
import { useCallback, useEffect, useState } from "react";
import AuthScreen from "../components/AuthScreen";
import Workspace from "../components/Workspace";

export default function Home() {
  // undefined = still reading localStorage (avoids flashing the sign-in screen)
  const [token, setToken] = useState<string | null | undefined>(undefined);
  useEffect(() => setToken(localStorage.getItem("token")), []);

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    setToken(null);
  }, []);

  if (token === undefined) return null;
  if (!token) {
    return <AuthScreen onToken={(t) => { localStorage.setItem("token", t); setToken(t); }} />;
  }
  return <Workspace token={token} onLogout={logout} />;
}
