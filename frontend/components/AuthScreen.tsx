"use client";
import { FormEvent, useState } from "react";
import { APP_NAME, authCall } from "../lib/api";
import { LogoMark } from "./Icons";

export default function AuthScreen({ onToken }: { onToken: (t: string) => void }) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      onToken(await authCall(mode, email.trim(), password));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setBusy(false);
    }
  }

  return (
    <div className="auth">
      <section className="auth-hero">
        <div className="brand brand-light"><LogoMark /><span>{APP_NAME}</span></div>
        <div className="hero-copy">
          <h1>Answers you can check.</h1>
          <p>Upload your PDFs and notes. Every answer links back to the exact passage it came from.</p>
        </div>
        <div className="demo" aria-hidden="true">
          <div className="demo-q">How many vacation days carry over?</div>
          <p className="demo-a">
            Up to 10 unused vacation days carry over each year.<span className="cite cite-on">1</span>
          </p>
          <div className="demo-src">
            <div className="demo-file">handbook.pdf, page 4</div>
            <p>
              Full-time employees accrue 1.5 vacation days per month.{" "}
              <mark>Unused vacation days carry over up to a maximum of 10 days.</mark>
            </p>
          </div>
        </div>
      </section>

      <section className="auth-form-wrap">
        <form className="auth-form" onSubmit={submit}>
          <div className="seg" role="tablist" aria-label="Account">
            <button type="button" role="tab" aria-selected={mode === "login"} className={mode === "login" ? "on" : ""} onClick={() => { setMode("login"); setError(""); }}>Sign in</button>
            <button type="button" role="tab" aria-selected={mode === "register"} className={mode === "register" ? "on" : ""} onClick={() => { setMode("register"); setError(""); }}>Create account</button>
          </div>

          <label className="field">
            <span>Email</span>
            <input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </label>
          <label className="field">
            <span>Password</span>
            <input type="password" autoComplete={mode === "login" ? "current-password" : "new-password"} required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} />
            {mode === "register" && <small>Use at least 8 characters.</small>}
          </label>

          {error && <div className="form-error" role="alert">{error}</div>}

          <button className="btn btn-primary btn-lg" disabled={busy}>
            {busy ? "Please wait…" : mode === "login" ? "Sign in" : "Create account"}
          </button>
          <p className="auth-note">Your documents are private to your account.</p>
        </form>
      </section>
    </div>
  );
}
