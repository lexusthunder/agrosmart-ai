# AgroSmart AI — pitch one-pager

> **Agricultura de precizie pentru fiecare fermier român.** O platformă end-to-end care transformă datele de senzor în decizii rentabile, automate, măsurate.

---

## 🎯 Problema

România irigă ~600,000 ha cu **−42% eficiență** vs media UE. Fermierii decid "din ochi" — apa, fertilizatorii și timpul lor se pierd, iar randamentele scad cu 6–9% anual din stres hidric și termic. Soluțiile actuale (sisteme John Deere, Bayer Climate FieldView) sunt **scumpe (>15k€/an), opace, în engleză, fără suport local**.

## 💡 Soluția

Un sistem **open-source, deployable în 5 minute**, care unește 3 capabilități într-un singur API:

1. **Decizie deterministă (rule-based)** — pentru irigare/pH/temperatură, transparent și auditabil.
2. **Recomandare cultură ML** — RandomForest antrenat pe 2200 probe agronomice, **99.3% acuratețe**.
3. **Hărți + alerte SMTP + dashboard** — fermierul vede totul în limba română, fără cont cloud.

## 🏆 Diferențiator

| Criteriu | Competiție (FieldView, Granular) | AgroSmart AI |
|---|---|---|
| Cost / 10 ha / an | >15,000 € | <500 € (self-hosted) |
| Limbă | EN | RO nativ |
| Self-hostable | ❌ | ✅ |
| Cod sursă | ❌ proprietar | ✅ MIT |
| ML transparent (feature importance) | ❌ blackbox | ✅ Sklearn explainable |
| Onboarding | săptămâni | 5 minute (`docker-compose up`) |

## 📊 Impact măsurabil

- **−42%** apă irigată
- **−68%** timp uman
- **ROI 14 luni** la fermă de 10 ha
- **−190 t CO₂e/an** la 100 de adopanți (5 ani)

> Surse: FAO AQUASTAT, UNESCO WWDR 2023, IPCC AR6 Ch.5 — vezi [`IMPACT.md`](./IMPACT.md).

## 🛣️ Roadmap

- **Q2 2026** — pilot 3 ferme (Cluj/Mureș/Timiș), validare empirică −42% apă.
- **Q3 2026** — integrare LoRaWAN pentru senzori autonomi pe baterie 2 ani.
- **Q4 2026** — predicție randament (LSTM) + integrare sateliți Sentinel-2.
- **2027** — extindere SE Europa (Ungaria, Bulgaria, Serbia) prin parteneri locali.

## 👤 Echipa

**Ureche Ionel Alexandru** — fondator, full-stack engineer cu background în AI și sisteme distribuite. Built [Aureum CRM](https://aureum.estate), CaloriAI și o suită de produse SaaS B2B.

## 🔗 Demo & links

- **Live demo**: `docker-compose up` → `http://localhost:8000/docs`
- **Sursa**: GitHub (MIT license)
- **Video pitch 60s**: [`DEMO_SCRIPT.md`](./DEMO_SCRIPT.md)
- **Arhitectură tehnică**: [`ARCHITECTURE.md`](./ARCHITECTURE.md)

---

*Construim pentru fermierul român, nu pentru Silicon Valley. Tehnologia trebuie să servească pământul, nu invers.*
