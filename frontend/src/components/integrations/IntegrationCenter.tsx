import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Bot,
  Check,
  CheckCircle2,
  ChevronDown,
  CircleDollarSign,
  KeyRound,
  Link2,
  PlugZap,
  RefreshCw,
  ShieldCheck,
  TriangleAlert,
  UserRoundCheck,
  X,
} from "lucide-react";

import type { AgentProfile } from "../../lib/agentTypes";
import { api } from "../../lib/api";
import type { Integration, IntegrationRequirement } from "../../lib/missionTypes";
import type { Project } from "../../lib/projectTypes";

export function IntegrationCenter({ agents }: { agents: AgentProfile[] }) {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [projectId, setProjectId] = useState("");
  const [requirements, setRequirements] = useState<IntegrationRequirement[]>([]);
  const [expanded, setExpanded] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState<string | null>(null);
  const [verification, setVerification] = useState<Record<string, { ok: boolean; detail: string }>>({});

  const loadBase = useCallback(async () => {
    try {
      const [catalog, portfolio] = await Promise.all([
        api<Integration[]>("/api/v1/integrations"),
        api<Project[]>("/api/v1/projects"),
      ]);
      setIntegrations(catalog);
      setProjects(portfolio);
      setProjectId((current) => current || portfolio[0]?.id || "");
      setError(null);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Integrationen konnten nicht geladen werden");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadRequirements = useCallback(async () => {
    if (!projectId) {
      setRequirements([]);
      return;
    }
    try {
      setRequirements(await api<IntegrationRequirement[]>(`/api/v1/projects/${projectId}/integration-requirements`));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Anforderungen konnten nicht geladen werden");
    }
  }, [projectId]);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadBase(), 0);
    return () => window.clearTimeout(timer);
  }, [loadBase]);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadRequirements(), 0);
    return () => window.clearTimeout(timer);
  }, [loadRequirements]);

  const requiredIds = useMemo(() => new Set(requirements.map((item) => item.integration_id)), [requirements]);
  const configured = integrations.filter((item) => item.ready).length;
  const blockers = requirements.filter((item) => item.required && !item.ready).length;

  async function toggleRequirement(integration: Integration) {
    if (!projectId) return;
    if (requiredIds.has(integration.id)) {
      await api<void>(`/api/v1/projects/${projectId}/integration-requirements/${integration.id}`, { method: "DELETE" });
    } else {
      await api<IntegrationRequirement>(`/api/v1/projects/${projectId}/integration-requirements`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ integration_id: integration.id, purpose: "Für dieses Projekt benötigt" }),
      });
    }
    await loadRequirements();
  }

  async function verify(integration: Integration) {
    setVerifying(integration.id);
    try {
      const result = await api<{ ok: boolean; detail: string }>(`/api/v1/integrations/${integration.id}/verify`, { method: "POST" });
      setVerification((current) => ({ ...current, [integration.id]: result }));
    } catch (reason) {
      setVerification((current) => ({ ...current, [integration.id]: { ok: false, detail: reason instanceof Error ? reason.message : "Prüfung fehlgeschlagen" } }));
    } finally {
      setVerifying(null);
    }
  }

  return (
    <div className="mt-7 space-y-5">
      {error && <div className="flex items-center gap-2 rounded-xl border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-200"><TriangleAlert size={16} />{error}</div>}
      <section className="grid grid-cols-2 gap-3 xl:grid-cols-4">
        <IntegrationMetric label="Integrationen" value={integrations.length} detail="lokaler Katalog" icon={<PlugZap size={17} />} />
        <IntegrationMetric label="Konfiguriert" value={configured} detail="Secrets und IDs vorhanden" icon={<CheckCircle2 size={17} />} />
        <IntegrationMetric label="Projektanforderungen" value={requirements.length} detail="für das gewählte Projekt" icon={<Link2 size={17} />} />
        <IntegrationMetric label="Fehlende Zugänge" value={blockers} detail={blockers ? "blockieren Ausführung" : "keine Blocker"} icon={<KeyRound size={17} />} alert={blockers > 0} />
      </section>

      <section className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4 sm:p-5">
        <div className="flex flex-wrap items-center justify-between gap-4 border-b border-white/[0.07] pb-4">
          <div>
            <p className="text-[10px] uppercase tracking-[0.16em] text-cyan-400">Account & Secret Readiness</p>
            <h2 className="mt-1 text-lg font-semibold">Integrationszentrum</h2>
            <p className="mt-1 text-xs text-slate-600">Nur Konfigurationsstatus – Secret-Werte verlassen niemals die lokale Umgebung.</p>
          </div>
          <div className="flex items-center gap-2">
            <select value={projectId} onChange={(event) => setProjectId(event.target.value)} className="max-w-64 rounded-lg border border-white/[0.08] bg-[#080b10] px-3 py-2 text-xs text-slate-400 outline-none">
              <option value="">Kein Projekt gewählt</option>
              {projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}
            </select>
            <button onClick={() => { void loadBase(); void loadRequirements(); }} className="mc-icon-button h-9 w-9 rounded-xl text-slate-500" title="Status neu prüfen"><RefreshCw size={14} className={loading ? "animate-spin" : ""} /></button>
          </div>
        </div>

        <div className="mt-4 grid gap-3 xl:grid-cols-2">
          {integrations.map((integration) => {
            const owner = agents.find((agent) => agent.id === integration.owner_agent);
            const required = requiredIds.has(integration.id);
            const isExpanded = expanded === integration.id;
            const verified = verification[integration.id];
            const displayReady = verified ? verified.ok : integration.ready;
            const displayStatus = verified ? (verified.ok ? "geprüft" : "Fehler") : (integration.ready ? "konfiguriert" : "fehlt");
            return (
              <article key={integration.id} className={`mc-panel rounded-2xl border p-4 ${required ? "border-cyan-300/20 bg-cyan-300/[0.035]" : "border-white/[0.065] bg-black/10"}`}>
                <div className="flex items-start gap-3">
                  <div className={`grid h-9 w-9 shrink-0 place-items-center rounded-xl ${displayReady ? "bg-emerald-400/10 text-emerald-300" : "bg-amber-300/10 text-amber-300"}`}>{displayReady ? <Check size={17} /> : <KeyRound size={16} />}</div>
                  <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2"><h3 className="text-sm font-semibold">{integration.name}</h3><span className={`rounded px-1.5 py-0.5 text-[9px] font-semibold uppercase ${displayReady ? "bg-emerald-400/10 text-emerald-300" : "bg-amber-300/10 text-amber-300"}`}>{displayStatus}</span></div>
                    <p className="mt-1 text-xs leading-5 text-slate-500">{integration.description}</p>
                  </div>
                  <button onClick={() => setExpanded(isExpanded ? null : integration.id)} className="mc-icon-button h-8 w-8 rounded-xl text-slate-600 hover:text-slate-300"><ChevronDown size={15} className={`transition-transform duration-300 ${isExpanded ? "rotate-180" : ""}`} /></button>
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-2 text-[10px] text-slate-600">
                  <span className="flex items-center gap-1 rounded bg-white/[0.035] px-2 py-1"><Bot size={11} />{owner?.name ?? integration.owner_agent}</span>
                  <span className="flex items-center gap-1 rounded bg-white/[0.035] px-2 py-1"><UserRoundCheck size={11} />{integration.account_required ? "Konto erforderlich" : "Kein Konto nötig"}</span>
                  <span className="flex items-center gap-1 rounded bg-white/[0.035] px-2 py-1"><CircleDollarSign size={11} />{integration.cost}</span>
                </div>
                {isExpanded && (
                  <div className="mt-4 grid gap-4 border-t border-white/[0.06] pt-4 md:grid-cols-2">
                    <div><p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Secret-Status</p><div className="mt-2 space-y-1.5">{integration.secrets.length ? integration.secrets.map((secret) => <div key={secret.names.join("|")} className="flex items-center justify-between rounded-lg bg-black/20 px-2.5 py-2 text-[10px]"><code className="text-slate-500">{secret.names.join(" oder ")}</code>{secret.configured ? <ShieldCheck size={13} className="text-emerald-400" /> : <X size={13} className="text-amber-300" />}</div>) : <p className="text-[10px] text-emerald-400/70">Keine Zugangsdaten erforderlich.</p>}</div></div>
                    <div><p className="text-[10px] font-semibold uppercase tracking-wider text-slate-600">Einrichtung</p><ol className="mt-2 space-y-1.5">{integration.setup_steps.map((step, index) => <li key={step} className="flex gap-2 text-[10px] leading-4 text-slate-500"><span className="text-cyan-500">{index + 1}.</span>{step}</li>)}</ol></div>
                    {integration.configurable_keys.length > 0 && <SecretConfiguration integration={integration} onSaved={loadBase} />}
                  </div>
                )}
                {verification[integration.id] && <p className={`mt-3 rounded-lg px-2.5 py-2 text-[10px] ${verification[integration.id].ok ? "bg-emerald-400/[0.07] text-emerald-300" : "bg-rose-400/[0.07] text-rose-300"}`}>{verification[integration.id].detail}</p>}
                <div className="mt-4 flex items-center justify-between border-t border-white/[0.055] pt-3"><span className="text-[10px] text-slate-700">{required ? "Für Projekt eingeplant" : "Nicht für Projekt benötigt"}</span><span className="flex gap-2"><button disabled={verifying === integration.id} onClick={() => void verify(integration)} className="mc-button flex items-center gap-1.5 rounded-xl px-2.5 py-1.5 text-[10px] font-semibold text-slate-400 hover:text-emerald-300 disabled:opacity-30">{verifying === integration.id ? <RefreshCw size={11} className="animate-spin" /> : <ShieldCheck size={11} />}Verbindung testen</button><button disabled={!projectId} onClick={() => void toggleRequirement(integration)} className={`mc-button rounded-xl px-2.5 py-1.5 text-[10px] font-semibold disabled:opacity-30 ${required ? "text-cyan-300 hover:text-rose-300" : "text-slate-400 hover:text-cyan-300"}`}>{required ? "Entfernen" : "Projekt hinzufügen"}</button></span></div>
              </article>
            );
          })}
        </div>
      </section>
    </div>
  );
}

function SecretConfiguration({ integration, onSaved }: { integration: Integration; onSaved: () => Promise<void> }) {
  const [values, setValues] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const sensitive = (key: string) => /TOKEN|PASSWORD|SECRET|API_KEY/.test(key);

  async function save() {
    const payload = Object.fromEntries(Object.entries(values).filter(([, value]) => value.trim()));
    if (Object.keys(payload).length === 0) return;
    setSaving(true);
    setMessage(null);
    try {
      await api<{ saved_keys: string[] }>(`/api/v1/integrations/${integration.id}/configuration`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ values: payload }),
      });
      setValues({});
      setMessage("Lokal gespeichert und für die Runtime aktiviert.");
      await onSaved();
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "Konfiguration konnte nicht gespeichert werden");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-xl border border-cyan-300/10 bg-cyan-300/[0.025] p-3 md:col-span-2">
      <div className="flex items-center gap-2"><KeyRound size={12} className="text-cyan-300" /><p className="text-[10px] font-semibold uppercase tracking-wider text-cyan-300/80">Sicher lokal konfigurieren</p></div>
      <div className="mt-3 grid gap-2 md:grid-cols-2">
        {integration.configurable_keys.map((key) => (
          <label key={key} className="text-[9px] text-slate-600">
            {key}
            <input
              type={sensitive(key) ? "password" : "text"}
              autoComplete="off"
              value={values[key] ?? ""}
              onChange={(event) => setValues((current) => ({ ...current, [key]: event.target.value }))}
              placeholder={integration.secrets.some((secret) => secret.configured && secret.names.includes(key)) ? "Bereits konfiguriert" : "Noch nicht gesetzt"}
              className="mt-1 w-full rounded-lg border border-white/[0.07] bg-[#080b10] px-2.5 py-2 text-[10px] text-slate-300 outline-none focus:border-cyan-300/30"
            />
          </label>
        ))}
      </div>
      <div className="mt-3 flex items-center justify-between gap-3"><p className="text-[9px] text-slate-600">Werte werden nur in der lokalen, ignorierten .env gespeichert.</p><button disabled={saving || !Object.values(values).some((value) => value.trim())} onClick={() => void save()} className="flex shrink-0 items-center gap-1.5 rounded-lg bg-cyan-300 px-3 py-2 text-[10px] font-semibold text-slate-950 disabled:opacity-30">{saving ? <RefreshCw size={11} className="animate-spin" /> : <ShieldCheck size={11} />}Speichern</button></div>
      {message && <p className="mt-2 text-[9px] text-slate-400">{message}</p>}
    </div>
  );
}

function IntegrationMetric({ label, value, detail, icon, alert = false }: { label: string; value: number; detail: string; icon: React.ReactNode; alert?: boolean }) {
  return <div className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4"><div className={`flex items-center justify-between text-xs ${alert ? "text-amber-300" : "text-slate-500"}`}><span>{label}</span>{icon}</div><p className="mt-3 text-xl font-semibold">{value}</p><p className="mt-1 text-[11px] text-slate-600">{detail}</p></div>;
}
