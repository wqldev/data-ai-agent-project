# Deploy to Render (manual, after GitHub push)

## 1. Push this repo to GitHub

In this folder (`20260713_AI_agent`):

```bash
gh auth login
gh repo create ai-agent-data-analysis --private --source=. --remote=origin --push
```

Or create an empty repo on GitHub, then:

```bash
git remote add origin https://github.com/<YOUR_USER>/ai-agent-data-analysis.git
git push -u origin main
```

## 2. Deploy on Render

1. Open https://dashboard.render.com/
2. **New** → **Blueprint**
3. Connect the GitHub repo
4. Render will read `render.yaml` and create Web Service `ai-agent-data-analysis`
5. Wait for build; open the `*.onrender.com` URL

### Manual Web Service (alternative)

- Runtime: Python
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
- Health Check Path: `/api/health`

## 3. Use the app

Open the Render URL → configure API Key in the top-right → start analysis.
