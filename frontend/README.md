# Kuyash Place — frontend

Next.js 16 (App Router) + React 19 + TypeScript + Tailwind v4. The customer site and the kitchen display screen.

Every screen runs on the Django API in [`../backend`](../backend): prices, availability, orders and order state all come from the server. There is no business logic here.

## Running it

See [`../SETUP.md`](../SETUP.md). The short version:

```bash
npm install
cp .env.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
npm run dev                  # http://localhost:3000
```

The backend must be running, or every screen shows a network error.

## Commands

| Command | What |
|---|---|
| `npm run dev` | Development server (webpack, not turbopack) |
| `npm run build` / `npm run start` | Production build and server |
| `npm run lint` | ESLint — clean today, keep it that way |
| `npm run typecheck` | `tsc --noEmit` |
| `npm run api:sync` | Regenerate `lib/api/openapi.yml` and `lib/api/schema.d.ts` from the backend |

There is no test runner here; the suite lives in the backend.

## Rules that matter

- **Use the existing design system.** Import `components/ui/*` and the brand tokens in `app/globals.css`; don't introduce a new one.
- **No money arithmetic in components.** Render `Money.display` from the API.
- **No card fields, ever.** Payment is a redirect to the provider's hosted page.
- **No `fetch` in components.** Everything goes through `api()` in `lib/api/client.ts`.
- **Never hand-edit `lib/api/schema.d.ts`** — run `npm run api:sync`.

Each of the first three is enforced by a CI gate (`backend/scripts/check-no-*.sh`).

## Where things live

| Path | What |
|---|---|
| `app/` | Routes — thin shells that compose features |
| `components/features/<feature>/` | One folder per domain, with an `index.ts` barrel |
| `components/ui/` | shadcn/ui primitives |
| `lib/api/` | The backend boundary: `client.ts`, generated `schema.d.ts`, typed helpers |
| `proxy.ts` | Next 16's middleware: the Content Security Policy and route gating |

Further reading: [`../API-DOCS.md`](../API-DOCS.md) for endpoints, [`../backend/docs/FRONTEND_INTEGRATION.md`](../backend/docs/FRONTEND_INTEGRATION.md) for how each screen was wired.
