# Bismarck-Mandan Location Scout

A mobile-first static web app that helps photographers find, filter, and shortlist portrait
session locations around Bismarck and Mandan, North Dakota, on an interactive map.

## Architecture

```
.
├── index.html              # App shell, markup for map/list views, filter panel, detail sheet
├── css/style.css           # All styling (mobile-first, dark-mode aware)
├── js/app.js               # CSV parsing, state, filtering, map + list rendering, favorites
├── data/locations.csv      # The location dataset (name, coords, category, session types, notes)
├── manifest.json           # PWA manifest (installable to a phone home screen)
├── service-worker.js       # Caches the app shell so location data works offline
└── icons/icon.svg          # App icon
```

**Stack:** Plain HTML/CSS/JavaScript · Leaflet + Leaflet.markercluster (via CDN) · OpenStreetMap tiles

No build step and no backend. Everything runs client-side, so it can be hosted on any static
host (GitHub Pages, Netlify, S3, etc.) and installed as a home-screen app on a phone.

## Running locally

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

(Any static file server works — the app just needs to be served over HTTP so the CSV `fetch`
call and the service worker aren't blocked by `file://` restrictions.)

## Features

- **Interactive map** — Leaflet map centered on Bismarck/Mandan, clustered markers colored by
  category (verified / scouted / secluded), tap a marker for full details.
- **List view** — same filtered results as a scrollable card list, sortable by name, confidence,
  or distance from the user.
- **Filters** — category, session type (wedding, engagement, senior, family, couples, portraits),
  confidence level, and free-text search, all combinable.
- **Shortlist** — star a location to save it to a personal shortlist (stored in the browser via
  `localStorage`, no account or backend needed) for planning a shoot with a client ahead of time.
- **Near me** — uses browser geolocation to sort locations by distance, for use in the field.
- **Directions** — one tap opens the location in Google Maps for turn-by-turn directions.
- **Works offline after first load** — a service worker caches the app shell and the location
  data; map tiles still need a connection.

## Location Dataset

`data/locations.csv` has one row per location with these columns:

| Column | Meaning |
|---|---|
| `name` | Location name |
| `latitude`, `longitude` | Coordinates (blank if not yet pinned) |
| `coordinate_quality` | `exact`, `approximate`, or `unknown` |
| `category` | `verified` (photographer-confirmed), `scouted` (researched, unconfirmed), or `secluded` (private/quiet spot) |
| `city` | Area/city description |
| `session_types` | Free-text session types (wedding, senior, family, etc.) — the app matches keywords out of this to build filter tags |
| `confidence` | How sure the research is that the spot is real/accessible (`Confirmed`, `Probable`, `Possible`, `Unverified`, plus qualifiers) |
| `notes` | Full description, access notes, permit warnings, etc. |

To add or edit locations, edit this CSV directly (keep it valid CSV — quote any field
containing a comma). The app has no in-browser editing UI by design; it's read-only browse
and filter.
