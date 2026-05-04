# Deploy AgroSmart AI online

Trei căi de la "0 → URL public", de la cea mai rapidă la cea mai ieftin-totuși-stabilă.

---

## 🟢 Calea 1 — Gradio Share (60 secunde, link temporar)

Ideal pentru demo în videocall sau pitch live. Generează URL `*.gradio.live` valabil ~72h.

```bash
cd agrosmart-ai
echo "GRADIO_SHARE=true" >> .env
.venv/bin/python run.py
```

În consolă apar 2 URL-uri:
- **Local**: `http://localhost:7860`
- **Public**: `https://abcd1234.gradio.live` ← trimite asta în chat

⚠️ Tunelul rulează prin laptopul tău — închide laptop = link mort. Pentru permanență vezi mai jos.

---

## 🟡 Calea 2 — Render.com (un click, free tier)

1. Deschide: **[render.com/deploy?repo=https://github.com/lexusthunder/agrosmart-ai](https://render.com/deploy?repo=https://github.com/lexusthunder/agrosmart-ai)**
2. Login cu GitHub → "Connect" pe repo → "Apply"
3. Render citește [`render.yaml`](../render.yaml), instalează deps, antrenează modelul, pornește API.
4. ~6 min mai târziu primești URL: `https://agrosmart-ai-xxxx.onrender.com/docs`

Free tier: serviciul "doarme" după 15 min inactivitate (primul request după aia ia ~30s să trezească instanța — OK pentru demo de juriu).

**Variabile de configurat după deploy:**
- `SECRET_KEY` (auto-generat de Render)
- (opțional) `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD` pentru alerte email

---

## 🔵 Calea 3 — Hugging Face Spaces (gratuit, persist)

HF Spaces e perfect pentru proiecte ML — gratuit, fără sleep, link memorabil.

### A) Prin browser (cel mai ușor)

1. Mergi la **https://huggingface.co/new-space**
2. Owner: `lexusthunder` (sau team), Space name: `agrosmart-ai`
3. SDK: **Docker** (foarte important — nu Gradio!)
4. Visibility: Public
5. După creare → tab **Files** → New file → upload manual SAU clone-and-push:

### B) Prin CLI (5 comenzi)

```bash
# 1. Login (vei fi redirecționat în browser pentru token)
huggingface-cli login

# 2. Creează space-ul
huggingface-cli repo create agrosmart-ai --type space --space_sdk docker

# 3. Adaugă remote-ul HF
git remote add hf https://huggingface.co/spaces/lexusthunder/agrosmart-ai

# 4. Renumește Dockerfile.spaces ca să fie folosit de HF
git mv Dockerfile.spaces Dockerfile-spaces  # backup
cp Dockerfile.spaces Dockerfile  # OVERWRITE — vezi nota mai jos

# 5. Push pe HF
git push hf main
```

⚠️ **Notă importantă**: HF Spaces caută `Dockerfile` la root. Dacă vrei să păstrezi Dockerfile-ul original, fă un branch separat `huggingface` care suprascrie:
```bash
git checkout -b huggingface
mv Dockerfile.spaces Dockerfile
git add Dockerfile && git commit -m "HF Spaces Dockerfile"
git push hf huggingface:main
```

URL-ul rezultat: `https://huggingface.co/spaces/lexusthunder/agrosmart-ai`
Direct API: `https://lexusthunder-agrosmart-ai.hf.space`

---

## 🟣 Calea 4 — Fly.io / Railway (pentru cei avansați)

Necesită CLI + Docker local. Consultă `Dockerfile` (nu `.spaces`) — e gata pentru orice platformă Docker.

```bash
# Fly.io
fly launch --copy-config --name agrosmart-ai
fly deploy

# Railway
railway init
railway up
```

---

## ✅ Quick check după deploy

Indiferent de calea aleasă:

```bash
PUBLIC_URL=https://your-deploy-url.com  # înlocuiește

curl $PUBLIC_URL/health
# {"status":"ok","timestamp":"..."}

curl $PUBLIC_URL/
# {"app":"AgroSmart AI","version":"1.0.0",...}

# Login cu user demo (dacă seed.py a rulat)
TOKEN=$(curl -s -X POST $PUBLIC_URL/auth/login \
  -d "username=fermier&password=agrosmart2025" | jq -r .access_token)

# Predicție ML
curl -X POST $PUBLIC_URL/ml/predict-crop \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"N":90,"P":42,"K":43,"temperature":21,"humidity":82,"ph":6.5,"rainfall":200}'
# {"cultura_recomandata":"rice","incredere":0.99,...}
```

Dacă cele 3 comenzi merg → live. ✅
