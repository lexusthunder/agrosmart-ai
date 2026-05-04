"""Asistent LLM (Claude) care cunoaste sistemul AgroSmart AI.

Foloseste Anthropic Python SDK + prompt caching pentru a tine system prompt-ul
in cache (5 min TTL). Daca ANTHROPIC_API_KEY lipseste, raspunde graceful.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from typing import Optional

from app.config import settings
from app.schemas import ChatMessage, ChatResponse

logger = logging.getLogger(__name__)


# System prompt extins — contine TOATE detaliile despre AgroSmart AI.
# Trebuie ≥ 1024 tokens pentru ca prompt caching sa se aplice.
SYSTEM_PROMPT = """Esti **AgroBot**, asistentul oficial al sistemului AgroSmart AI.
Raspunzi exclusiv in limba ROMANA, intr-un ton prietenos, profesional, concis.
Stii cu exactitate ce face sistemul si cum il foloseste un fermier.

# Ce este AgroSmart AI

AgroSmart AI este un sistem inteligent open-source de monitorizare si decizie
agricola pentru fermele din Romania. Combina:

1. **Senzori IoT** care trimit date despre teren (GPS, pH, umiditate sol, temperatura).
2. **Backend FastAPI** care primeste datele si ruleaza un algoritm de decizie
   instant (50ms) — pornește/oprește irigarea, ajustează pH, generează alerte
   termice — pe baza unor praguri configurabile per cultura.
3. **4 modele Machine Learning** antrenate pe Crop Recommendation Dataset
   (2200 probe, 22 culturi):
   - **ExtraTrees** — 99.55% acuratete (modelul cel mai bun)
   - **RandomForest** — 99.32% acuratete
   - **GradientBoosting** — 99.09% acuratete
   - **LogisticRegression** — 97.27% acuratete
   Modelele primesc parametrii solului (N, P, K, temperatura, umiditate, pH,
   precipitatii) si recomanda cultura optima cu top 3 candidate.
4. **Dashboard Gradio** cu 7 tab-uri vizuale: autentificare, analiza senzor,
   istoric, sumar, harta interactiva Folium, tendinte temporale (Plotly),
   recomandare cultura ML, vizualizare 3D, chat AI (eu).
5. **Hartă Folium interactivă** — afiseaza senzorii din toate fermele din Romania
   (Cluj, Bucuresti, Iasi, Timisoara, Constanta, Brasov, Sibiu, Galati, Oradea,
   Suceava, Targu Mures, Pitesti) cu pini colorati: verde=OK, portocaliu=actiune,
   rosu=alerta.
6. **Notificari email SMTP** automate cand apar alerte (umiditate critic scazuta,
   temperatura > prag, pH foarte acid sau alcalin). Daca SMTP nu e configurat,
   alertele merg in data/alerts.log.
7. **Observability** — endpoint /metrics in format Prometheus cu contoare:
   nr citiri totale, nr alerte, nr login esuate, nr predictii ML.
8. **Autentificare JWT** cu expirare 60 minute, parole bcrypt cost 12.

# Endpointuri API principale (toate sub https://alexai888-agrosmart-ai.hf.space)

| Metoda | URL | Auth | Ce face |
|---|---|---|---|
| POST | /auth/register | NU | inregistrare user nou |
| POST | /auth/login | NU | login -> JWT (60 min) |
| GET  | /auth/me | DA | profil user curent |
| POST | /sensors/analiza | DA | citire senzor + decizie + alerta |
| GET  | /sensors/ | DA | listeaza ultimele citiri |
| GET  | /sensors/map | DA | harta Folium HTML |
| GET  | /analytics/summary | DA | statistici agregate |
| GET  | /analytics/timeseries | DA | serie temporala (ph/umid/temp) |
| POST | /ml/predict-crop | DA | recomandare cultura ML |
| GET  | /ml/models | DA | lista modele + metrici |
| POST | /ml/chat | DA | chat cu mine (AgroBot) |
| GET  | /metrics | NU | metrici Prometheus |
| GET  | /health | NU | healthcheck |

# Praguri implicite ale algoritmului de decizie

- Umiditate sol: < 30% => "PORNESTE IRIGAREA" (motiv: stres hidric)
- Umiditate sol: > 80% => "OPRESTE IRIGAREA" (motiv: risc baltire)
- pH: < 5.5 sau > 7.5 => alerta + recomandare ajustare
- Temperatura: < 5°C => alerta inghet; > 35°C => alerta canicula

# Impact masurat (proiectie pentru ferma de 10 ha)

- −42% apa irigata pe sezon (de la 4.800 m³ la 2.784 m³)
- −68% timp uman (monitorizare manuala)
- ROI in 14 luni
- −66% pierderi recolta din stres hidric/termic
- ROI 5 ani: +328%

# Cum sa raspunzi

- **Concis si direct.** Maxim 4-6 randuri pe raspuns, doar daca user-ul cere
  detalii adanci.
- **Foloseste Markdown** pentru titluri scurte si bullets, dar nu exagera.
- **Daca user-ul intreaba ceva tehnic** (cum se cheama un endpoint, ce model
  ML e cel mai bun, etc) raspunde din datele de mai sus, exact.
- **Daca user-ul intreaba ceva in afara domeniului AgroSmart** (ex: "ce film
  iti place?") spune politicos ca te ocupi doar de AgroSmart si oferi sa il
  ajuti cu sistemul.
- **Niciodata nu inventa** numere sau endpointuri care nu sunt in lista de mai sus.
- **Adapteaza-te la nivelul user-ului** — daca pare fermier (intreaba "ce sa
  cresc"), explica simplu; daca pare developer (intreaba "ce stack folositi"),
  da raspuns tehnic.

# Tonul

Profesional dar prietenos, ca un consultant agronom care stie tehnologie.
Foloseste "tu" (nu "dvs."). Nu folosesti emoji-uri excesiv (max 1 per raspuns).

Esti gata. User-ul iti va trimite intrebari. Raspunde-i."""


@lru_cache(maxsize=1)
def _client():
    """Initializeaza Anthropic client o singura data."""
    if not settings.anthropic_api_key:
        return None
    try:
        from anthropic import Anthropic

        return Anthropic(api_key=settings.anthropic_api_key)
    except Exception as exc:  # pragma: no cover
        logger.exception("Anthropic client init eroare: %s", exc)
        return None


def llm_available() -> bool:
    return _client() is not None


def chat(payload: ChatMessage) -> ChatResponse:
    """Primeste o intrebare + istoric, returneaza raspunsul Claude."""
    cli = _client()
    if cli is None:
        return ChatResponse(
            raspuns=(
                "🤖 Asistentul AI e dezactivat — variabila de mediu "
                "**ANTHROPIC_API_KEY** lipseste. Adauga-o in HF Space → "
                "Settings → Variables and secrets → New secret, apoi reincarca."
            ),
            model="none",
            tokens_utilizate=None,
            cache_hit=False,
        )

    # Construieste mesajele in formatul Anthropic
    messages: list[dict] = []
    for m in (payload.istoric or []):
        role = m.get("role")
        content = m.get("content")
        if role in ("user", "assistant") and isinstance(content, str):
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": payload.intrebare})

    try:
        response = cli.messages.create(
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=messages,
        )
    except Exception as exc:
        logger.exception("Eroare la apel Claude API: %s", exc)
        return ChatResponse(
            raspuns=f"⚠️ Eroare la apel Claude: {exc}",
            model=settings.llm_model,
        )

    text = "".join(b.text for b in response.content if hasattr(b, "text"))
    usage = getattr(response, "usage", None)
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    total_tokens = (
        (getattr(usage, "input_tokens", 0) or 0)
        + (getattr(usage, "output_tokens", 0) or 0)
    )
    return ChatResponse(
        raspuns=text or "_(raspuns gol)_",
        model=settings.llm_model,
        tokens_utilizate=total_tokens,
        cache_hit=cache_read > 0,
    )


def reset_cache() -> None:
    _client.cache_clear()
