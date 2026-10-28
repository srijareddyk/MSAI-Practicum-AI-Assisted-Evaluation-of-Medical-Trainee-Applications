# MSAI application desk

Vite + React UI for screening Northwestern MSAI master's packets.

```bash
npm install
npm run dev
```

The dev server proxies `/api` to `http://127.0.0.1:8000`. Start the API from the repo root:

```bash
python -m uvicorn api.server:app --reload --host 127.0.0.1 --port 8000
```
