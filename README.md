# Bismarck-Mandan Location Scout

A map-based tool for finding portrait session locations around Bismarck and Mandan, North
Dakota. Built for photographers scouting spots ahead of a shoot and for pulling up on a phone
in the field.

## Features

- 🗺️ **Interactive map** — clustered pins colored by category (verified / scouted / secluded)
- 📋 **List view** — the same results as sortable cards (name, confidence, or distance from you)
- 🔍 **Filters** — category, session type, confidence, and text search, all combinable
- ⭐ **Shortlist** — star locations to plan a shoot, saved on your device
- 📍 **Near me** — sort by distance using your phone's location
- 🧭 **Directions** — one tap to Google Maps
- 📴 **Works offline** after the first visit (location data is cached; map tiles need a signal)

## Run locally

```bash
python3 -m http.server 8000
# open http://localhost:8000
```

## Tech stack

Plain HTML/CSS/JavaScript, no build step. Leaflet + Leaflet.markercluster for the map,
OpenStreetMap tiles. Data lives in `data/locations.csv`.

## Deploy

Static files only, so any static host works: GitHub Pages, Netlify, Vercel, S3 + CloudFront.
