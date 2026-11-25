"use client";

import { useState } from "react";
import { Activity, ArrowRight, Beaker, Bell, Boxes, ChevronRight, CircleDot, FileText, FlaskConical, Layers3, LayoutDashboard, LogOut, Menu, Plus, Search, SlidersHorizontal, X } from "lucide-react";
import { QueryClient, QueryClientProvider, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { api, type User } from "../lib/api";
import { Badge, ErrorMessage, Field, ThemeControl, useAction } from "./ui";
import { Dashboard, MarketTwin, Reports, Research, Simulator } from "./insights";
import { Experiments, ParticipantLab, Products, Projects } from "./studio";

const nav = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/projects", label: "Projects", icon: Layers3 },
  { href: "/products", label: "Product studio", icon: Boxes },
  { href: "/experiments", label: "Consumer lab", icon: FlaskConical },
  { href: "/market-twin", label: "Market twin", icon: Activity },
  { href: "/simulations", label: "Simulator", icon: SlidersHorizontal },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/research", label: "Research", icon: Beaker },
];

export function Workspace() {
  const [client] = useState(() => new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 15000 } } }));
  return <QueryClientProvider client={client}><Shell /></QueryClientProvider>;
}

function Mark() {
  return <span className="brand"><span className="brand-icon"><Layers3 size={20} strokeWidth={2.5} /></span><span>Demand<span className="brand-accent">Twin</span><small>RESEARCH STUDIO</small></span></span>;
}

function Shell() {
  const path = usePathname();
  if (path.startsWith("/lab/")) return <ParticipantLab id={path.split("/")[2]} />;
  return <AuthenticatedShell />;
}

function Notifications() {
  const [open, setOpen] = useState(false);
  const list = useQuery({ queryKey: ["notifications"],
    queryFn: () => api<{ id: string; message: string; read: boolean; created: string }[]>("/notifications"), refetchInterval: 15000 });
  const action = useAction(() => { void list.refetch(); });
  const unread = list.data?.filter((item) => !item.read).length ?? 0;
  return <div className="notifications">
    <button className="icon-button" aria-label={unread ? "Notifications, " + unread + " unread" : "Notifications"} aria-expanded={open} onClick={() => setOpen(!open)}>
      <Bell size={17} />{unread > 0 && <span className="notification-count">{unread}</span>}
    </button>
    {open && <section className="notification-panel" aria-label="Notification list">
      <strong>Notifications</strong><ErrorMessage error={list.error || action.error} />
      {list.data?.length ? list.data.map((item) => <div className="list-row" key={item.id}><div><p>{item.message}</p><small>{new Date(item.created).toLocaleString()}</small></div>
        {!item.read && <button className="text-button" disabled={action.busy} onClick={() => action.run(() => api("/notifications/" + item.id + "/read", "POST"))}>Mark read</button>}
      </div>) : <p className="muted">Your study, model and report updates will appear here.</p>}
    </section>}
  </div>;
}

function AuthenticatedShell() {
  const path = usePathname();
  const router = useRouter();
  const client = useQueryClient();
  const auth = useQuery({ queryKey: ["me"], queryFn: () => api<User>("/auth/me") });
  const [menu, setMenu] = useState(false);
  const [search, setSearch] = useState("");
  const logout = useAction();
  if (auth.isPending) return <main className="standalone"><Mark /><p>Opening your workspace…</p></main>;
  if (!auth.data) return <SignIn startupError={(auth.error as { status?: number } | null)?.status === 401 ? null : auth.error} />;
  const user = auth.data;
  const link = nav.find((item) => item.href === path) ?? nav[0];
  const filtered = nav.filter((item) => item.label.toLowerCase().includes(search.toLowerCase()));
  return <div className="shell">
    {menu && <button aria-label="Close navigation" className="scrim" onClick={() => setMenu(false)} />}
    <aside className={"sidebar " + (menu ? "open" : "")}>
      <Link className="brand-link" href="/" onClick={() => setMenu(false)}><Mark /></Link>
      <div className="workspace-label"><div className="workspace-avatar">DT</div><div><strong>Research workspace</strong><small>Personal workspace</small></div><ChevronRight size={15} /></div>
      <nav aria-label="Workspace">
        <span className="nav-label">WORKSPACE</span>
        {filtered.map(({ href, label, icon: Icon }) => <Link key={href} href={href} onClick={() => { setMenu(false); setSearch(""); }} aria-current={path === href ? "page" : undefined}>
          <Icon size={17} /><span>{label}</span>{path === href && <CircleDot className="nav-indicator" size={10} />}
        </Link>)}
        {filtered.length === 0 && <p className="nav-label">No matching pages</p>}
      </nav>
      <div className="sidebar-bottom"><div className="workspace-note"><span><i /> Evidence-first</span><small>Sandbox ready · RACE-Twin</small></div>
        <div className="profile"><span className="avatar">{user.email.slice(0, 2).toUpperCase()}</span><div><strong title={user.email}>{user.email}</strong><small>{user.role}</small></div>
          <button type="button" className="icon-button" aria-label="Sign out" disabled={logout.busy} onClick={() => logout.run(async () => {
            await api("/auth/logout", "POST"); client.clear(); router.replace("/");
          })}><LogOut size={16} /></button></div>
        <ErrorMessage error={logout.error} />
      </div>
    </aside>
    <div className="main">
      <header className="topbar"><div className="breadcrumbs"><button className="icon-button mobile-menu" aria-label="Open navigation" onClick={() => setMenu(true)}><Menu size={19} /></button>
        <span>Workspace</span><ChevronRight size={14} /><strong>{link.label}</strong></div>
        <div className="top-actions"><label className="search"><Search size={15} /><input aria-label="Search navigation" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Find a page…" />
          {search && <button type="button" aria-label="Clear search" onClick={() => setSearch("")}><X size={14} /></button>}</label><Notifications /><ThemeControl /></div>
      </header>
      <main className="content" key={path}>
        {path === "/projects" ? <Projects /> : path === "/products" ? <Products /> : path === "/experiments" ? <Experiments user={user} />
          : path === "/market-twin" || path === "/analytics" ? <MarketTwin /> : path === "/simulations" ? <Simulator />
          : path === "/reports" ? <Reports /> : path === "/research" ? <Research user={user} /> : <Dashboard />}
      </main>
      <footer className="app-footer"><span>DemandTwin · Computational market research</span><span>RACE-Twin / Local workspace</span></footer>
    </div>
  </div>;
}

const credentials = z.object({ email: z.email(), password: z.string().min(10).max(128), researchCode: z.string().optional() });
function SignIn({ startupError }: { startupError: unknown }) {
  const [register, setRegister] = useState(false);
  const client = useQueryClient();
  const action = useAction();
  const { register: field, handleSubmit, formState: { errors } } = useForm<z.infer<typeof credentials>>({ resolver: zodResolver(credentials) });
  return <main className="auth-page">
    <section className="auth-info"><Mark /><div><Badge type="green">CONSUMER RESEARCH WORKSPACE</Badge><h1>Explore how shoppers might choose.</h1>
      <p>Design choice studies, fit preference models and compare product scenarios with a visible evidence trail.</p>
      <div className="auth-steps"><span><Layers3 size={16} /> Product concepts</span><span><FlaskConical size={16} /> Choice experiments</span><span><Activity size={16} /> Market scenarios</span></div></div>
      <span className="auth-footer">DEMANDTWIN / RACE-TWIN RESEARCH FRAMEWORK</span>
    </section>
    <section className="auth-main"><div className="auth-theme"><ThemeControl /></div><div className="auth-form">
      <span className="eyebrow">YOUR WORKSPACE</span><h2>{register ? "Create your account" : "Sign in"}</h2>
      <p>{register ? "Start a project and run a synthetic choice study." : "Open your projects, experiments and model runs."}</p>
      <ErrorMessage error={startupError} />
      <form className="stack" onSubmit={handleSubmit((input) => action.run(async () => {
        const user = await api<User>(register ? "/auth/register" : "/auth/login", "POST", {
          email: input.email, password: input.password, ...(register && input.researchCode ? { research_code: input.researchCode } : {}),
        });
        client.setQueryData(["me"], user);
      }))}>
        <Field label="Email"><input type="email" placeholder="you@example.com" autoComplete="email" required {...field("email")} /></Field>
        <Field label="Password"><input type="password" placeholder="At least 10 characters" autoComplete={register ? "new-password" : "current-password"} required {...field("password")} /></Field>
        {register && <Field label="Research code (optional)"><input autoComplete="off" {...field("researchCode")} /></Field>}
        <ErrorMessage error={action.error || errors.email?.message || errors.password?.message} />
        <button className="button primary" disabled={action.busy}>{register ? <Plus size={16} /> : <ArrowRight size={16} />}{register ? "Create account" : "Sign in"}</button>
      </form>
      <button className="text-button" onClick={() => setRegister(!register)}>{register ? "Already registered? Sign in" : "New here? Create an account"}</button>
    </div></section>
  </main>;
}
