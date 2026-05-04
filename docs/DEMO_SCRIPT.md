# Script video demo — 60 secunde

> Filmare ecran VS Code + browser. Un singur take dacă se poate. Voice-over în RO.

## Timeline

| Sec | Ce arăți | Ce spui |
|---|---|---|
| **0–10** | *Slide statistic*: imagine satelit fermă uscată în România + cifră "**42% din apa de irigat se pierde**" (FAO) | *"Agricultura românească pierde anual milioane de metri cubi de apă din cauza irigării oarbe. AgroSmart AI rezolvă asta."* |
| **10–25** | Browser → `localhost:8000/docs` → login fermier → POST `/sensors/analiza` cu pH 8.0, umiditate 22%, temperatură 38°C → răspunsul JSON cu **alerta:true** și acțiunea **PORNEȘTE IRIGAREA** | *"Senzorul trimite datele, sistemul decide imediat: irigare necesară, alertă pentru fermier — totul în 50 ms."* |
| **25–45** | Browser → `localhost:8000/sensors/map` (hartă Folium cu pini roșii/verzi) → apoi POST `/ml/predict-crop` cu N=90, P=42, K=43, pH=6.5, rainfall=200 → răspuns "**rice**" cu confidență 98% și top 3 | *"Pe lângă reguli deterministe, un model ML antrenat pe 2200 de probe agronomice recomandă cultura optimă pentru solul tău cu acuratețe 99%."* |
| **45–60** | Slide final: **−42% apă, −68% timp, ROI 14 luni, 328% ROI 5 ani** + logo + URL | *"Mai puțină apă. Mai puțin timp. Mai mult randament. AgroSmart AI — agricultura de precizie pentru fiecare fermier român."* |

## Setup pre-take

```bash
# 1. Pornește backend
python run.py &

# 2. Pornește dashboard (separat)
python -m dashboard.app &

# 3. Seedeaza date pentru harta să arate convingător
python -m scripts.seed
python -m scripts.simulate_sensor --count 30

# 4. Antrenează modelul ML (dacă nu e deja)
python -m scripts.train_model
```

## Tools recomandate

- **Captură ecran**: OBS Studio (gratuit, multi-source)
- **Editare**: DaVinci Resolve sau iMovie
- **Voice-over**: Audacity + microfon decent (Blue Yeti / lavaliera USB)
- **Subtitle EN**: auto-generate din voice → corectare manuală în SRT

## Variantă scurtă (30s, pentru Twitter/X)

| Sec | Ce arăți | Ce spui |
|---|---|---|
| 0–7 | Statistic + problemă | "42% din apa de irigat se pierde" |
| 7–22 | Demo POST analiza + map + ML predict (cut rapid) | "Senzori → decizie → cultură optimă" |
| 22–30 | Cifre impact + CTA | "−42% apă. ROI 14 luni. AgroSmart.ai" |
