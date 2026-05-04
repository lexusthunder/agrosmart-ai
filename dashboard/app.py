"""Dashboard Gradio - interfata interactiva pentru AgroSmart AI."""

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


# ---- helpers ---------------------------------------------------------- #


def _fmt_response(payload: dict[str, Any], status_code: int) -> str:
    return f"HTTP {status_code}\n\n{json.dumps(payload, indent=2, ensure_ascii=False)}"


def login(username: str, password: str) -> tuple[str, str]:
    """Login → returneaza (token, mesaj)."""
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
    return token, f"✅ Autentificat ca {username}"


def analiza(
    token: str,
    lat: float,
    lon: float,
    ph: float,
    umiditate: float,
    temperatura: float,
) -> tuple[str, str, str, str]:
    """Trimite o citire la API si afiseaza rezultatul."""
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
    alerta = "🚨 ALERTA" if data["alerta"] else "✅ NORMAL"

    badge = (
        f"## {actiune}\n\n"
        f"**Motiv:** {motiv}\n\n"
        f"**Status pH:** `{ph_status}`  ·  **Alerta:** {alerta}"
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


def harta_html(token: str) -> str:
    """Returneaza harta Folium ca iframe HTML."""
    if not token:
        return "<p style='padding:1rem'>❌ Trebuie sa te autentifici intai.</p>"
    return (
        f'<iframe src="{API}/sensors/map" '
        f'style="width:100%;height:620px;border:0;border-radius:12px" '
        f'title="Harta AgroSmart"></iframe>'
        f'<p style="font-size:13px;color:#666;margin-top:8px">'
        f'Note: harta foloseste tokenul actual prin proxy direct la API. '
        f'Pentru autentificare in iframe foloseste extensii browser.</p>'
    )


def trend_chart(token: str, metric: str, days: int) -> go.Figure:
    """Plot Plotly cu seria temporala."""
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
        fig.update_layout(
            title=f"Nu exista date pentru {metric} in ultimele {days} zile",
            height=400,
        )
        return fig

    df = pd.DataFrame(points)
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    label_map = {"ph": "pH", "umiditate": "Umiditate (%)", "temperatura": "Temperatura (°C)"}
    color_map = {"ph": "#7B3F00", "umiditate": "#1f77b4", "temperatura": "#d62728"}

    fig = px.line(
        df,
        x="timestamp",
        y="valoare",
        title=f"{label_map.get(metric, metric)} — ultimele {days} zile ({len(df)} citiri)",
        labels={"timestamp": "Data/ora", "valoare": label_map.get(metric, metric)},
        markers=True,
    )
    fig.update_traces(line_color=color_map.get(metric, "#2C5F2D"), line_width=2)
    fig.update_layout(
        height=460,
        plot_bgcolor="#FAFBF6",
        paper_bgcolor="white",
        font=dict(family="sans-serif", size=13),
    )
    return fig


def predict_crop_ui(
    token: str,
    n: float,
    p_val: float,
    k: float,
    temp: float,
    hum: float,
    ph: float,
    rain: float,
) -> str:
    if not token:
        return "❌ Trebuie sa te autentifici intai"
    body = {
        "N": float(n),
        "P": float(p_val),
        "K": float(k),
        "temperature": float(temp),
        "humidity": float(hum),
        "ph": float(ph),
        "rainfall": float(rain),
    }
    try:
        r = httpx.post(
            f"{API}/ml/predict-crop",
            headers={"Authorization": f"Bearer {token}"},
            json=body,
            timeout=15.0,
        )
    except httpx.RequestError as exc:
        return f"❌ Eroare conexiune: {exc}"

    if r.status_code != 200:
        return _fmt_response(r.json(), r.status_code)

    data = r.json()
    top3 = "\n".join(
        f"- **{name}** — {prob*100:.2f}%" for name, prob in data["top_3"]
    )
    return (
        f"## 🌾 Cultura recomandata: **{data['cultura_recomandata'].upper()}**\n\n"
        f"**Incredere:** {data['incredere']*100:.2f}%\n\n"
        f"### Top 3 candidate\n{top3}"
    )


# ---- UI ---------------------------------------------------------------- #


CSS = """
.gradio-container { max-width: 1100px !important; }
#title h1 { color: #2C5F2D; }
.action-card { background: #F1F7E8; padding: 1rem; border-radius: 12px;
               border-left: 6px solid #2C5F2D; }
"""


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="AgroSmart AI Dashboard", theme=gr.themes.Soft(), css=CSS) as ui:
        gr.Markdown("# 🌱 AgroSmart AI — Dashboard de control", elem_id="title")
        gr.Markdown(
            "Sistem de monitorizare si decizie agricola in timp real. "
            "Trimite date de senzor → primesti decizia algoritmului."
        )

        token_state = gr.State("")

        with gr.Tab("🔐 Autentificare"):
            with gr.Row():
                u = gr.Textbox(label="Username", value="fermier")
                p = gr.Textbox(label="Parola", type="password", value="agrosmart2025")
            login_btn = gr.Button("Login", variant="primary")
            login_msg = gr.Markdown()
            login_btn.click(login, inputs=[u, p], outputs=[token_state, login_msg])

        with gr.Tab("📡 Analiza senzor"):
            with gr.Row():
                with gr.Column(scale=1):
                    lat = gr.Number(label="📍 Latitudine (GPS)", value=46.77)
                    lon = gr.Number(label="📍 Longitudine (GPS)", value=23.62)
                    ph = gr.Slider(0, 14, value=6.5, step=0.01, label="🧪 pH")
                    um = gr.Slider(0, 100, value=24, step=0.5, label="💧 Umiditate (%)")
                    temp = gr.Slider(-10, 50, value=28, step=0.5, label="🌡️ Temperatura (°C)")
                    btn = gr.Button("▶ Analizeaza date", variant="primary")
                with gr.Column(scale=1):
                    decision_md = gr.Markdown(elem_classes="action-card")
                    raw = gr.Code(label="Raspuns API (JSON)", language="json")
                    ph_out = gr.Textbox(label="Status pH", interactive=False)
            btn.click(
                analiza,
                inputs=[token_state, lat, lon, ph, um, temp],
                outputs=[token_state, decision_md, raw, ph_out],
            )

        with gr.Tab("📜 Istoric citiri"):
            limit = gr.Slider(5, 200, value=20, step=5, label="Numar de inregistrari")
            refresh = gr.Button("Reincarca")
            tabel = gr.Markdown()
            refresh.click(listeaza_istoric, inputs=[token_state, limit], outputs=tabel)

        with gr.Tab("📊 Sumar / Analytics"):
            sum_btn = gr.Button("Reincarca statistici")
            sum_md = gr.Markdown()
            sum_btn.click(summary_md, inputs=[token_state], outputs=sum_md)

        with gr.Tab("🗺️ Harta ferme"):
            gr.Markdown(
                "Marcaje colorate: 🟢 OK · 🟠 actiune · 🔴 alerta. "
                "Click pe pini pentru detalii citire."
            )
            map_btn = gr.Button("Incarca / reincarca harta", variant="primary")
            map_html = gr.HTML()
            map_btn.click(harta_html, inputs=[token_state], outputs=map_html)

        with gr.Tab("📈 Tendinte"):
            gr.Markdown(
                "Vizualizeaza evolutia pH-ului, umiditatii sau temperaturii in timp."
            )
            with gr.Row():
                metric = gr.Dropdown(
                    choices=["ph", "umiditate", "temperatura"],
                    value="umiditate",
                    label="Metrica",
                )
                days = gr.Slider(1, 30, value=7, step=1, label="Zile inapoi")
            trend_btn = gr.Button("Genereaza grafic", variant="primary")
            trend_plot = gr.Plot()
            trend_btn.click(
                trend_chart,
                inputs=[token_state, metric, days],
                outputs=trend_plot,
            )

        with gr.Tab("🌾 Recomandare cultura (ML)"):
            gr.Markdown(
                "**RandomForest** antrenat pe 2200 probe agronomice "
                "(sursa: Kaggle Crop Recommendation, 22 culturi). "
                "Acuratete pe test set: **~99.3%**."
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
                    ml_btn = gr.Button("Recomanda cultura", variant="primary")
            ml_out = gr.Markdown()
            ml_btn.click(
                predict_crop_ui,
                inputs=[token_state, n_in, p_in, k_in, temp_in, hum_in, ph_in, rain_in],
                outputs=ml_out,
            )

        gr.Markdown(
            "---\n*AgroSmart AI · Ureche Ionel Alexandru · 2025*",
        )
    return ui


def main() -> None:
    ui = build_ui()
    ui.launch(
        server_name="0.0.0.0",
        server_port=settings.dashboard_port,
        show_api=False,
    )


if __name__ == "__main__":
    main()
