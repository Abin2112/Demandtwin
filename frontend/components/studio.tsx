"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowRight, Check, Clipboard, FlaskConical, Link2, Play, Plus, Sprout, Trash2 } from "lucide-react";
import Link from "next/link";
import { api, money, number, type Alternative, type Model, type Product, type Project, type Study, type StudyResults, type User } from "../lib/api";
import { Badge, Card, Empty, ErrorMessage, Field, Notice, PageTitle, ThemeControl, useAction, values } from "./ui";

export const useProjects = () => useQuery({ queryKey: ["projects"], queryFn: () => api<Project[]>("/projects") });
export const useProducts = () => useQuery({ queryKey: ["products"], queryFn: () => api<Product[]>("/products") });
export const useModels = () => useQuery({
  queryKey: ["models"], queryFn: () => api<Model[]>("/models"),
  refetchInterval: (query) => query.state.data?.some((model) => ["queued", "running"].includes(model.status)) ? 1800 : false,
});

function useMutation() {
  const client = useQueryClient();
  return useAction(() => {
    void client.invalidateQueries({ predicate: (query) => query.queryKey[0] !== "me" });
  });
}

const str = (data: FormData, key: string) => String(data.get(key) ?? "");
const num = (data: FormData, key: string) => Number(data.get(key));
export const alternative = ({ name, price, grams, flavour, packaging, positioning }: Alternative): Alternative =>
  ({ name, price, grams, flavour, packaging, positioning });

export function readAlternative(data: FormData, prefix = ""): Alternative {
  return {
    name: str(data, prefix + "name"), price: num(data, prefix + "price"), grams: num(data, prefix + "grams"),
    flavour: str(data, prefix + "flavour") as Alternative["flavour"], packaging: str(data, prefix + "packaging") as Alternative["packaging"],
    positioning: str(data, prefix + "positioning") as Alternative["positioning"],
  };
}

export function AlternativeFields({ product, prefix = "", optional = false }: { product?: Alternative; prefix?: string; optional?: boolean }) {
  return <div className="form-grid">
    <Field label="Product name"><input name={prefix + "name"} defaultValue={product?.name} required={!optional} maxLength={120} placeholder="Millet crisps" /></Field>
    <Field label="Price (INR)"><input name={prefix + "price"} defaultValue={product?.price} type="number" min=".01" max="100000" step=".01" required={!optional} placeholder="30" /></Field>
    <Field label="Pack size (g)"><input name={prefix + "grams"} defaultValue={product?.grams} type="number" min=".01" max="5000" step=".01" required={!optional} placeholder="50" /></Field>
    <Field label="Flavour"><select name={prefix + "flavour"} defaultValue={product?.flavour ?? "classic"}><option value="classic">Classic</option><option value="spicy">Spicy</option></select></Field>
    <Field label="Packaging"><select name={prefix + "packaging"} defaultValue={product?.packaging ?? "standard"}><option value="standard">Standard</option><option value="resealable">Resealable</option></select></Field>
    <Field label="Positioning"><select name={prefix + "positioning"} defaultValue={product?.positioning ?? "standard"}><option value="standard">Standard</option><option value="premium">Premium</option></select></Field>
  </div>;
}

export function Projects() {
  const list = useProjects();
  const action = useMutation();
  const [edit, setEdit] = useState<Project | null>(null);
  return <>
    <PageTitle eyebrow="ORGANIZE / 01" title="Projects" description="Keep product concepts, studies and model runs together." />
    <div className="split">
      <Card title={edit ? "Edit project" : "New project"} hint="Projects are private to your account.">
        <form key={edit?.id ?? "new"} className="stack" onSubmit={(event) => {
          const data = values(event);
          const form = event.currentTarget;
          void action.run(async () => {
            await api(edit ? "/projects/" + edit.id : "/projects", edit ? "PATCH" : "POST", { name: str(data, "name"), description: str(data, "description") });
            form.reset(); setEdit(null);
          });
        }}>
          <Field label="Project name"><input name="name" required maxLength={120} defaultValue={edit?.name} placeholder="Mumbai snack concepts" /></Field>
          <Field label="Description"><textarea name="description" maxLength={2000} defaultValue={edit?.description} placeholder="What are you investigating?" /></Field>
          <div className="actions"><button className="button primary" disabled={action.busy}><Plus size={16} />{edit ? "Save changes" : "Create project"}</button>
            {edit && <button className="button secondary" type="button" onClick={() => setEdit(null)}>Cancel</button>}</div>
        </form>
        <ErrorMessage error={action.error} />
      </Card>
      <Card title="Your projects" hint="Choose a project when creating concepts and studies.">
        <ErrorMessage error={list.error} />
        {list.isPending ? <p>Loading projects…</p> : list.data?.length ? <div className="rows">{list.data.map((project) => <div className="list-row" key={project.id}>
          <div><strong>{project.name}</strong><small>{project.description || "Project workspace"}</small></div>
          <div className="actions"><button className="button secondary small" type="button" onClick={() => setEdit(project)}>Edit</button>
            {project.is_owner && <button className="icon-button" aria-label={"Delete " + project.name} disabled={action.busy} onClick={() => {
              if (window.confirm("Delete this project and its products, experiments, and reports?")) void action.run(async () => {
                await api("/projects/" + project.id, "DELETE");
                if (edit?.id === project.id) setEdit(null);
              });
            }}><Trash2 size={16} /></button>}</div>
        </div>)}</div> : <Empty title="No projects yet" detail="Give your first research question a workspace." />}
      </Card>
    </div>
    <Collaborators projects={list.data?.filter((project) => project.is_owner) ?? []} />
  </>;
}

function Collaborators({ projects }: { projects: Project[] }) {
  const [selected, setSelected] = useState("");
  const project = projects.find((item) => item.id === selected) ?? projects[0];
  const members = useQuery({ queryKey: ["members", project?.id], enabled: Boolean(project),
    queryFn: () => api<{ id: string; email: string; role: string }[]>("/projects/" + project!.id + "/members") });
  const action = useMutation();
  if (!project) return null;
  return <Card title="Project collaborators" hint="Add a registered account as an editor. Only the project owner can manage membership or delete the project.">
    <form className="stack" onSubmit={(event) => {
      const data = values(event);
      const form = event.currentTarget;
      void action.run(async () => { await api("/projects/" + project.id + "/members", "POST", { email: data.get("email") }); form.reset(); });
    }}>
      <div className="form-grid"><Field label="Shared project"><select value={project.id} onChange={(event) => setSelected(event.target.value)}>
        {projects.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
      <Field label="Collaborator email"><input name="email" type="email" required maxLength={254} placeholder="Registered account email" /></Field></div>
      <button className="button secondary" disabled={action.busy}>Add editor</button>
    </form>
    <ErrorMessage error={action.error || members.error} />
    <div className="rows">{members.data?.map((member) => <div className="list-row" key={member.id}>
      <div><strong>{member.email}</strong><small>{member.role}</small></div>
      {member.role !== "owner" && <button className="button secondary small" disabled={action.busy}
        onClick={() => action.run(() => api("/projects/" + project.id + "/members/" + member.id, "DELETE"))}>Remove access</button>}
    </div>)}</div>
  </Card>;
}

function PackagingImage({ product }: { product: Product }) {
  const action = useMutation();
  return <div className="stack">
    {product.packaging_image && <img className="packaging-preview" src={product.packaging_image} alt={product.name + " packaging"} />}
    <Field label={"Upload packaging for " + product.name}><input type="file" accept="image/png,image/jpeg,image/webp" disabled={action.busy} onChange={(event) => {
      const file = event.target.files?.[0];
      const input = event.target;
      if (!file) return;
      void action.run(async () => {
        if (file.size > 5 * 1024 * 1024) throw new Error("Choose an image no larger than 5 MB.");
        await api("/products/" + product.id + "/image", "POST", file); input.value = "";
      });
    }} /></Field>
    {product.packaging_image?.startsWith("/api/") && <button className="text-button" disabled={action.busy}
      onClick={() => action.run(() => api("/products/" + product.id + "/image", "DELETE"))}>Remove packaging image</button>}
    <ErrorMessage error={action.error} />
  </div>;
}

export function Products() {
  const projects = useProjects(), products = useProducts();
  const [selected, setSelected] = useState<{ product: Product; mode: "edit" | "variant" } | null>(null);
  const [addCompetitor, setAddCompetitor] = useState(false);
  const action = useMutation();
  const product = selected?.product;
  function save(event: FormEvent<HTMLFormElement>) {
    const data = values(event);
    const form = event.currentTarget;
    const details = {
      ...readAlternative(data), category: str(data, "category"), location: str(data, "location"),
      segment: str(data, "segment"), description: str(data, "description"), ingredients: str(data, "ingredients"),
      features: str(data, "features"), packaging_image: str(data, "packaging_image") || null,
      cost: str(data, "cost") ? num(data, "cost") : null,
      competitors: addCompetitor ? [readAlternative(data, "competitor-"), ...(product?.competitors.slice(1) ?? [])] : [],
    };
    void action.run(async () => {
      if (selected?.mode === "edit") await api("/products/" + selected.product.id, "PATCH", details);
      else if (selected?.mode === "variant") await api("/products/" + selected.product.id + "/variants", "POST", details);
      else await api("/products", "POST", { ...details, project_id: str(data, "project_id") });
      form.reset(); setSelected(null); setAddCompetitor(false);
    });
  }
  return <>
    <PageTitle eyebrow="DESIGN / 02" title="Product studio" description="Capture a packaged snack concept and the alternatives you want shoppers to compare." />
    <ErrorMessage error={projects.error || products.error} />
    <div className="split">
      <Card title={selected ? selected.mode === "edit" ? "Edit concept" : "Create variant" : "New product concept"} hint="The current choice model uses price, pack size, flavour, packaging and positioning.">
        {projects.data?.length ? <form key={(product?.id ?? "new") + selected?.mode} className="stack" onSubmit={save}>
          {!product && <Field label="Project"><select name="project_id">{projects.data.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>}
          <AlternativeFields product={selected?.mode === "variant" && product ? { ...product, name: product.name.slice(0, 110) + " variant" } : product} />
          <div className="form-grid">
            <Field label="Category"><input name="category" defaultValue={product?.category ?? "Packaged snacks"} required maxLength={120} /></Field>
            <Field label="Target location"><input name="location" defaultValue={product?.location ?? "Mumbai"} required maxLength={120} /></Field>
            <Field label="Target segment"><select name="segment" defaultValue={product?.segment ?? "balanced"}><option value="value">Value</option><option value="balanced">Balanced</option><option value="premium">Premium</option></select></Field>
            <Field label="Cost (optional, INR)"><input name="cost" type="number" min="0" max="100000" step=".01" defaultValue={product?.cost ?? ""} /></Field>
          </div>
          <Field label="Description"><textarea name="description" maxLength={2000} defaultValue={product?.description} /></Field>
          <Field label="Ingredients"><input name="ingredients" maxLength={2000} defaultValue={product?.ingredients} /></Field>
          <Field label="Product features"><input name="features" maxLength={2000} defaultValue={product?.features} /></Field>
          <Field label="Packaging image URL (optional)"><input name="packaging_image" placeholder="https://…" maxLength={1500} defaultValue={product?.packaging_image ?? ""} /></Field>
          <label className="check"><input type="checkbox" checked={addCompetitor} onChange={(event) => setAddCompetitor(event.target.checked)} /> Include a competitor</label>
          {addCompetitor && <fieldset><legend>Competitor</legend><AlternativeFields prefix="competitor-" product={product?.competitors[0]} /></fieldset>}
          <div className="actions"><button className="button primary" disabled={action.busy}><Plus size={16} />{selected?.mode === "edit" ? "Save concept" : selected ? "Save variant" : "Create product"}</button>
            {selected && <button className="button secondary" type="button" onClick={() => { setSelected(null); setAddCompetitor(false); }}>Cancel</button>}</div>
        </form> : <Empty title="Create a project first" detail="Your concepts belong to a project." href="/projects" action="Go to projects" />}
        <ErrorMessage error={action.error} />
      </Card>
      <Card title="Concept library" hint="Variants are tracked alongside their parent product.">
        {products.data?.length ? <div className="rows">{products.data.map((item) => <div className="concept-entry" key={item.id}><div className="list-row"><div><strong>{item.name}</strong>
          <small>{money(item.price)} · {item.grams} g · {item.category}</small><Badge>{item.parent_id ? "Variant" : item.location}</Badge></div>
          <div className="actions">{(["edit", "variant"] as const).map((mode) => <button key={mode} className="button secondary small" onClick={() => {
            setSelected({ product: item, mode }); setAddCompetitor(item.competitors.length > 0);
          }}>{mode === "edit" ? "Edit" : "Add variant"}</button>)}</div></div>
          <details><summary>Packaging image</summary><PackagingImage product={item} /></details>
          </div>)}</div> : <Empty title="No products yet" detail="Create a concept to use in a choice study." />}
      </Card>
    </div>
  </>;
}

type Ranking = { selected: number; rationale: string; strategy: string; candidates: { index: number; information_gain_nats: number; alternatives: number; completed: number }[] };
type RankingHistory = Ranking & { id: string; created: string };
function StudyDetail({ study, models, action }: { study: Study; models: Model[]; action: ReturnType<typeof useMutation> }) {
  const [ranking, setRanking] = useState<Ranking | null>(null);
  const [copied, setCopied] = useState(false);
  const results = useQuery({ queryKey: ["results", study.id], queryFn: () => api<StudyResults>("/experiments/" + study.id + "/results"), refetchInterval: study.status === "active" ? 5000 : false });
  const history = useQuery({ queryKey: ["design-history", study.id], queryFn: () => api<RankingHistory[]>("/experiments/" + study.id + "/design-history") });
  const path = "/experiments/" + study.id;
  const invite = "/lab/" + study.id;
  const latest = models.find((model) => model.experiment_id === study.id);
  function rank(event: FormEvent<HTMLFormElement>) {
    const data = values(event);
    void action.run(async () => setRanking(await api<Ranking>(path + "/next-design", "POST", {
      strategy: str(data, "strategy"), segment: str(data, "segment"), model_id: latest?.status === "ready" ? latest.id : null,
    })));
  }
  return <div className="stack">
    <div className="actions"><Badge type={study.status === "active" ? "green" : ""}>{study.status}</Badge><Badge>{study.synthetic ? "Synthetic sandbox" : "Human hypothetical choice"}</Badge><Badge>{study.designs.length} candidate tasks</Badge><Badge>{study.policy.strategy} · up to {study.task_count} tasks per session</Badge></div>
    <div className="actions">
      {study.status === "draft" && <button className="button primary" disabled={action.busy} onClick={() => action.run(() => api(path + "/launch", "POST"))}><Play size={15} />Launch study</button>}
      {study.status === "active" && <>
        <Link href={invite} className="button secondary"><Link2 size={15} />Open participant lab</Link>
        <button className="button secondary" disabled={action.busy} onClick={() => action.run(async () => { await navigator.clipboard.writeText(location.origin + invite); setCopied(true); })}><Clipboard size={15} />{copied ? "Copied" : "Copy invite"}</button>
        {study.synthetic && <button className="button secondary" disabled={action.busy} onClick={() => action.run(() => api(path + "/seed", "POST"))}><Sprout size={15} />Generate synthetic panel</button>}
        <button className="button secondary" disabled={action.busy} onClick={() => action.run(() => api(path + "/close", "POST"))}>Close study</button>
      </>}
      <button className="button primary" disabled={action.busy || (results.data?.participants ?? 0) < 8 || ["queued", "running"].includes(latest?.status ?? "")}
        onClick={() => action.run(() => api("/models/train", "POST", { experiment_id: study.id }))}>Train choice model</button>
    </div>
    <ErrorMessage error={results.error || latest?.error || history.error} />
    {results.data && <><div className="actions"><Badge>{number(results.data.participants)} participants</Badge><Badge>{number(results.data.responses)} choices</Badge><Badge>{number(results.data.complete)} complete</Badge></div>
      {Object.keys(results.data.choices).length > 0 && <div className="table-wrap"><table><thead><tr><th>Observed task selection</th><th>Count</th></tr></thead>
        <tbody>{Object.entries(results.data.choices).map(([name, count]) => <tr key={name}><td>{name}</td><td>{number(count)}</td></tr>)}</tbody></table></div>}</>}
    {latest && <p className="muted">Latest model · <strong>{latest.status}</strong> · {latest.id.slice(0, 8)}</p>}
    {latest && ["failed", "running", "queued"].includes(latest.status) && <button className="button secondary" disabled={action.busy}
      onClick={() => action.run(() => api("/models/" + latest.id + "/retry", "POST"))}>Retry failed or interrupted run</button>}
    <form className="stack inset" onSubmit={rank}>
      <strong>Adaptive design review</strong><p className="muted">Review candidate information gain. Participant assignment follows the study’s saved policy.</p>
      <div className="form-grid">
        <Field label="Design policy"><select name="strategy"><option value="adaptive">Information gain</option><option value="balanced">Balance exposure</option><option value="random">Seeded random</option></select></Field>
        <Field label="Segment"><select name="segment"><option value="balanced">Balanced</option><option value="value">Value</option><option value="premium">Premium</option></select></Field>
      </div>
      <button className="button secondary" disabled={action.busy}>Rank candidates</button>
      {ranking && <><p>Recommended task {ranking.selected + 1}. {ranking.rationale}.</p><div className="table-wrap"><table><thead><tr><th>Task</th><th>Gain (nats)</th><th>Burden</th><th>Completed</th></tr></thead>
        <tbody>{ranking.candidates.map((item) => <tr key={item.index}><td>{item.index + 1}</td><td>{item.information_gain_nats.toFixed(4)}</td><td>{item.alternatives} products</td><td>{item.completed}</td></tr>)}</tbody></table></div></>}
      {history.data?.length ? <details><summary>Recommendation history</summary><ul>{history.data.map((item) => <li key={item.id}>{new Date(item.created).toLocaleDateString()} · {item.strategy} · task {item.selected + 1}</li>)}</ul></details> : null}
    </form>
  </div>;
}

export function Experiments({ user }: { user: User }) {
  const products = useProducts(), models = useModels();
  const studies = useQuery({ queryKey: ["experiments"], queryFn: () => api<Study[]>("/experiments") });
  const [selection, setSelection] = useState("");
  const [productId, setProductId] = useState("");
  const action = useMutation();
  const current = studies.data?.find((study) => study.id === selection) ?? studies.data?.[0];
  const chosenProduct = products.data?.find((item) => item.id === productId) ?? products.data?.[0];
  return <>
    <PageTitle eyebrow="COLLECT / 03" title="Consumer lab" description="Design a choice study, invite participants and review outcomes by evidence type." />
    <Notice>Use the synthetic sandbox for development. Real recruitment requires an approved protocol and researcher access.</Notice>
    <div className="split">
      <Card title="Design a study" hint="Each task shows your concept, competitor alternatives and a no-purchase option.">
        {chosenProduct ? <form className="stack" onSubmit={(event) => {
          const data = values(event);
          void action.run(async () => {
            const prices = str(data, "prices").split(",").map(Number);
            if (prices.length < 3 || prices.length > 12 || prices.some((price) => !Number.isFinite(price) || price <= 0) || new Set(prices).size !== prices.length) throw new Error("Enter 3–12 distinct positive prices separated by commas.");
            const opponents = chosenProduct.competitors.length ? chosenProduct.competitors : products.data?.filter((p) => p.project_id === chosenProduct.project_id && p.id !== chosenProduct.id).slice(0, 1).map(alternative) ?? [];
            if (!opponents.length) throw new Error("Add a competitor to the product or create a second concept in the project.");
            const designs = prices.map((price) => [{ ...alternative(chosenProduct), price }, ...opponents]);
            if (data.has("contrast")) {
              const contrast = { ...alternative(chosenProduct), grams: Math.min(5000, chosenProduct.grams * 1.2),
                packaging: chosenProduct.packaging === "standard" ? "resealable" : "standard" };
              designs.push(...prices.map((price) => [{ ...contrast, packaging: contrast.packaging as Alternative["packaging"], price }, ...opponents]));
            }
            const quotas = Object.fromEntries(["value", "balanced", "premium"].filter((segment) => str(data, "quota-" + segment)).map((segment) => [segment, num(data, "quota-" + segment)]));
            const study = await api<Study>("/experiments", "POST", {
              project_id: chosenProduct.project_id, name: str(data, "name"), synthetic: str(data, "mode") !== "real", designs,
              policy: { strategy: str(data, "strategy"), task_limit: num(data, "task_limit"), max_products: num(data, "max_products"),
                min_price: num(data, "min_price"), max_price: num(data, "max_price"), segment_quotas: quotas },
            });
            setSelection(study.id);
          });
        }}>
          <Field label="Study name"><input name="name" required maxLength={120} placeholder="Millet crisps price study" /></Field>
          <Field label="Product"><select value={chosenProduct.id} onChange={(event) => setProductId(event.target.value)}>{products.data?.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
          <Field label="Price levels (INR, comma-separated)"><input name="prices" defaultValue="15, 20, 30, 40, 50" required /></Field>
          <label className="check"><input name="contrast" type="checkbox" defaultChecked /> Include a larger pack with alternate packaging</label>
          <Field label="Evidence mode"><select name="mode"><option value="sandbox">Synthetic sandbox</option>{user.role === "researcher" && <option value="real">Approved human study</option>}</select></Field>
          <fieldset className="stack"><legend>Assignment and participant burden</legend>
            <div className="form-grid">
              <Field label="Assignment policy"><select name="strategy"><option value="random">Randomized</option><option value="balanced">Balance segment exposure</option><option value="adaptive">Adaptive information gain</option></select></Field>
              <Field label="Maximum tasks per participant"><input name="task_limit" type="number" min="1" max="24" defaultValue="6" required /></Field>
              <Field label="Maximum products per task"><input name="max_products" type="number" min="2" max="6" defaultValue="6" required /></Field>
              <Field label="Minimum displayed price (INR)"><input name="min_price" type="number" min="0" max="99999" step=".01" defaultValue="0" required /></Field>
              <Field label="Maximum displayed price (INR)"><input name="max_price" type="number" min=".01" max="100000" step=".01" defaultValue="100000" required /></Field>
            </div>
            <p className="muted">Optional enrollment limits. When any limit is supplied, only those segments enroll.</p>
            <div className="form-grid">{["value", "balanced", "premium"].map((segment) => <Field key={segment} label={segment + " enrollment limit"}>
              <input name={"quota-" + segment} type="number" min="1" max="100000" /></Field>)}</div>
          </fieldset>
          <button className="button primary" disabled={action.busy}><FlaskConical size={16} />Create study</button>
        </form> : <Empty title="A product is required" detail="Add a concept and competitor to design your first choice task." href="/products" action="Open product studio" />}
        <ErrorMessage error={action.error || products.error || studies.error || models.error} />
      </Card>
      <Card title="Study workspace" hint="Manage launches, inspect responses, and train a model.">
        {current ? <div className="stack"><Field label="Study"><select value={current.id} onChange={(event) => setSelection(event.target.value)}>
          {studies.data?.map((study) => <option key={study.id} value={study.id}>{study.name}</option>)}</select></Field>
          <StudyDetail key={current.id} study={current} models={models.data ?? []} action={action} /></div>
          : <Empty title="No studies yet" detail="Build a draft from a saved product concept." />}
      </Card>
    </div>
  </>;
}

type PublicStudy = { name: string; synthetic: boolean; task_count: number; consent_version: string; consent_text: string };
type Task = { task: number; alternatives: Alternative[] };
export function ParticipantLab({ id }: { id: string }) {
  const path = "/experiments/" + id;
  const [token, setToken] = useState("");
  const [withdrawn, setWithdrawn] = useState(false);
  const study = useQuery({ queryKey: ["participant-study", id], queryFn: () => api<PublicStudy>(path + "/participant") });
  const tasks = useQuery({ queryKey: ["tasks", id, token], queryFn: () => api<Task[]>(path + "/tasks", "GET", undefined, token), enabled: Boolean(token) && !withdrawn });
  const action = useAction();
  useEffect(() => { setToken(localStorage.getItem("dt-participant-" + id) ?? ""); }, [id]);
  const task = tasks.data?.[0];
  return <main className="participant-page"><header><Link href="/" className="brand"><span className="brand-icon"><FlaskConical size={18} /></span>DemandTwin Lab</Link><ThemeControl /></header>
    <PageTitle eyebrow="PARTICIPANT EXPERIENCE" title={study.data?.name ?? "Choice study"} description="Compare snack products in a series of hypothetical shopping decisions." />
    {study.data?.synthetic && <Notice>Sandbox session. Responses in this study are labeled synthetic.</Notice>}
    <ErrorMessage error={study.error || tasks.error || action.error} />
    {withdrawn ? <Card title="Your responses were deleted"><p>You have withdrawn from this study.</p></Card> : !token && study.data ?
      <Card title="Consent and eligibility" hint={"You will see up to " + study.data.task_count + " product choice tasks."}>
        <form className="stack" onSubmit={(event) => {
          const data = values(event);
          void action.run(async () => {
            const response = await api<{ participant_key: string }>(path + "/consent", "POST", {
              adult: data.has("adult"), consent: data.has("consent"), version: study.data.consent_version,
              segment: str(data, "segment"), synthetic: study.data.synthetic,
            });
            localStorage.setItem("dt-participant-" + id, response.participant_key);
            setToken(response.participant_key);
          });
        }}>
          <p className="consent-copy">{study.data.consent_text}</p>
          <label className="check"><input name="adult" type="checkbox" required /> I am 18 years or older.</label>
          <label className="check"><input name="consent" type="checkbox" required /> I understand the study and agree to participate.</label>
          <Field label="Shopping preference"><select name="segment"><option value="value">Value first</option><option value="balanced">Balance of price and features</option><option value="premium">Premium features</option></select></Field>
          <button className="button primary" disabled={action.busy}>Start tasks <ArrowRight size={16} /></button>
        </form>
      </Card> : task ? <Card title={"Choice task " + (task.task + 1)} hint="Which one would you choose if these were the options available?">
        <div className="choice-grid">{task.alternatives.map((item, index) => <button key={index} className="choice" disabled={action.busy} onClick={() => action.run(async () => {
          await api(path + "/responses", "POST", { task: task.task, chosen: index + 1 }, token); await tasks.refetch();
        })}><strong>{item.name}</strong><span>{money(item.price)}</span><small>{item.grams} g · {item.flavour} · {item.packaging} · {item.positioning}</small></button>)}</div>
        <button className="button secondary" disabled={action.busy} onClick={() => action.run(async () => {
          await api(path + "/responses", "POST", { task: task.task, chosen: 0 }, token); await tasks.refetch();
        })}>I would buy neither</button>
      </Card> : tasks.data?.length === 0 ? <Card title="Study complete"><div className="actions"><Check size={19} /> Your choices have been recorded.</div></Card> : null}
    {token && !withdrawn && <button className="text-button" disabled={action.busy} onClick={() => {
      if (window.confirm("Withdraw and permanently delete your responses?")) void action.run(async () => {
        await api(path + "/participant", "DELETE", undefined, token);
        localStorage.removeItem("dt-participant-" + id); setWithdrawn(true); setToken("");
      });
    }}>Withdraw and delete my responses</button>}
  </main>;
}
