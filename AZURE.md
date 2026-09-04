# Host Optival on a personal Azure account

**Do not upload real applicant PDFs.** A personal Azure account is not a FERPA environment. Do **not** upgrade the subscription or remove the spending limit if you want the card unused.

## Realistic path on this trial: Azure OpenAI (no VM)

Your Free Trial / Students account **cannot create VMs or App Service** (compute quota 0). You can still run the **website on your laptop** and send Doc A/B prompts to **Azure OpenAI**. That uses the **$200 credit**, not the card, while the spending limit is on.

1. Portal → **Azure OpenAI** (or **Azure AI Foundry**) → Create  
   Subscription: **Azure subscription 1** (Free Trial)  
   If Create is blocked, Microsoft has not enabled OpenAI on this offer — then stay on local Ollama.
2. Deploy a cheap chat model, e.g. **gpt-4o-mini** (note the **deployment name**).
3. Keys and Endpoint → copy endpoint + key.
4. In the project folder:

```bash
cp .env.example .env
# edit .env: LLM_PROVIDER=azure, endpoint, key, deployment name
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn api.server:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 — status should read **Ready · Azure OpenAI**.

Pay-as-you-go / upgrade: **do not**. If Azure asks you to remove the spending limit to create OpenAI, skip it.

---

## VM hosting (currently blocked on this account)

This app is a FastAPI UI plus a local Ollama model. A **Linux VM + Docker Compose** is the path that works when the subscription actually allows VMs.

## 1. Create the Azure account

1. Open [https://azure.microsoft.com/free/](https://azure.microsoft.com/free/)
2. Sign in with a Microsoft account (or create one)
3. Complete identity verification (card hold is common; usually not charged if you stay in free credit)
4. Pick **Pay as you go** after the trial if asked — you can still deallocate the VM so it stops billing compute

Useful extras:

- [Azure for Students](https://azure.microsoft.com/free/students/) if you have a `.edu` email (credits, no card on some offers)

Install tools on your Mac:

```bash
brew install azure-cli
# rsync/ssh are already on macOS
```

You also need **Docker on the VM** (the deploy script installs that). You do **not** need Docker Desktop locally.

Log in:

```bash
az login
az account show
```

## 2. Deploy (recommended)

From the repo root, with Azure CLI installed:

```bash
chmod +x scripts/azure-deploy.sh
./scripts/azure-deploy.sh
```

What it creates:

| Resource | Purpose |
|----------|---------|
| Resource group `optival-rg` | Container for everything |
| Ubuntu 22.04 VM `optival-vm` | Runs the app |
| Size `Standard_B4ms` (4 vCPU / 16 GB) | Enough for **qwen2.5:7b** |
| Ports 80 and 8000 | Browser access |
| Docker Compose | `app` (UI+API) + `ollama` + model pull |

Default cloud model is **`qwen2.5:7b`** (fits a personal VM). Local laptops can keep `qwen3:14b`.

Override if you want:

```bash
AZURE_LOCATION=centralus AZURE_VM_SIZE=Standard_B4ms DEFAULT_MODEL=qwen2.5:7b ./scripts/azure-deploy.sh
```

First boot can take **10–20 minutes** while Docker builds and Ollama pulls the model. Then open:

```
http://<VM_PUBLIC_IP>
```

Check:

```bash
curl http://<VM_PUBLIC_IP>/api/health
```

`ollama.ok` should become true after the pull finishes. **Objective metrics** works even before the model is ready.

## 3. Cost control (important)

A B4ms VM left running will spend trial credit.

```bash
# Stop compute billing (keeps the disk)
az vm deallocate -g optival-rg -n optival-vm

# Start again
az vm start -g optival-rg -n optival-vm
# IP may change unless you use a static public IP

# Tear everything down
az group delete -n optival-rg --yes --no-wait
```

## 4. What Azure is running

```
Browser
   │
   ▼
:80 / :8000  →  FastAPI (built React UI + /api)
                   │
                   ▼
              Ollama in Docker  (DEFAULT_MODEL, usually qwen2.5:7b)
```

Env vars on the app container:

| Variable | Meaning |
|----------|---------|
| `OLLAMA_HOST` | `http://ollama:11434` inside Compose |
| `DEFAULT_MODEL` | Model name shown in the UI |
| `CORS_ORIGINS` | `*` in Azure so the public IP works |

## 5. If `az vm create` fails on size/quota

Try a smaller or different SKU:

```bash
AZURE_VM_SIZE=Standard_B2ms ./scripts/azure-deploy.sh
```

`B2ms` is 8 GB — use a small model such as `llama3.2:3b`:

```bash
AZURE_VM_SIZE=Standard_B2ms DEFAULT_MODEL=llama3.2:3b ./scripts/azure-deploy.sh
```

`qwen3:14b` needs a larger VM (≈16 GB+ RAM) and is slow without a GPU. Personal-account GPU quota is often **zero** unless you request it.

## 6. Why not App Service only?

Azure App Service is fine for a website, not for pulling and serving a local LLM next to long screening jobs. This product’s Doc A/B path is Ollama. The VM keeps that architecture.
