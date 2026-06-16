# Deploy the MRSW RentConnect app (live)

The full front-end: a campus **hostel marketplace** (browse → book), owner listing
tools, and a tenant **rent-readiness wallet** — all wired to your live API. Built with
React (Vite); Render compiles it on **its** servers, so you run nothing locally.

This talks to your backend at `https://mrsw-rentconnect.onrender.com` by default
(set in `src/App.jsx` as `DEFAULT_API`). To point elsewhere, click the **API:** link
in the footer, or change `DEFAULT_API`.

## Put it online (browser only)

1. **GitHub:** new repo (e.g. `mrsw-rentconnect-web`) → **Add file → Upload files** →
   drag the **contents** of the `mrsw-web` folder to the repo root → Commit.
2. **Render → New → Static Site**, pick the repo:
   - **Build Command:** `npm install && npm run build`
   - **Publish Directory:** `dist`
   Click **Create Static Site.** First build takes a few minutes.
   *(Or New → Blueprint — `render.yaml` has these settings.)*
3. Open the URL. The hostel marketplace is the landing page (public, no login).

## What works, end to end

- **Browse & search hostels** — filter by university, room type, price; live availability.
- **Listing detail → Book** — sign in / create an account, request beds, owner is notified.
- **Tenant wallet** — live readiness meter, five funds, trust score, and your bookings.
- **Owner** — list a hostel (with photo URLs), see your listings, confirm/decline bookings.

Demo logins: `ama@example.com` / `password123` (student) and
`campus.living@example.com` / `password123` (hostel owner). Or register fresh —
choosing "A hostel owner" lets you list immediately.

## Run locally (optional, needs Node)

```bash
npm install
npm run dev      # http://localhost:5173
```
For local dev against a local backend, click the footer **API:** link and set it to
`http://localhost:8000`.

## Notes

- The backend is a separate Render service. If the app shows "can't reach the API,"
  the free backend is asleep — wait ~30–60s and retry.
- Hostel photos are placeholder image URLs for now. Real **upload** needs object
  storage (Cloudflare R2 / Supabase) — the next infrastructure step.
