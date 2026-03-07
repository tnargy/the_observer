# The Observer — Dashboard

Minimal dashboard for The Observer (frontend). This README covers local development for the dashboard only.

Prerequisites
- Node.js (16+) and npm

Quick start

1. Install dependencies

```bash
cd dashboard
npm install
```

2. Copy environment example and edit if needed

```bash
cp .env.example .env
# Edit VITE_API_URL if your collector runs elsewhere
```

3. Start dev server

```bash
npm run dev
```

The dashboard will open at the port Vite chooses (default: http://localhost:5173). Ensure the Collector API is reachable at the `VITE_API_URL` you set.

Build & preview

```bash
npm run build
npm run preview
```

Notes
- The dashboard expects the Collector API to implement `/api/agents` and `/api/agents/{id}/metrics` as documented in the TRD.
- If you want hot-reload styles, Tailwind is preconfigured; run `npm run dev` after editing `src/index.css`.
