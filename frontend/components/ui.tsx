"use client";

import { useEffect, useState, type ReactNode, type FormEvent } from "react";
import { AlertTriangle, ArrowRight, CircleHelp, Monitor, Moon, Sun } from "lucide-react";
import Link from "next/link";

type Theme = "light" | "dark" | "system";
export function ThemeControl() {
  const [theme, setTheme] = useState<Theme>("light");
  useEffect(() => {
    const saved = localStorage.getItem("dt-theme");
    if (saved === "light" || saved === "dark" || saved === "system") setTheme(saved);
  }, []);
  useEffect(() => {
    const query = matchMedia("(prefers-color-scheme: dark)");
    function apply() { document.documentElement.dataset.theme = theme === "system" ? query.matches ? "dark" : "light" : theme; }
    apply();
    query.addEventListener("change", apply);
    return () => query.removeEventListener("change", apply);
  }, [theme]);
  const Icon = theme === "dark" ? Moon : theme === "system" ? Monitor : Sun;
  return <label className="theme"><Icon size={16} /><select aria-label="Theme" value={theme} onChange={(event) => {
    const value = event.target.value as Theme;
    localStorage.setItem("dt-theme", value);
    setTheme(value);
  }}><option value="light">Light</option><option value="dark">Dark</option><option value="system">System</option></select></label>;
}
export function Notice({ children }: { children: ReactNode }) {
  return <div className="notice"><AlertTriangle size={17} /> <span>{children}</span></div>;
}
export function ErrorMessage({ error }: { error: unknown }) {
  return error ? <div className="notice error" role="alert"><AlertTriangle size={17} /><span>{error instanceof Error ? error.message : String(error)}</span></div> : null;
}
export function Empty({ title, detail, href, action }: { title: string; detail: string; href?: string; action?: string }) {
  return <div className="empty"><div className="empty-icon"><CircleHelp size={19} /></div><strong>{title}</strong><p>{detail}</p>
    {href && <Link className="button secondary" href={href}>{action}<ArrowRight size={15} /></Link>}</div>;
}
export function PageTitle({ eyebrow, title, description, action }: { eyebrow: string; title: string; description: string; action?: ReactNode }) {
  return <header className="page-title"><div><span className="eyebrow">{eyebrow}</span><h1>{title}</h1><p>{description}</p></div>{action}</header>;
}
export function Card({ title, hint, children, action }: { title: string; hint?: string; children: ReactNode; action?: ReactNode }) {
  return <section className="card"><header className="card-header"><div><h2>{title}</h2>{hint && <p>{hint}</p>}</div>{action}</header>{children}</section>;
}
export function Field({ label, children }: { label: string; children: ReactNode }) {
  return <label className="field"><span>{label}</span>{children}</label>;
}
export function Badge({ children, type = "" }: { children: ReactNode; type?: string }) {
  return <span className={"badge " + type}>{children}</span>;
}
export function useAction(onDone?: () => void) {
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  async function run<T>(task: () => Promise<T>) {
    setError(null);
    setBusy(true);
    try {
      const result = await task();
      onDone?.();
      return result;
    } catch (failure) {
      setError(failure);
    } finally {
      setBusy(false);
    }
  }
  return { error, busy, run };
}
export function values(event: FormEvent<HTMLFormElement>) {
  event.preventDefault();
  return new FormData(event.currentTarget);
}
