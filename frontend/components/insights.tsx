"use client";

import { useState, type FormEvent } from "react";
import { Activity, ArrowDownToLine, ArrowRight, Boxes, CheckCircle2, ClipboardList, FlaskConical, Plus, SlidersHorizontal, Users } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Area, AreaChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import Link from "next/link";
import { api, money, number, percent, type Model, type Parameters, type Report, type Simulation, type Study, type User } from "../lib/api";
import { AlternativeFields, readAlternative, useModels, useProducts } from "./studio";
import { Badge, Card, Empty, ErrorMessage, Field, Notice, PageTitle, useAction, values } from "./ui";

type Overview = { products: number; active: number; completed: number; real_participants: number; synthetic_participants: number;
  model: Model | null; simulation: Simulation | null; activity: Pick<Study, "id" | "name" | "status" | "synthetic">[] };
const chartStyle = { background: "var(--card)", color: "var(--foreground)", borderColor: "var(--border)", borderRadius: 8 };

export function Dashboard() {
  const client = useQueryClient();
  const demo = useAction(() => { void client.invalidateQueries({ predicate: (query) => query.queryKey[0] !== "me" }); });
  const result = useQuery({ queryKey: ["dashboard"], queryFn: () => api<Overview>("/dashboard") });
  const data = result.data;
  const latest = data?.simulation;
  const stats = [
    { label: "Product concepts", value: data?.products, icon: Boxes, detail: "Concepts and variants" },
    { label: "Active experiments", value: data?.active, icon: FlaskConical, detail: "Open for responses" },
    { label: "Real participants", value: data?.real_participants, icon: Users, detail: (data?.synthetic_participants ?? 0) + " sandbox sessions separately" },
    { label: "Completed studies", value: data?.completed, icon: CheckCircle2, detail: "Closed experiments" },
  ];
  return <>
    <PageTitle eyebrow="WORKSPACE / OVERVIEW" title="Research overview" description="Track your concepts, choice studies and market evidence." action={<Link href="/products" className="button primary"><Plus size={17} /> New concept</Link>} />
    <ErrorMessage error={result.error} />
    <div className="actions"><button className="button secondary" disabled={demo.busy} onClick={() => demo.run(async () => {
      const workspace = await api<{ model_id: string; status: string }>("/demo", "POST");
      let status = workspace.status;
      const deadline = Date.now() + 120000;
      while (["queued", "running"].includes(status) && Date.now() < deadline) {
        await new Promise((resolve) => setTimeout(resolve, 1000));
        status = (await api<Model>("/models/" + workspace.model_id + "/status")).status;
      }
      if (status !== "ready") throw new Error("The demo study was saved. Review its training run in Consumer Lab and retry if needed.");
      await api("/demo", "POST");
    })}>
      <FlaskConical size={16} />{demo.busy ? "Preparing sandbox…" : "Prepare demo workspace"}</button>
      <span className="muted">Creates a labeled synthetic study, fitted model and price scenarios for you to explore.</span></div>
    <ErrorMessage error={demo.error} />
    <div className="overview-banner"><div><Badge>PACKAGED FOOD & SNACKS</Badge><h2>Test a product idea before launch.</h2><p>Start with a product concept, collect choice responses, then compare scenarios under explicit assumptions.</p>
      <Link href={data?.products ? "/experiments" : "/projects"}>{data?.products ? "Open consumer lab" : "Create your first project"} <ArrowRight size={16} /></Link></div>
      <div className="banner-art" aria-hidden="true"><span /><span /><span /><span /><span /><span /><i /><i /><i /></div></div>
    <div className="stats-grid">{stats.map(({ label, value, icon: Icon, detail }) => <div className="stat" key={label}><div><span>{label}</span><Icon size={18} /></div><strong>{value === undefined ? "—" : number(value)}</strong><small>{detail}</small></div>)}</div>
    <div className="split dashboard-split">
      <Card title="Latest scenario" hint="Estimated share per eligible choice opportunity." action={<Link href="/simulations" className="icon-button" aria-label="Open simulator"><ArrowRight size={18} /></Link>}>
        {latest ? <ScenarioSummary item={latest} /> : <Empty title="Your estimates will appear here" detail="Train a model from a choice study, then compare prices in the simulator." href="/simulations" action="Open simulator" />}
      </Card>
      <Card title="Evidence and activity" hint="Model status and recent choice studies.">
        <div className="model-status"><Activity size={18} /><div><strong>{data?.model ? "Model " + data.model.status : "Awaiting choice evidence"}</strong><small>{data?.model?.evidence_quality ?? "Complete a study to fit your first model."}</small></div><Badge type={data?.model?.status === "ready" ? "green" : ""}>{data?.model?.id.slice(0, 8) ?? "No run"}</Badge></div>
        {data?.activity.length ? <div className="rows">{data.activity.map((item) => <div className="list-row" key={item.id}><div><strong>{item.name}</strong><small>{item.synthetic ? "Synthetic sandbox" : "Human hypothetical choices"}</small></div><Badge>{item.status}</Badge></div>)}</div>
          : <div className="quiet-row"><ClipboardList size={17} /> No experiment activity yet</div>}
      </Card>
    </div>
  </>;
}

function ScenarioSummary({ item }: { item: Simulation }) {
  const target = item.result;
  const [lo, hi] = target.interval_90[1];
  return <div className="stack">
    <div className="actions"><Badge type={target.abstain ? "amber" : "green"}>{target.abstain ? "Outside observed support" : target.evidence_quality}</Badge><span className="muted">{item.name}</span></div>
    <div className="scenario-head"><strong>{percent(target.choice[1])}</strong><span>90% interval {percent(lo)}–{percent(hi)}</span></div>
    <div className="table-wrap"><table><thead><tr><th>Alternative</th><th>Choice share</th><th>Expected units</th></tr></thead><tbody>
      {target.labels.map((label, index) => <tr key={index}><td>{label}</td><td>{percent(target.choice[index])}</td><td>{index ? number(target.expected_units[index - 1]) : "—"}</td></tr>)}
    </tbody></table></div>
    <p className="muted">{number(item.inputs.opportunities)} assumed opportunities · own-price elasticity {target.elasticity?.toFixed(2) ?? "unavailable"}</p>
    {target.warnings.length > 0 && <Notice>{target.warnings.join(" · ")}</Notice>}
    <details><summary>Segment assumptions and contribution detail</summary><div className="table-wrap"><table><thead><tr><th>Segment</th><th>Weight</th><th>Target share</th><th>Price coefficient per INR</th></tr></thead>
      <tbody>{Object.entries(target.segments).map(([segment, entry]) => <tr key={segment}><td>{segment}</td><td>{percent(entry.weight)}</td><td>{percent(entry.choice[1])}</td><td>{entry.price_coefficient.toFixed(4)}</td></tr>)}</tbody></table></div></details>
  </div>;
}

export function Simulator() {
  const models = useModels(), products = useProducts();
  const saved = useQuery({ queryKey: ["simulations"], queryFn: () => api<Simulation[]>("/simulations") });
  const client = useQueryClient();
  const action = useAction(() => { void client.invalidateQueries({ queryKey: ["simulations"] }); void client.invalidateQueries({ queryKey: ["dashboard"] }); });
  const [modelId, setModelId] = useState(""), [productId, setProductId] = useState("");
  const [comparison, setComparison] = useState<Simulation[]>([]);
  const [selected, setSelected] = useState("");
  const ready = models.data?.filter((model) => model.status === "ready") ?? [];
  const model = ready.find((item) => item.id === modelId) ?? ready[0];
  const eligibleProducts = products.data?.filter((item) => item.project_id === model?.project_id) ?? [];
  const product = eligibleProducts.find((item) => item.id === productId) ?? eligibleProducts[0];
  const current = saved.data?.find((item) => item.id === selected) ?? comparison[0] ?? saved.data?.[0];
  const curve = [...comparison].sort((a, b) => a.inputs.product.price - b.inputs.product.price).map((item) => ({
    price: item.inputs.product.price, share: item.result.choice[1], low: item.result.interval_90[1][0], high: item.result.interval_90[1][1],
  }));
  function submit(event: FormEvent<HTMLFormElement>) {
    const data = values(event);
    if (!product || !model) return;
    void action.run(async () => {
      const target = readAlternative(data);
      const prices = String(data.get("prices") || "").split(",").filter((value) => value.trim()).map(Number);
      const weights = Object.fromEntries(["value", "balanced", "premium"].map((key) => [key, Number(data.get(key))]).filter(([, value]) => Number(value) > 0));
      const common = { competitors: product.competitors.flatMap((item, index) => data.has("omit-" + index) ? [] : [{ ...item, price: Number(data.get("price-" + index)) }]),
        opportunities: Number(data.get("opportunities")), segment_weights: weights };
      if (!Object.keys(weights).length) throw new Error("Set at least one positive segment weight.");
      if (prices.some((price) => !Number.isFinite(price) || price <= 0) || prices.length > 12 || new Set(prices).size !== prices.length) throw new Error("Enter up to 12 distinct positive prices.");
      const build = (price: number) => ({ ...common, name: target.name.slice(0, 95) + " · " + money(price), product: { ...target, price } });
      const results = prices.length > 1 ? await api<Simulation[]>("/simulations/compare", "POST", { model_id: model.id, scenarios: prices.map(build) }) :
        [await api<Simulation>("/simulations", "POST", { model_id: model.id, ...build(prices[0] ?? target.price) })];
      setComparison(results); setSelected(results[0].id);
    });
  }
  return <>
    <PageTitle eyebrow="SIMULATE / 05" title="Market simulator" description="Change price, product attributes or the competitive set and compare conditional outcomes." />
    <ErrorMessage error={models.error || products.error || saved.error || action.error} />
    <div className="split">
      <Card title="Scenario inputs" hint="Segment weights and opportunity volume are analyst assumptions.">
        {model && product ? <form className="stack" onSubmit={submit}>
          <Field label="Choice model"><select value={model.id} onChange={(e) => { setModelId(e.target.value); setProductId(""); }}>{ready.map((item) => <option key={item.id} value={item.id}>{item.id.slice(0, 8)} · {item.evidence_quality}</option>)}</select></Field>
          <Field label="Base concept"><select value={product.id} onChange={(e) => setProductId(e.target.value)}>{eligibleProducts.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
          <fieldset key={product.id}><legend>Target configuration</legend><AlternativeFields product={product} />
            {product.competitors.map((item, index) => <div className="competitor" key={index}><Field label={item.name + " price (INR)"}><input name={"price-" + index} type="number" defaultValue={item.price} min=".01" max="100000" step=".01" required /></Field>
              <label className="check"><input name={"omit-" + index} type="checkbox" /> Unavailable</label></div>)}
          </fieldset>
          <Field label="Compare prices (optional, comma-separated)"><input name="prices" placeholder="20, 30, 40" /></Field>
          <Field label="Eligible choice opportunities"><input name="opportunities" type="number" min="1" max="100000000" defaultValue="1000" required /></Field>
          <div className="form-grid">{["value", "balanced", "premium"].map((segment) => <Field key={segment} label={segment + " weight"}>
            <input name={segment} type="number" min="0" max="100" step="0.01" defaultValue={product.segment === segment ? "1" : "0"} key={product.id} required />
          </Field>)}</div>
          <button className="button primary" disabled={action.busy}><SlidersHorizontal size={16} />{action.busy ? "Simulating…" : "Run simulation"}</button>
        </form> : <Empty title={model ? "Add a concept to the model’s project" : "A trained choice model is required"} detail="Generate a sandbox panel or train on an approved study." href="/experiments" action="Open consumer lab" />}
      </Card>
      <div className="stack">
        {curve.length > 1 && <Card title="Price comparison" hint="Target share and 90% parameter intervals."><div className="chart"><ResponsiveContainer width="100%" height="100%"><AreaChart data={curve} margin={{ left: -15, right: 8 }}>
          <CartesianGrid stroke="var(--border)" vertical={false} /><XAxis dataKey="price" tickFormatter={money} stroke="var(--muted)" /><YAxis tickFormatter={percent} domain={[0, 1]} stroke="var(--muted)" />
          <Tooltip formatter={(value) => percent(Number(value))} labelFormatter={(value) => money(Number(value))} contentStyle={chartStyle} />
          <Area type="monotone" dataKey="high" stroke="var(--chart-2)" fill="var(--chart-fill)" /><Area type="monotone" dataKey="low" stroke="var(--chart-2)" fill="var(--card)" />
          <Area type="monotone" dataKey="share" stroke="var(--chart-1)" strokeWidth={2.5} fill="transparent" />
        </AreaChart></ResponsiveContainer></div></Card>}
        <Card title="Scenario results" hint="Estimates are conditional on your inputs and the model’s evidence.">
          {current ? <div className="stack"><Field label="Saved scenario"><select value={current.id} onChange={(e) => setSelected(e.target.value)}>
            {(saved.data?.length ? saved.data : comparison).map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}
          </select></Field><ScenarioSummary item={current} /><Link className="button secondary" href="/reports">Generate a report <ArrowRight size={15} /></Link></div>
            : <Empty title="No scenario results yet" detail="Run a simulation to compare product and no-purchase shares." />}
        </Card>
      </div>
    </div>
  </>;
}

export function MarketTwin() {
  const models = useModels();
  const [selection, setSelection] = useState("");
  const ready = models.data?.filter((item) => item.status === "ready") ?? [];
  const id = ready.find((item) => item.id === selection)?.id ?? ready[0]?.id;
  const result = useQuery({ queryKey: ["model", id], queryFn: () => api<Model>("/models/" + id), enabled: Boolean(id) });
  const model = result.data;
  const groups: Record<string, Parameters> = model?.preferences ? { global: model.preferences.global, ...model.preferences.segments } : {};
  return <>
    <PageTitle eyebrow="INTERPRET / 04" title="Market twin" description="Inspect fitted segment preferences, uncertainty and holdout calibration." />
    <ErrorMessage error={models.error || result.error} />
    {id ? <Card title="Model version" hint="Each run records the evidence source and the evaluation split."><div className="actions">
      <select aria-label="Model version" value={id} onChange={(e) => setSelection(e.target.value)}>{ready.map((item) => <option key={item.id} value={item.id}>{item.id.slice(0, 8)} · {item.evidence_quality}</option>)}</select>
      {model && <><Badge>{model.feature_version}</Badge><Badge>{model.test_rows} held-out choices</Badge></>}</div></Card> :
      <Empty title="No trained choice model" detail="Fit a model before reviewing preferences." href="/experiments" action="Open consumer lab" />}
    {model && <div className="split">
      <Card title="Preference coefficients" hint="Local Gaussian approximation. Intervals shown as mean ± 1.645 standard deviations.">
        <div className="table-wrap"><table><thead><tr><th>Segment</th><th>Attribute</th><th>Mean</th><th>90% interval</th></tr></thead><tbody>{Object.entries(groups).flatMap(([name, group]) => group.mean.map((mean, idx) => {
          const radius = 1.645 * Math.sqrt(group.covariance[idx][idx]);
          return <tr key={name + idx}><td>{name} <small>({group.rows})</small></td><td>{model.preferences?.features[idx].replaceAll("_", " ")}</td>
            <td>{mean.toFixed(3)}</td><td>{(mean - radius).toFixed(3)} to {(mean + radius).toFixed(3)}</td></tr>;
        }))}</tbody></table></div>
      </Card>
      <Card title="Held-out evaluation" hint="Scores use the same held-out participants for both models.">
        <div className="table-wrap"><table><thead><tr><th>Model</th><th>Log loss</th><th>Brier</th><th>Accuracy</th></tr></thead>
          <tbody>{Object.entries(model.metrics ?? {}).map(([name, score]) => <tr key={name}><td>{name.replaceAll("_", " ")}</td><td>{score.log_loss.toFixed(3)}</td><td>{score.brier.toFixed(3)}</td><td>{percent(score.accuracy)}</td></tr>)}</tbody></table></div>
        <p className="muted">Confidence vs observed accuracy, segment model</p>
        <div className="chart"><ResponsiveContainer width="100%" height="100%"><LineChart data={model.metrics?.empirical_bayes_laplace?.calibration ?? []} margin={{ left: -10, right: 16 }}>
          <CartesianGrid stroke="var(--border)" /><XAxis dataKey="confidence" type="number" domain={[0, 1]} tickFormatter={percent} stroke="var(--muted)" />
          <YAxis domain={[0, 1]} tickFormatter={percent} stroke="var(--muted)" /><Tooltip contentStyle={chartStyle} formatter={(value) => percent(Number(value))} />
          <Line type="linear" dataKey="accuracy" stroke="var(--chart-1)" strokeWidth={2.5} />
        </LineChart></ResponsiveContainer></div>
        {model.synthetic && <Notice>Synthetic model. Coefficients describe a seeded scenario generator.</Notice>}
      </Card>
    </div>}
  </>;
}

export function Reports() {
  const simulations = useQuery({ queryKey: ["simulations"], queryFn: () => api<Simulation[]>("/simulations") });
  const reports = useQuery({ queryKey: ["reports"], queryFn: () => api<Report[]>("/reports") });
  const action = useAction(() => { void reports.refetch(); });
  return <>
    <PageTitle eyebrow="COMMUNICATE / 06" title="Reports" description="Export scenario assumptions, estimated shares, uncertainty and evidence limitations." />
    <ErrorMessage error={simulations.error || reports.error || action.error} />
    <div className="split">
      <Card title="Create a PDF report" hint="Reports are private to your project.">
        {simulations.data?.length ? <form className="stack" onSubmit={(event) => {
          const data = values(event);
          void action.run(() => api("/reports", "POST", { simulation_id: data.get("simulation") }));
        }}><Field label="Scenario"><select name="simulation">{simulations.data.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></Field>
          <button className="button primary" disabled={action.busy}><Plus size={16} />Generate report</button></form> : <Empty title="Run a simulation first" detail="A saved scenario supplies the report data." href="/simulations" action="Open simulator" />}
      </Card>
      <Card title="Report library">
        {reports.data?.length ? <div className="rows">{reports.data.map((item) => <div className="list-row" key={item.id}><div><strong>{simulations.data?.find((simulation) => simulation.id === item.simulation_id)?.name ?? "Scenario report"}</strong>
          <small>{new Date(item.created).toLocaleDateString()}</small></div><a className="button secondary small" href={"/api/v1/reports/" + item.id + "/download"}><ArrowDownToLine size={15} />PDF</a></div>)}</div> :
          <Empty title="No saved reports" detail="Generate one from a saved scenario." />}
      </Card>
    </div>
  </>;
}

type Dataset = { id: string; name: string; source_url: string | null; license: string; version: string; download_status: string; records: number | null; limitations: string };
export function Research({ user }: { user: User }) {
  const enabled = user.role === "researcher";
  const sources = useQuery({ queryKey: ["datasets"], queryFn: () => api<Dataset[]>("/research/datasets"), enabled });
  const runs = useQuery({ queryKey: ["research-runs"], queryFn: () => api<Model[]>("/research/training-runs"), enabled });
  const experiments = useQuery({ queryKey: ["research-ablation"], queryFn: () => api<Record<string, unknown>>("/research/ablation"), enabled });
  const action = useAction();
  return <>
    <PageTitle eyebrow="REPRODUCE / 07" title="Research" description="Inspect dataset provenance, training versions and evidence-specific experiment results." action={enabled &&
      <button className="button secondary" disabled={action.busy} onClick={() => action.run(async () => {
        const data = await api("/research/exports");
        const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
        const link = document.createElement("a"); link.href = url; link.download = "demandtwin-research.json"; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
      })}><ArrowDownToLine size={16} />Export metadata</button>} />
    {!enabled ? <Empty title="Researcher access required" detail="Use the configured research code when registering a researcher account." /> : <>
      <ErrorMessage error={sources.error || runs.error || experiments.error || action.error} />
      <Card title="Dataset catalogue" hint="Access status, permitted use and limitations by source.">
        <div className="table-wrap"><table><thead><tr><th>Dataset</th><th>Version and rights</th><th>Access status</th><th>Limitations</th></tr></thead>
          <tbody>{sources.data?.map((item) => <tr key={item.id}><td>{item.source_url ? <a href={item.source_url} target="_blank" rel="noreferrer">{item.name}</a> : item.name}</td>
            <td>{item.version}<small>{item.license}</small></td><td>{item.download_status}<small>{item.records == null ? "" : number(item.records) + " records"}</small></td><td>{item.limitations}</td></tr>)}</tbody></table></div>
      </Card>
      <div className="split"><Card title="Training runs">{runs.data?.length ? <div className="rows">{runs.data.map((item) => <div className="list-row" key={item.id}><div><strong>{item.id}</strong><small>{item.evidence_quality ?? "Awaiting model output"}</small></div><Badge>{item.status}</Badge></div>)}</div> :
        <Empty title="No runs in this workspace" detail="Train a model in the consumer lab." />}</Card>
        <Card title="Experiment and ablation records" hint="Generated by the offline reproducible experiment suite."><pre className="json">{JSON.stringify(experiments.data ?? {}, null, 2)}</pre></Card></div>
    </>}
  </>;
}
