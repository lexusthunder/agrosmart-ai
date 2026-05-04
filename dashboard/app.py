"""Dashboard Gradio AgroSmart AI — design premium, multi-tab, integrare LLM + 3D + multi-model."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import gradio as gr
import httpx
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from app.config import settings

API = settings.dashboard_api_url

# Tema Plotly comuna pentru consistency
PLOTLY_TEMPLATE = "plotly_white"
COLORS = {
    "primary": "#0F766E",      # teal profund
    "accent": "#84CC16",       # lime
    "warning": "#F59E0B",      # amber
    "danger": "#DC2626",       # red
    "ink": "#0F172A",          # slate-900
    "muted": "#64748B",        # slate-500
    "soft": "#F1F5F9",         # slate-100
}


# ---- helpers ---------------------------------------------------------- #


def _fmt_response(payload: dict[str, Any], status_code: int) -> str:
    return f"HTTP {status_code}\n\n{json.dumps(payload, indent=2, ensure_ascii=False)}"


def login(username: str, password: str) -> tuple[str, str]:
    """Login -> returneaza (token, mesaj)."""
    if not username or not password:
        return "", "❌ Introdu username si parola"
    try:
        r = httpx.post(
            f"{API}/auth/login",
            data={"username": username, "password": password},
            timeout=10.0,
        )
    except httpx.RequestError as exc:
        return "", f"❌ Eroare conexiune API: {exc}"
    if r.status_code != 200:
        return "", f"❌ {r.json().get('detail', 'Login esuat')}"
    token = r.json()["access_token"]
    return token, f"✅ Autentificat ca **{username}**. Acum poti folosi orice tab."


def analiza(
    token: str,
    lat: float,
    lon: float,
    ph: float,
    umiditate: float,
    temperatura: float,
) -> tuple[str, str, str, str]:
    if not token:
        return "", "—", "❌ Trebuie sa te autentifici intai", ""

    body = {
        "lat": float(lat),
        "lon": float(lon),
        "ph": float(ph),
        "umiditate": float(umiditate),
        "temperatura": float(temperatura),
    }
    try:
        r = httpx.post(
            f"{API}/sensors/analiza",
            headers={"Authorization": f"Bearer {token}"},
            json=body,
            timeout=10.0,
        )
    except httpx.RequestError as exc:
        return "", "—", f"❌ Eroare conexiune: {exc}", ""

    if r.status_code not in (200, 201):
        return "", "—", _fmt_response(r.json(), r.status_code), ""

    data = r.json()
    actiune = data["actiune"]
    motiv = data["motiv"]
    ph_status = data["ph_status"]
    alerta_label = "🚨 ALERTA" if data["alerta"] else "✅ NORMAL"

    badge = (
        f"## {actiune}\n\n"
        f"**Motiv:** {motiv}\n\n"
        f"**Status pH:** `{ph_status}`  ·  **Status:** {alerta_label}"
    )
    return token, badge, _fmt_response(data, r.status_code), ph_status


def listeaza_istoric(token: str, limit: int) -> str:
    if not token:
        return "❌ Trebuie sa te autentifici intai"
    try:
        r = httpx.get(
            f"{API}/sensors/",
            headers={"Authorization": f"Bearer {token}"},
            params={"limit": limit},
            timeout=10.0,
        )
    except httpx.RequestError as exc:
        return f"❌ {exc}"
    if r.status_code != 200:
        return _fmt_response(r.json(), r.status_code)

    rows = r.json()
    if not rows:
        return "_Nu exista citiri inca._"

    lines = [
        "| ID | Timestamp | pH | Umid % | Temp °C | Actiune |",
        "|---:|-----------|---:|-------:|--------:|---------|",
    ]
    for row in rows:
        ts = datetime.fromisoformat(row["timestamp"]).strftime("%Y-%m-%d %H:%M")
        flag = "🚨 " if row["alerta"] else ""
        lines.append(
            f"| {row['id']} | {ts} | {row['ph']:.2f} | "
            f"{row['umiditate']:.1f} | {row['temperatura']:.1f} | "
            f"{flag}{row['actiune']} |"
        )
    return "\n".join(lines)


def summary_md(token: str) -> str:
    if not token:
        return "❌ Trebuie sa te autentifici intai"
    try:
        r = httpx.get(
            f"{API}/analytics/summary",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )
    except httpx.RequestError as exc:
        return f"❌ {exc}"
    if r.status_code != 200:
        return _fmt_response(r.json(), r.status_code)

    s = r.json()
    actiuni_md = "\n".join(f"- **{k}** → {v}" for k, v in s["actiuni_frecvente"].items()) or "_-_"
    return (
        f"### Statistici sistem\n\n"
        f"| | |\n|---|---:|\n"
        f"| Total citiri | **{s['total_citiri']}** |\n"
        f"| Ultimele 24h | **{s['citiri_24h']}** |\n"
        f"| % alerte | **{s['procent_alerte']}%** |\n"
        f"| pH mediu | **{s['ph_mediu']}** |\n"
        f"| Umiditate medie | **{s['umiditate_medie']}%** |\n"
        f"| Temperatura medie | **{s['temperatura_medie']}°C** |\n\n"
        f"### Actiuni frecvente\n{actiuni_md}"
    )


def hero_kpis(token: str) -> str:
    """Banner KPIs in homepage — date live."""
    if not token:
        return (
            "<div class='hero'>"
            "<h2>🔐 Autentifica-te pentru a vedea datele live</h2>"
            "<p>Tab-ul <b>Autentificare</b> sus-stanga. Credentiale: fermier / agrosmart2025.</p>"
            "</div>"
        )
    try:
        r = httpx.get(
            f"{API}/analytics/summary",
            headers={"Authorization": f"Bearer {token}"},
            timeout=8.0,
        )
        s = r.json() if r.status_code == 200 else {}
    except Exception:  # noqa: BLE001
        s = {}

    return f"""
<div class='kpi-grid'>
  <div class='kpi-card kpi-primary'>
    <div class='kpi-label'>Total citiri</div>
    <div class='kpi-value'>{s.get('total_citiri', '—')}</div>
    <div class='kpi-sub'>↑ {s.get('citiri_24h', 0)} in ultimele 24h</div>
  </div>
  <div class='kpi-card kpi-accent'>
    <div class='kpi-label'>Acuratete ML</div>
    <div class='kpi-value'>99.55%</div>
    <div class='kpi-sub'>ExtraTrees · 22 culturi</div>
  </div>
  <div class='kpi-card kpi-warning'>
    <div class='kpi-label'>% Alerte</div>
    <div class='kpi-value'>{s.get('procent_alerte', 0)}%</div>
    <div class='kpi-sub'>din toate citirile</div>
  </div>
  <div class='kpi-card kpi-info'>
    <div class='kpi-label'>Umiditate medie</div>
    <div class='kpi-value'>{s.get('umiditate_medie', '—')}%</div>
    <div class='kpi-sub'>pH mediu {s.get('ph_mediu', '—')}</div>
  </div>
</div>
"""


def harta_html(token: str) -> str:
    """Fetch harta Folium server-side (cu auth) si returneaza HTML inline.

    Iframe nu functioneaza pentru ca nu transporta JWT-ul. Server-side fetch
    aduce HTML-ul deja randat de Folium si il afiseaza direct.
    """
    if not token:
        return "<p style='padding:1rem'>❌ Trebuie sa te autentifici intai.</p>"
    try:
        r = httpx.get(
            f"{API}/sensors/map",
            headers={"Authorization": f"Bearer {token}"},
            timeout=20.0,
        )
    except httpx.RequestError as exc:
        return f"<p style='padding:1rem;color:#DC2626'>❌ Eroare conexiune: {exc}</p>"
    if r.status_code != 200:
        return f"<p style='padding:1rem;color:#DC2626'>❌ HTTP {r.status_code}: {r.text[:200]}</p>"
    # Foloseste srcdoc — iframe-ul renderaza HTML-ul direct, fara request extern,
    # deci nu trebuie sa transporte JWT.
    safe_html = r.text.replace('"', "&quot;")
    return (
        f'<iframe srcdoc="{safe_html}" '
        f'style="width:100%;height:640px;border:0;border-radius:16px;'
        f'box-shadow:0 8px 32px rgba(15,118,110,0.12)" '
        f'title="Harta AgroSmart" sandbox="allow-scripts allow-same-origin allow-popups"></iframe>'
    )


def trend_chart(token: str, metric: str, days: int) -> go.Figure:
    fig = go.Figure()
    if not token:
        fig.update_layout(title="❌ Autentifica-te in tab-ul Autentificare", height=400)
        return fig
    try:
        r = httpx.get(
            f"{API}/analytics/timeseries",
            headers={"Authorization": f"Bearer {token}"},
            params={"metric": metric, "days": int(days)},
            timeout=10.0,
        )
    except httpx.RequestError as exc:
        fig.update_layout(title=f"❌ Eroare conexiune: {exc}", height=400)
        return fig

    if r.status_code != 200:
        fig.update_layout(title=f"❌ HTTP {r.status_code}: {r.text[:120]}", height=400)
        return fig

    data = r.json()
    points = data.get("points", [])
    if not points:
        fig.update_layout(title=f"Nu exista date pentru {metric} in ultimele {days} zile", height=400)
        return fig

    df = pd.DataFrame(points)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    label_map = {"ph": "pH", "umiditate": "Umiditate (%)", "temperatura": "Temperatura (°C)"}
    rgba_map = {
        "ph": ("#7B3F00", "rgba(123, 63, 0, 0.18)"),
        "umiditate": (COLORS["primary"], "rgba(15, 118, 110, 0.18)"),
        "temperatura": (COLORS["danger"], "rgba(220, 38, 38, 0.18)"),
    }
    line_color, fill_rgba = rgba_map.get(metric, (COLORS["primary"], "rgba(15, 118, 110, 0.18)"))

    fig = px.area(
        df, x="timestamp", y="valoare",
        title=f"📈 {label_map.get(metric, metric)} — ultimele {days} zile ({len(df)} citiri)",
        labels={"timestamp": "Timp", "valoare": label_map.get(metric, metric)},
        template=PLOTLY_TEMPLATE,
    )
    fig.update_traces(
        line_color=line_color,
        line_width=3,
        fillcolor=fill_rgba,
        mode="lines+markers",
        marker=dict(size=6, line=dict(color="white", width=1.5)),
    )
    fig.update_layout(
        height=470,
        font=dict(family="Inter, system-ui, sans-serif", size=13),
        title_font_size=18,
        title_font_color=COLORS["ink"],
        xaxis=dict(showgrid=True, gridcolor="#E2E8F0"),
        yaxis=dict(showgrid=True, gridcolor="#E2E8F0"),
        hoverlabel=dict(bgcolor="white", font_size=13),
        margin=dict(l=20, r=20, t=70, b=20),
    )
    return fig


def predict_crop_ui(
    token: str,
    n: float, p_val: float, k: float,
    temp: float, hum: float, ph: float, rain: float,
    model_ales: str = "auto",
) -> str:
    if not token:
        return "❌ Trebuie sa te autentifici intai"
    body: dict[str, Any] = {
        "N": float(n), "P": float(p_val), "K": float(k),
        "temperature": float(temp), "humidity": float(hum),
        "ph": float(ph), "rainfall": float(rain),
    }
    if model_ales and model_ales != "auto":
        body["model_ales"] = model_ales
    try:
        r = httpx.post(
            f"{API}/ml/predict-crop",
            headers={"Authorization": f"Bearer {token}"},
            json=body, timeout=15.0,
        )
    except httpx.RequestError as exc:
        return f"❌ Eroare conexiune: {exc}"

    if r.status_code != 200:
        return _fmt_response(r.json(), r.status_code)

    data = r.json()
    top3 = "\n".join(f"- **{name}** — {prob*100:.2f}%" for name, prob in data["top_3"])
    return (
        f"## 🌾 Cultura recomandata: **{data['cultura_recomandata'].upper()}**\n\n"
        f"<div class='ml-result'>"
        f"<b>Model folosit:</b> <code>{data.get('model_folosit', 'auto')}</code> &nbsp;•&nbsp; "
        f"<b>Incredere:</b> <span class='confidence'>{data['incredere']*100:.2f}%</span>"
        f"</div>\n\n"
        f"### Top 3 candidate\n{top3}"
    )


def model_comparison_chart(token: str) -> go.Figure:
    """Bar chart cu performanta modelelor."""
    fig = go.Figure()
    if not token:
        fig.update_layout(title="❌ Autentifica-te intai", height=400)
        return fig
    try:
        r = httpx.get(f"{API}/ml/models", headers={"Authorization": f"Bearer {token}"}, timeout=10.0)
    except httpx.RequestError as exc:
        fig.update_layout(title=f"❌ {exc}", height=400)
        return fig
    if r.status_code != 200:
        fig.update_layout(title=f"❌ HTTP {r.status_code}", height=400)
        return fig

    data = r.json()
    metrics = data.get("metrics", {})
    if not metrics:
        fig.update_layout(title="Nu am gasit metrici", height=400)
        return fig

    names = list(metrics.keys())
    accs = [metrics[n]["accuracy"] * 100 for n in names]
    f1s = [metrics[n]["f1_macro"] * 100 for n in names]
    best = data.get("best", "")
    bar_colors = [COLORS["accent"] if n == best else COLORS["primary"] for n in names]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=names, y=accs, name="Accuracy %",
        marker_color=bar_colors,
        text=[f"{a:.2f}%" for a in accs], textposition="outside",
    ))
    fig.add_trace(go.Bar(
        x=names, y=f1s, name="F1 macro %",
        marker_color=COLORS["warning"], opacity=0.7,
        text=[f"{f:.2f}%" for f in f1s], textposition="outside",
    ))
    fig.update_layout(
        title=f"🏆 Comparatie modele ML — castigator: {best}",
        template=PLOTLY_TEMPLATE,
        barmode="group",
        height=470,
        font=dict(family="Inter, system-ui, sans-serif", size=13),
        title_font_size=18,
        yaxis=dict(range=[85, 102], title="Procent (%)", showgrid=True, gridcolor="#E2E8F0"),
        xaxis=dict(showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        margin=dict(l=20, r=20, t=70, b=60),
    )
    return fig


def view_3d_scatter(token: str) -> go.Figure:
    """Plot Plotly 3D — pH x Umiditate x Temperatura, color by status."""
    fig = go.Figure()
    if not token:
        fig.update_layout(title="❌ Autentifica-te in tab-ul Autentificare", height=600)
        return fig
    try:
        r = httpx.get(
            f"{API}/sensors/", headers={"Authorization": f"Bearer {token}"},
            params={"limit": 500}, timeout=15.0,
        )
    except httpx.RequestError as exc:
        fig.update_layout(title=f"❌ {exc}", height=600)
        return fig
    if r.status_code != 200:
        fig.update_layout(title=f"❌ HTTP {r.status_code}", height=600)
        return fig

    rows = r.json()
    if not rows:
        fig.update_layout(title="Nu exista citiri inca", height=600)
        return fig

    df = pd.DataFrame(rows)

    def _status(row) -> str:
        if row["alerta"]:
            return "ALERTA"
        if str(row["actiune"]).upper().startswith("OK"):
            return "OK"
        return "ACTIUNE"

    df["status"] = df.apply(_status, axis=1)
    color_map = {"OK": COLORS["primary"], "ACTIUNE": COLORS["warning"], "ALERTA": COLORS["danger"]}

    fig = px.scatter_3d(
        df, x="ph", y="umiditate", z="temperatura",
        color="status", color_discrete_map=color_map,
        hover_data=["id", "actiune", "lat", "lon"],
        title=f"🌐 Spatiu 3D senzori — pH × Umiditate × Temperatura ({len(df)} citiri)",
        labels={"ph": "pH", "umiditate": "Umiditate (%)", "temperatura": "Temp (°C)"},
        template=PLOTLY_TEMPLATE,
    )
    fig.update_traces(marker=dict(size=7, opacity=0.85, line=dict(color="white", width=1)))
    fig.update_layout(
        height=620,
        font=dict(family="Inter, system-ui, sans-serif", size=13),
        title_font_size=18,
        scene=dict(
            xaxis=dict(title="pH", backgroundcolor="#FAFBF6", gridcolor="#CBD5E1"),
            yaxis=dict(title="Umiditate (%)", backgroundcolor="#F0F9F4", gridcolor="#CBD5E1"),
            zaxis=dict(title="Temperatura (°C)", backgroundcolor="#FAFBF6", gridcolor="#CBD5E1"),
            camera=dict(eye=dict(x=1.6, y=1.6, z=1.0)),
        ),
        legend=dict(orientation="h", yanchor="top", y=1.05, xanchor="center", x=0.5),
        margin=dict(l=0, r=0, t=70, b=0),
    )
    return fig


def chat_send(token: str, message: str, history: list) -> tuple[list, str, str]:
    """Trimite mesaj la /ml/chat. Returneaza (history, msg_clear, last_reply_pentru_tts)."""
    history = history or []
    if not token:
        history = history + [
            {"role": "user", "content": message or ""},
            {"role": "assistant", "content": "❌ Te rog autentifica-te in tab-ul Autentificare."},
        ]
        return history, "", ""
    if not (message or "").strip():
        return history, "", ""

    api_history = [
        {"role": h.get("role"), "content": h.get("content")}
        for h in history if h.get("role") in ("user", "assistant")
    ]
    body = {"intrebare": message, "istoric": api_history}
    try:
        r = httpx.post(
            f"{API}/ml/chat",
            headers={"Authorization": f"Bearer {token}"},
            json=body, timeout=60.0,
        )
    except httpx.RequestError as exc:
        reply = f"❌ Eroare conexiune: {exc}"
    else:
        if r.status_code != 200:
            reply = f"❌ HTTP {r.status_code}: {r.text[:200]}"
        else:
            data = r.json()
            reply = data.get("raspuns", "_(fara raspuns)_")

    new_history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": reply},
    ]
    return new_history, "", reply


def voice_chat(token: str, audio_path: str | None, history: list) -> tuple[list, str, str | None]:
    """Trimite audio -> Whisper transcribe + LLM -> chat. Returneaza (history, transcript, audio_for_tts)."""
    history = history or []
    if not token:
        history = history + [
            {"role": "user", "content": "🎤 (audio)"},
            {"role": "assistant", "content": "❌ Te rog autentifica-te in tab-ul Autentificare."},
        ]
        return history, "", ""
    if not audio_path:
        return history, "", ""

    # Trimite audio la /ml/transcribe pentru text
    try:
        with open(audio_path, "rb") as f:
            r = httpx.post(
                f"{API}/ml/transcribe",
                headers={"Authorization": f"Bearer {token}"},
                files={"audio": ("rec.wav", f, "audio/wav")},
                timeout=120.0,
            )
    except httpx.RequestError as exc:
        history = history + [
            {"role": "user", "content": "🎤 (audio)"},
            {"role": "assistant", "content": f"❌ Eroare transcribere: {exc}"},
        ]
        return history, "", ""

    if r.status_code != 200:
        history = history + [
            {"role": "user", "content": "🎤 (audio)"},
            {"role": "assistant", "content": f"❌ HTTP {r.status_code}: {r.text[:200]}"},
        ]
        return history, "", ""

    transcript = r.json().get("transcript", "").strip()
    if not transcript:
        history = history + [
            {"role": "user", "content": "🎤 (audio)"},
            {"role": "assistant", "content": "🤔 N-am inteles ce ai spus. Mai incearca."},
        ]
        return history, "", ""

    # Trimite transcriptul la chat
    new_history, _, reply = chat_send(token, transcript, history)
    return new_history, transcript, reply


# ---- UI ---------------------------------------------------------------- #

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

.gradio-container {
    max-width: 1280px !important;
    font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
}

#hero-banner {
    background: linear-gradient(135deg, #0F766E 0%, #14B8A6 50%, #84CC16 100%);
    color: white;
    padding: 2.5rem 2rem;
    border-radius: 24px;
    margin-bottom: 1.5rem;
    box-shadow: 0 20px 60px rgba(15, 118, 110, 0.25);
    position: relative;
    overflow: hidden;
}
#hero-banner::before {
    content: '';
    position: absolute;
    inset: 0;
    background: radial-gradient(circle at 80% 20%, rgba(255,255,255,0.15) 0%, transparent 50%);
    pointer-events: none;
}
#hero-banner h1 {
    font-size: 2.4rem !important;
    font-weight: 800 !important;
    margin: 0 !important;
    letter-spacing: -0.02em;
    color: white !important;
}
#hero-banner p {
    color: rgba(255,255,255,0.92) !important;
    font-size: 1.05rem;
    margin-top: 0.5rem !important;
}

.kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 16px;
    margin: 1rem 0 1.5rem 0;
}
.kpi-card {
    background: white;
    border-radius: 18px;
    padding: 1.25rem 1.5rem;
    box-shadow: 0 4px 24px rgba(15, 23, 42, 0.06);
    border: 1px solid rgba(15, 23, 42, 0.05);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
.kpi-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 40px rgba(15, 23, 42, 0.10);
}
.kpi-label {
    font-size: 0.78rem;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    color: #64748B;
    font-weight: 600;
}
.kpi-value {
    font-size: 2.2rem;
    font-weight: 800;
    color: #0F172A;
    line-height: 1.1;
    margin: 4px 0;
}
.kpi-sub {
    font-size: 0.82rem;
    color: #94A3B8;
}
.kpi-primary { border-top: 4px solid #0F766E; }
.kpi-accent { border-top: 4px solid #84CC16; }
.kpi-warning { border-top: 4px solid #F59E0B; }
.kpi-info { border-top: 4px solid #06B6D4; }

.action-card {
    background: linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 100%);
    padding: 1.5rem 1.75rem;
    border-radius: 16px;
    border-left: 6px solid #0F766E;
    box-shadow: 0 4px 16px rgba(15, 118, 110, 0.08);
}
.action-card h2 {
    color: #064E3B !important;
    margin: 0 0 0.5rem 0 !important;
    font-size: 1.6rem !important;
    font-weight: 700;
}

.ml-result {
    background: #F8FAFC;
    padding: 1rem 1.25rem;
    border-radius: 12px;
    margin: 0.5rem 0;
    border: 1px solid #E2E8F0;
}
.confidence {
    color: #15803D;
    font-weight: 700;
    font-size: 1.1em;
}

button.lg.primary {
    background: linear-gradient(135deg, #0F766E 0%, #14B8A6 100%) !important;
    border: 0 !important;
    color: white !important;
    font-weight: 600 !important;
    box-shadow: 0 4px 12px rgba(15, 118, 110, 0.25) !important;
    transition: all 0.2s !important;
}
button.lg.primary:hover {
    transform: translateY(-1px);
    box-shadow: 0 8px 20px rgba(15, 118, 110, 0.35) !important;
}

.tabs > .tab-nav {
    border-bottom: 2px solid #F1F5F9 !important;
}
.tabs > .tab-nav button.selected {
    border-bottom-color: #0F766E !important;
    color: #0F766E !important;
    font-weight: 700 !important;
}

#footer-credits {
    text-align: center;
    color: #94A3B8;
    font-size: 0.85rem;
    margin: 2rem 0 1rem 0;
    padding-top: 1.5rem;
    border-top: 1px solid #E2E8F0;
}

.chatbot-modern {
    border-radius: 16px !important;
    border: 1px solid #E2E8F0 !important;
}
"""


def build_ui() -> gr.Blocks:
    theme = gr.themes.Soft(
        primary_hue=gr.themes.colors.teal,
        secondary_hue=gr.themes.colors.lime,
        neutral_hue=gr.themes.colors.slate,
        font=[gr.themes.GoogleFont("Inter"), "system-ui", "sans-serif"],
    ).set(
        body_background_fill="#F8FAFC",
        block_background_fill="white",
        block_border_width="1px",
        block_shadow="0 1px 3px rgba(15, 23, 42, 0.04)",
        block_radius="16px",
    )

    with gr.Blocks(title="AgroSmart AI · Dashboard", theme=theme, css=CSS) as ui:
        gr.HTML(
            """
            <div id="hero-banner">
              <h1>🌱 AgroSmart AI</h1>
              <p>Sistem inteligent pentru agricultura de precizie · 99.55% acuratete ML · 12 ferme monitorizate · API + Dashboard + AI Assistant</p>
            </div>
            """
        )

        token_state = gr.State("")
        kpi_html = gr.HTML(hero_kpis(""))

        with gr.Tabs():

            # ---------- AUTENTIFICARE ----------
            with gr.Tab("🔐 Autentificare"):
                gr.Markdown(
                    "### Conecteaza-te ca fermier\n"
                    "Folosim JWT (60 min). Dupa login, tab-urile celelalte devin functionale."
                )
                with gr.Row():
                    u = gr.Textbox(label="Username", value="fermier")
                    p = gr.Textbox(label="Parola", type="password", value="agrosmart2025")
                login_btn = gr.Button("🚀 Login", variant="primary", size="lg")
                login_msg = gr.Markdown()

                def _login_and_kpis(username, password):
                    tok, msg = login(username, password)
                    return tok, msg, hero_kpis(tok)

                login_btn.click(
                    _login_and_kpis,
                    inputs=[u, p],
                    outputs=[token_state, login_msg, kpi_html],
                )

            # ---------- ANALIZA SENZOR ----------
            with gr.Tab("📡 Analiza senzor"):
                gr.Markdown(
                    "### Trimite o citire de senzor\n"
                    "Sistemul aplica algoritmul de decizie (50ms) si raspunde cu actiune + alerta."
                )
                with gr.Row():
                    with gr.Column(scale=1):
                        lat = gr.Number(label="📍 Latitudine (GPS)", value=46.77)
                        lon = gr.Number(label="📍 Longitudine (GPS)", value=23.62)
                        ph = gr.Slider(0, 14, value=6.5, step=0.01, label="🧪 pH")
                        um = gr.Slider(0, 100, value=24, step=0.5, label="💧 Umiditate (%)")
                        temp = gr.Slider(-10, 50, value=28, step=0.5, label="🌡️ Temperatura (°C)")
                        btn = gr.Button("▶ Analizeaza", variant="primary", size="lg")
                    with gr.Column(scale=1):
                        decision_md = gr.Markdown(elem_classes="action-card")
                        ph_out = gr.Textbox(label="Status pH", interactive=False)
                        raw = gr.Code(label="Raspuns API (JSON)", language="json")
                btn.click(
                    analiza,
                    inputs=[token_state, lat, lon, ph, um, temp],
                    outputs=[token_state, decision_md, raw, ph_out],
                )

            # ---------- HARTA ----------
            with gr.Tab("🗺️ Harta ferme"):
                gr.Markdown(
                    "### 12 ferme din Romania monitorizate live\n"
                    "🟢 OK · 🟠 actiune · 🔴 alerta · click pini pentru detalii."
                )
                map_btn = gr.Button("🔄 Incarca / reincarca harta", variant="primary", size="lg")
                map_html_out = gr.HTML()
                map_btn.click(harta_html, inputs=[token_state], outputs=map_html_out)

            # ---------- TENDINTE 2D ----------
            with gr.Tab("📈 Tendinte"):
                gr.Markdown("### Evolutia parametrilor in timp")
                with gr.Row():
                    metric = gr.Dropdown(
                        choices=["ph", "umiditate", "temperatura"],
                        value="umiditate", label="Metrica",
                    )
                    days = gr.Slider(1, 30, value=7, step=1, label="Zile inapoi")
                trend_btn = gr.Button("📊 Genereaza grafic", variant="primary", size="lg")
                trend_plot = gr.Plot()
                trend_btn.click(trend_chart, inputs=[token_state, metric, days], outputs=trend_plot)

            # ---------- 3D SPACE ----------
            with gr.Tab("🌐 Vizualizare 3D"):
                gr.Markdown(
                    "### Spatiu tridimensional al senzorilor\n"
                    "Fiecare punct = o citire reala. Rotește cu mouse-ul. "
                    "Aici se vad **clusterele de risc** instant — alertele se grupeaza in colturi extreme."
                )
                viz_btn = gr.Button("🎬 Render 3D", variant="primary", size="lg")
                viz_plot = gr.Plot()
                viz_btn.click(view_3d_scatter, inputs=[token_state], outputs=viz_plot)

            # ---------- ML COMPARE ----------
            with gr.Tab("🏆 Modele ML"):
                gr.Markdown(
                    "### 4 algoritmi antrenati pe 2200 probe agronomice (22 culturi)\n"
                    "Compara performanta si latenta de inferenta."
                )
                cmp_btn = gr.Button("📊 Incarca comparatie", variant="primary", size="lg")
                cmp_plot = gr.Plot()
                cmp_btn.click(model_comparison_chart, inputs=[token_state], outputs=cmp_plot)

            # ---------- RECOMANDARE CULTURA ----------
            with gr.Tab("🌾 Recomandare ML"):
                gr.Markdown(
                    "### Recomandare cultura optima\n"
                    "Spune-mi ce ai in sol, iti spun ce sa cresti. **99.55% acuratete** pe test set."
                )
                with gr.Row():
                    with gr.Column():
                        n_in = gr.Number(label="Azot N (kg/ha)", value=90)
                        p_in = gr.Number(label="Fosfor P (kg/ha)", value=42)
                        k_in = gr.Number(label="Potasiu K (kg/ha)", value=43)
                        temp_in = gr.Slider(0, 50, value=21, label="Temperatura (°C)")
                    with gr.Column():
                        hum_in = gr.Slider(0, 100, value=82, label="Umiditate (%)")
                        ph_in = gr.Slider(0, 14, value=6.5, step=0.1, label="pH")
                        rain_in = gr.Slider(0, 500, value=200, label="Precipitatii (mm/an)")
                        model_dd = gr.Dropdown(
                            choices=["auto", "ExtraTrees", "RandomForest", "GradientBoosting", "LogisticRegression"],
                            value="auto", label="Model ML",
                        )
                        ml_btn = gr.Button("🌱 Recomanda cultura", variant="primary", size="lg")
                ml_out = gr.Markdown()
                ml_btn.click(
                    predict_crop_ui,
                    inputs=[token_state, n_in, p_in, k_in, temp_in, hum_in, ph_in, rain_in, model_dd],
                    outputs=ml_out,
                )

            # ---------- AI CHAT (text + voice) ----------
            with gr.Tab("🤖 AgroBot AI"):
                gr.HTML(
                    """
                    <div style='background:linear-gradient(135deg,#0F766E15,#84CC1615);
                                padding:1rem 1.5rem;border-radius:14px;margin-bottom:1rem;
                                border:1px solid #0F766E33'>
                      <h3 style='margin:0;color:#0F172A'>🤖 Asistent AI alimentat de Claude Sonnet 4.6</h3>
                      <p style='margin:.25rem 0 0;color:#475569'>
                        Scrie sau <b>vorbeste</b> 🎤 cu mine. Iti raspund in romana cu voce 🔊.
                        Stiu tot despre AgroSmart: ML, API, cifre impact, recomandari culturi.
                      </p>
                    </div>
                    """
                )
                chatbot = gr.Chatbot(
                    height=480,
                    type="messages",
                    avatar_images=(None, "https://api.dicebear.com/7.x/bottts/svg?seed=AgroSmart"),
                    elem_classes="chatbot-modern",
                    show_label=False,
                    show_copy_button=True,
                    elem_id="agrobot_chat",
                )
                # Hidden field — JS-ul de TTS asculta schimbarile aici si citeste textul
                last_reply = gr.Textbox(visible=False, elem_id="last_reply_tts")

                with gr.Row():
                    msg = gr.Textbox(
                        placeholder="Scrie aici SAU foloseste microfonul de mai jos...",
                        show_label=False, scale=7, container=False,
                    )
                    send_btn = gr.Button("📤 Trimite", variant="primary", scale=1)
                    tts_toggle = gr.Checkbox(value=True, label="🔊 Voce", scale=1, container=False)

                with gr.Accordion("🎤 Vorbeste cu AgroBot (apesi & vorbesti)", open=True):
                    audio_in = gr.Audio(
                        sources=["microphone"],
                        type="filepath",
                        label="Apasa, vorbeste 5-10 secunde, opreste — eu transcriu si raspund",
                        format="wav",
                        elem_id="voice_input",
                    )
                    voice_btn = gr.Button("🎙️ Trimite vocal", variant="primary", size="lg")

                with gr.Accordion("💡 Exemple intrebari", open=False):
                    gr.Examples(
                        examples=[
                            "Ce face AgroSmart AI in 2 randuri?",
                            "Ce model ML e cel mai precis si de ce?",
                            "Care este economia de apa pe ferma de 10 ha?",
                            "Cum trimit o citire de senzor prin API?",
                            "Recomanda-mi o cultura pentru sol cu pH 6.5 si 200mm precipitatii",
                            "Cati senzori sunt activi acum si in ce orase?",
                        ],
                        inputs=msg,
                    )

                # JS: cand last_reply se schimba si toggle-ul e ON -> citeste cu Web Speech API
                tts_js = """
                async (reply, enabled) => {
                  if (!enabled || !reply) return reply;
                  try {
                    if ('speechSynthesis' in window) {
                      window.speechSynthesis.cancel();
                      const utter = new SpeechSynthesisUtterance(reply.replace(/[*#`_~]/g, ''));
                      utter.lang = 'ro-RO';
                      utter.rate = 1.05;
                      utter.pitch = 1.0;
                      // Prefera o voce romana daca exista
                      const voices = window.speechSynthesis.getVoices();
                      const ro = voices.find(v => v.lang && v.lang.startsWith('ro'));
                      if (ro) utter.voice = ro;
                      window.speechSynthesis.speak(utter);
                    }
                  } catch (e) { console.warn('TTS failed', e); }
                  return reply;
                }
                """

                # Text submission
                send_btn.click(
                    chat_send, [token_state, msg, chatbot], [chatbot, msg, last_reply]
                ).then(None, [last_reply, tts_toggle], None, js=tts_js)
                msg.submit(
                    chat_send, [token_state, msg, chatbot], [chatbot, msg, last_reply]
                ).then(None, [last_reply, tts_toggle], None, js=tts_js)

                # Voice submission
                voice_btn.click(
                    voice_chat, [token_state, audio_in, chatbot],
                    [chatbot, msg, last_reply],
                ).then(None, [last_reply, tts_toggle], None, js=tts_js)

            # ---------- ISTORIC ----------
            with gr.Tab("📜 Istoric"):
                limit = gr.Slider(5, 200, value=30, step=5, label="Numar inregistrari")
                refresh = gr.Button("🔄 Reincarca", variant="primary", size="lg")
                tabel = gr.Markdown()
                refresh.click(listeaza_istoric, inputs=[token_state, limit], outputs=tabel)

            # ---------- SUMAR ----------
            with gr.Tab("📊 Statistici"):
                sum_btn = gr.Button("🔄 Reincarca statistici", variant="primary", size="lg")
                sum_md = gr.Markdown()
                sum_btn.click(summary_md, inputs=[token_state], outputs=sum_md)

        gr.HTML(
            """
            <div id="footer-credits">
              AgroSmart AI v2.0 · <b>Ureche Ionel Alexandru</b> ·
              <a href="https://github.com/lexusthunder/agrosmart-ai" target="_blank">GitHub</a> ·
              <a href="https://alexai888-agrosmart-ai.hf.space/docs" target="_blank">API Docs</a> ·
              MIT License · 2026
            </div>
            """
        )
    return ui


def main() -> None:
    ui = build_ui()
    ui.launch(
        server_name="0.0.0.0",
        server_port=settings.dashboard_port,
        show_api=False,
        share=settings.gradio_share,
    )


if __name__ == "__main__":
    main()
