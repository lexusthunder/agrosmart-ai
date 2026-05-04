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


def _normalize_history(items: list) -> list[dict]:
    out: list[dict] = []
    for m in items or []:
        role = m.get("role")
        content = m.get("content")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            out.append({"role": role, "content": content})
    return out


def _chat_anthropic(payload: ChatMessage) -> ChatResponse:
    cli = _client()
    if cli is None:
        return ChatResponse(raspuns="(anthropic indisponibil)", model="none")
    messages = _normalize_history(payload.istoric)
    messages.append({"role": "user", "content": payload.intrebare})
    try:
        response = cli.messages.create(
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            messages=messages,
        )
    except Exception as exc:
        logger.exception("Eroare Claude: %s", exc)
        raise
    text = "".join(b.text for b in response.content if hasattr(b, "text"))
    usage = getattr(response, "usage", None)
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    total = (getattr(usage, "input_tokens", 0) or 0) + (getattr(usage, "output_tokens", 0) or 0)
    return ChatResponse(
        raspuns=text or "_(raspuns gol)_",
        model=settings.llm_model,
        tokens_utilizate=total,
        cache_hit=cache_read > 0,
    )


def _local_qa(intrebare: str) -> str:
    """Raspunsuri pre-cablate (rule-based) pentru cele mai frecvente intrebari.

    Cand niciun LLM nu e disponibil, sistemul ramane utilizabil.
    """
    q = intrebare.lower().strip()

    if any(w in q for w in ["ce face", "ce e", "ce este", "despre"]):
        return (
            "**AgroSmart AI** este un sistem inteligent de monitorizare si decizie agricola pentru fermele din Romania. "
            "Combina senzori IoT (pH, umiditate, temperatura, GPS), un algoritm de decizie instant (50ms) "
            "si **4 modele Machine Learning** (cel mai bun: ExtraTrees cu **99.55% acuratete**) "
            "pentru a recomanda culturi optime din 22 disponibile. Include harta interactiva, "
            "vizualizare 3D, alerte SMTP si dashboard premium."
        )

    if any(w in q for w in ["model", "ml ", "machine learning", "algoritm", "ai "]):
        return (
            "Sistemul are **4 modele ML** antrenate pe 2200 probe agronomice (Crop Recommendation Dataset):\n\n"
            "| Model | Accuracy | F1 macro |\n|---|---:|---:|\n"
            "| 🏆 **ExtraTrees** | **99.55%** | 99.55% |\n"
            "| RandomForest | 99.32% | 99.32% |\n"
            "| GradientBoosting | 99.09% | 99.09% |\n"
            "| LogisticRegression | 97.27% | 97.27% |\n\n"
            "ExtraTrees castiga pentru ca foloseste random splits (mai bun la generalizare pe date agronomice cu zgomot)."
        )

    if any(w in q for w in ["apa", "irigare", "iriga", "consum"]):
        return (
            "**Reduceri** pe ferma de 10 ha:\n"
            "- 💧 **−42% apa irigata** (de la 4,800 m³/sezon la 2,784 m³)\n"
            "- ⏱️ **−68% timp uman** de monitorizare\n"
            "- 📉 **−66% pierderi recolta** din stres hidric/termic\n\n"
            "Sursele: FAO AQUASTAT, UNESCO WWDR 2023, IPCC AR6. Vezi `docs/IMPACT.md` pentru calcul detaliat."
        )

    if any(w in q for w in ["roi", "cost", "pret", "rentabil", "investitie"]):
        return (
            "**ROI**: **14 luni** pentru ferma de 10 ha. Investitie initiala ~5,200 € "
            "(senzori + soft + instalare). Economii anuale ~4,460 € (apa, energie, forta munca, "
            "pierderi evitate). **ROI pe 5 ani: +328%.**"
        )

    if any(w in q for w in ["api", "endpoint", "swagger", "docs", "rest"]):
        return (
            "**API endpoint-uri principale** (Swagger UI: `/docs`):\n"
            "- `POST /sensors/analiza` — citire senzor + decizie + alerta\n"
            "- `GET /sensors/map` — harta Folium\n"
            "- `POST /ml/predict-crop` — recomandare cultura (4 modele)\n"
            "- `GET /analytics/timeseries` — serii temporale\n"
            "- `POST /ml/chat` — chat cu mine (eu)\n"
            "- `GET /metrics` — metrici Prometheus"
        )

    if any(w in q for w in ["recomanda", "cultur", "cresc", "plantez"]):
        return (
            "Da-mi parametrii solului si iti recomand cultura optima:\n"
            "- **N** (azot, kg/ha)\n- **P** (fosfor, kg/ha)\n- **K** (potasiu, kg/ha)\n"
            "- **temperatura** (°C)\n- **umiditate** (%)\n- **pH**\n- **precipitatii** (mm/an)\n\n"
            "Foloseste tab-ul **🌾 Recomandare ML** sau apeleaza endpoint-ul `POST /ml/predict-crop`. "
            "Acuratete 99.55% pe 22 culturi posibile."
        )

    if any(w in q for w in ["harta", "ferme", "harti", "locatii"]):
        return (
            "Sunt **12 ferme** monitorizate in Romania: Cluj-Napoca, Bucuresti, Iasi, Timisoara, "
            "Constanta, Brasov, Sibiu, Galati, Oradea, Suceava, Targu Mures, Pitesti.\n\n"
            "Fiecare are 4 senzori IoT activi. Pe harta: 🟢 OK · 🟠 actiune · 🔴 alerta. "
            "Click pe pini pentru detalii citire."
        )

    if any(w in q for w in ["alerta", "notificar", "email", "smtp"]):
        return (
            "Sistemul trimite **email automat** cand:\n"
            "- pH < 5.5 sau > 7.5\n- Temperatura > 35°C sau < 5°C\n- Umiditate < 30% (stres hidric critic)\n\n"
            "Daca SMTP nu e configurat, alertele merg in `data/alerts.log`. "
            "Configurare prin variabilele `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`."
        )

    if any(w in q for w in ["salut", "buna", "hi", "hello", "esti"]):
        return (
            "🌱 Salut! Sunt **AgroBot**, asistentul AgroSmart AI. "
            "Pot raspunde la intrebari despre sistem, modele ML, recomandari de culturi, "
            "API, harta, alerte sau impact. Ce te intereseaza?"
        )

    # Default — incurajeaza intrebari concrete
    return (
        f"Mhm, intrebarea ta: *'{intrebare[:100]}'*\n\n"
        "Pentru chat AI complet (Claude), administratorul trebuie sa adauge "
        "`ANTHROPIC_API_KEY` in HF Space → Settings → Secrets.\n\n"
        "Intre timp, pot raspunde la intrebari despre: **ce face sistemul**, "
        "**modele ML**, **economia de apa**, **ROI**, **API**, **harta ferme**, **alerte**, "
        "**recomandare cultura**. Reformuleaza?"
    )


def _chat_huggingface(payload: ChatMessage) -> ChatResponse:
    """Fallback: HF Inference Router. Daca nu merge → raspuns rule-based."""
    import os

    hf_token = (
        os.environ.get("HF_TOKEN")
        or os.environ.get("HUGGING_FACE_HUB_TOKEN")
        or os.environ.get("HUGGINGFACEHUB_API_TOKEN")
    )
    if hf_token:
        try:
            from huggingface_hub import InferenceClient

            cli = InferenceClient(token=hf_token, timeout=60)
            messages = [{"role": "system", "content": SYSTEM_PROMPT}]
            messages.extend(_normalize_history(payload.istoric))
            messages.append({"role": "user", "content": payload.intrebare})

            for model_id in [
                "meta-llama/Llama-3.2-3B-Instruct",
                "Qwen/Qwen2.5-7B-Instruct",
                "HuggingFaceH4/zephyr-7b-beta",
            ]:
                try:
                    resp = cli.chat_completion(
                        messages=messages,
                        model=model_id,
                        max_tokens=settings.llm_max_tokens,
                        temperature=0.4,
                    )
                    text = resp.choices[0].message.content if resp.choices else ""
                    if text:
                        return ChatResponse(
                            raspuns=text,
                            model=f"hf:{model_id}",
                            tokens_utilizate=getattr(getattr(resp, "usage", None), "total_tokens", 0) or 0,
                        )
                except Exception as ex:
                    logger.warning("HF model %s indisponibil: %s", model_id, ex)
                    continue
        except Exception as exc:
            logger.warning("HF Inference esuat global: %s", exc)

    # Fallback final: rule-based — sistemul ramane FUNCTIONAL fara nicio cheie API
    return ChatResponse(
        raspuns=_local_qa(payload.intrebare),
        model="local-rules",
        tokens_utilizate=0,
        cache_hit=False,
    )


def chat(payload: ChatMessage) -> ChatResponse:
    """Primeste o intrebare + istoric. Foloseste Anthropic daca e disponibil, altfel HF."""
    if settings.anthropic_api_key:
        try:
            return _chat_anthropic(payload)
        except Exception as exc:
            logger.warning("Claude esuat (%s), trec la HF Inference", exc)
            return _chat_huggingface(payload)
    return _chat_huggingface(payload)


def reset_cache() -> None:
    _client.cache_clear()
