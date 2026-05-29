# Sharing this project on GitHub

## 1. Log in to GitHub

- Open [https://github.com/login](https://github.com/login) and sign in (or create an account).

## 2. Create an empty repository on the website

1. Click **+** → **New repository**
2. Name: `BenchAssist-IL-Audit` (or your team name)
3. **Private** recommended (course / API keys in local `.env` only)
4. Do **not** add a README, `.gitignore`, or license (this repo already has them)
5. Click **Create repository**

## 3. Push from your machine

In Terminal, from this folder:

```bash
cd /Users/tymoribrahim/Desktop/RAI_Proiect/BenchAssist-IL-Audit

# Replace YOUR_USERNAME with your GitHub username
git remote add origin https://github.com/YOUR_USERNAME/BenchAssist-IL-Audit.git
git branch -M main
git push -u origin main
```

GitHub will ask you to sign in (browser or personal access token).

### Using SSH instead (optional)

```bash
git remote add origin git@github.com:YOUR_USERNAME/BenchAssist-IL-Audit.git
git push -u origin main
```

## 4. What your partners do

```bash
git clone https://github.com/YOUR_USERNAME/BenchAssist-IL-Audit.git
cd BenchAssist-IL-Audit
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,datasets,genai]'
cp .env.example .env
# Edit .env: add GEMINI_API_KEY, set MODEL_PROVIDER=gemini if needed
python -m benchassist.verify_pipeline --provider mock
streamlit run app.py
```

See [README.md](README.md) for the full pipeline.

## Security

- **Never commit `.env`** — it is in `.gitignore` and holds your API key.
- Generated outputs under `results/` and `data/` are ignored by default; partners re-run the pipeline or you share outputs separately.
