# Hanime Cloud Web

A Flask-based web application that provides a polished browsing and playback experience for Hanime-style video discovery.

## Project Overview

Hanime Cloud Web is a server-rendered platform with API proxying and dynamic templates for:
- Trending feeds (daily/weekly/monthly/yearly)
- Search-driven discovery
- Tag-based browsing
- Stream playback with quality switching
- Public API-style JSON routes for integrations

The latest update focuses on a **premium modern dark UI**, improved responsiveness, and cleaner maintainable frontend architecture without changing existing route behavior.

## Features

- Modern responsive UI for mobile/tablet/desktop
- Sticky upgraded navbar + improved search UX
- Enhanced cards, tags, buttons, hover states, and visual hierarchy
- Loading overlay and smoother transitions for navigation actions
- Trending filters and search results with consistent component styling
- Video detail page with quality switch + social share + watched marker
- Browse page optimized for content scanning
- Custom 404/500 pages aligned with new design system
- Existing Flask endpoints preserved for compatibility

## UI Highlights

- Premium dark gradient theme with neon accent palette
- Glassmorphism-inspired cards and section surfaces
- Reusable design tokens and utility classes in one stylesheet
- Improved spacing and readability for long sessions
- Better touch ergonomics for handheld devices

## Tech Stack

- **Backend:** Python, Flask
- **Frontend:** Jinja2 Templates, Bootstrap 5, custom CSS/JS
- **Playback:** Video.js + IMA plugin + HLS sources
- **HTTP/API:** Requests

## Installation

### 1) Clone repository

```bash
git clone <your-repository-url>
cd HentaiHomies
```

### 2) Create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
```

### 3) Install dependencies

```bash
pip install -r requirements.txt
```

### 4) Run application

```bash
python main.py
```

App runs by default on:
- `http://0.0.0.0:8000`

## Environment Variables

Set these variables when using Telegram logging:

- `TOKEN`: Telegram bot token
- `CHAT`: Telegram chat ID

Example:

```bash
export TOKEN="<telegram_bot_token>"
export CHAT="<telegram_chat_id>"
```

## API Integration Notes

The app consumes upstream services for content data:
- Landing/trending and browse metadata via hosted API gateway
- Search data from search service endpoint
- Proxy endpoint rewrites/streams external playlist and media links

Public JSON routes include:
- `/api/video/<slug>`
- `/api/trending/<time>/<page>`
- `/api/browse`
- `/api/browse/<type>`
- `/api/browse/<type>/<category>/<page>`

## Folder Structure

```text
HentaiHomies/
├── main.py
├── requirements.txt
├── static/
│   ├── styles.css
│   ├── app.js
│   └── *.png
├── templates/
│   ├── base.html
│   ├── hm.html
│   ├── trending.html
│   ├── search.html
│   ├── browse.html
│   ├── cards.html
│   ├── video.html
│   ├── terms.html
│   ├── privacy.html
│   ├── 404.html
│   └── 500.html
└── README.md
```

## Scripts / Commands

- Start server:
  ```bash
  python main.py
  ```
- Basic syntax check:
  ```bash
  python -m compileall main.py
  ```

## Deployment Guide

1. Configure environment variables (`TOKEN`, `CHAT`) if logging is needed.
2. Install dependencies using `requirements.txt`.
3. Launch with a production WSGI server (e.g., Gunicorn) behind Nginx/Cloudflare.
4. Enable HTTPS and set proper caching headers for static assets.
5. Monitor upstream API availability and error logs.

## Future Scalability

Recommended next steps:
- Extract API client layer into service modules
- Add template partials/macros for shared cards/components
- Introduce caching for browse/trending/search responses
- Add observability (structured logs + health checks)
- Move styles/scripts to a versioned asset pipeline

## Contribution Guide

1. Fork and create a feature branch.
2. Keep route behavior backward compatible.
3. Run checks before opening PR.
4. Provide clear commit messages and PR descriptions.
5. Follow existing Flask + Jinja architecture patterns.

## License

This project is licensed under the [MIT License](LICENSE).
