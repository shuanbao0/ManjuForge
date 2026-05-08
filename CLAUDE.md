# CLAUDE.md

This file gives Claude Code (claude.ai/code) the orientation it needs to work in this repository.

## Project Overview

**ManjuForge Studio** (npm package name `manju-forge`, repo `ManjuForge`, originally LumenX Studio upstream) is an **AI-native short comic / micro-drama production platform**. It turns a novel-style script into a finished video by chaining: *script analysis → art direction → asset generation → storyboard scripting → storyboard image generation → motion (i2v/r2v) generation → assembly + audio mixing*.

The product ships in three forms:
- **Local dev**: FastAPI backend + Next.js frontend running side-by-side (`npm run dev`).
- **Desktop app**: PyInstaller bundle that boots the FastAPI server in a thread and renders the built frontend inside a `pywebview` window (`main.py`, `build_mac.sh`, `build_windows.ps1`).
- **Docker**: separate `Dockerfile.backend` / `Dockerfile.frontend`, wired by `docker-compose.yml`.

User data (logs, config, projects) lives under `~/.manju-forge/` regardless of platform.

## Architecture

### Top-level layout

```
ManjuForge/
├── main.py                 # Desktop entrypoint: spawns uvicorn thread + pywebview window
├── src/                    # Python backend
│   ├── apps/comic_gen/     # The actual product surface (FastAPI app + pipeline)
│   ├── models/             # AI provider clients (Wanx, Doubao, Kling, Vidu, Qwen-VL, Image)
│   ├── audio/tts.py        # Text-to-speech
│   ├── utils/              # OSS, provider routing, media refs, system check, logging
│   └── config.py           # YAML + env config loader
├── frontend/               # Next.js 14 + React 18 + TypeScript + Tailwind
│   ├── src/app/page.tsx    # Single-page hash router (Library / Series / Project / Settings)
│   ├── src/components/     # canvas, common, layout, library, modals, modules, project, series, settings
│   ├── src/lib/api.ts      # Backend HTTP client (~28 KB; wraps every backend route)
│   └── src/store/projectStore.ts  # Zustand store
├── tests/                  # Pytest suites (provider routing, media refs, cross-phase, series, ...)
├── scripts/                # Dev helpers + OSS migration utilities
├── docker/, Dockerfile.*   # Containerised deployment
├── build_mac.sh / build_windows.ps1  # Desktop packaging via PyInstaller
└── docs/images/            # Product screenshots referenced by README
```

### Backend (`src/apps/comic_gen`)

This is the heart of the product. Files map roughly to pipeline stages:

| File | Responsibility |
|------|----------------|
| `api.py` | The single FastAPI app. ~80+ routes for series/projects/assets/storyboard/video/audio/export. Mounts `/files/*` aliases for `output/`. Hosts `/debug/config`, `/system/check`, `/upload`, `/config/env`. |
| `models.py` | Pydantic models — `Script`, `Series`, `VideoTask`, `ImageAsset`, `AssetUnit`, `ProviderRoutingConfig`, etc. |
| `pipeline.py` | `ComicGenPipeline` — top-level orchestrator that composes the per-stage generators. Persists state to `output/projects.json`. Includes path-traversal hardening (`_safe_resolve_path`, `_validate_safe_id`). |
| `llm.py`, `llm_adapter.py` | Script processing, entity extraction, prompt polishing (Qwen/OpenAI-compatible). |
| `assets.py` | Character / scene / prop image generation. |
| `storyboard.py` | Storyboard frame extraction + per-frame image generation. |
| `video.py` | i2v / r2v video generation, dispatches to provider clients. |
| `audio.py` | Voice acting + SFX synthesis. |
| `export.py` | Final video stitching via FFmpeg. |
| `style_presets.json` | Built-in art-direction presets. |

### Model Instance architecture (Vendor → Instance → Reference)

**This is the canonical way to configure and run any AI model in the product.**
Settings does not configure "vendors" or pick "current LLM" — every model is a
``ModelInstance`` row owned by a user, and projects reference instances by id.

Three layers:

1. **Vendor** (system-known, immutable) — DashScope / OpenAI / Anthropic /
   DeepSeek / Kling / Vidu / Pixverse / Doubao / Hailuo. Surfaced for UI
   purposes through ``src/utils/vendor_connectors.py`` +
   ``src/utils/model_catalog.py``; users never CRUD vendors.
2. **ModelInstance** (per-user) — pairs a vendor + ``model_name`` +
   ``credentials`` + ``base_url`` + a user-chosen ``display_name``. Users
   may have many per type; one is marked ``is_default``. CRUD via
   ``GET/POST/PUT/DELETE /me/instances`` and
   ``POST /me/instances/{id}/{set-default,test}``.
3. **Reference** — ``ModelSettings`` on Script/Series stores
   ``llm_instance_id`` / ``t2i_instance_id`` / ``i2i_instance_id`` /
   ``i2v_instance_id`` / ``tts_instance_id`` (all UUIDs, all optional).
   ``None`` falls back to the user's default instance for that type.

Files:
- ``src/models/instance.py`` — ``InstanceType`` enum, ``ModelInstance``
  dataclass with ``to_public_dict`` that scrubs credentials.
- ``src/models/instance_repository.py`` — Repository pattern, Fernet
  encryption, "single default per (user, type)" invariant.
- ``src/models/instance_testers.py`` — Strategy registry: per-type
  connectivity probes (LLM ping, DashScope key presence check, etc.).
- ``src/auth/me_routes.py`` — REST surface.
- ``src/auth/service.py::_seed_default_instances`` — onboarding hook.
- ``src/runtime.py::with_instance`` — Context Manager that binds an
  instance to the current call so ``get_cred()`` resolves from
  ``instance.credentials`` first, then env. **All pipeline stages must
  enter this scope before invoking a model client** (see
  ``src/apps/comic_gen/instance_resolver.py::scoped_instance``).
- ``src/apps/comic_gen/llm_adapter.py`` — reads model_name + base_url +
  credentials from the active instance when one is bound.

Adding a new vendor:
1. Append a ``VendorConnector`` to ``src/utils/vendor_connectors.py``.
2. Register the family in ``src/utils/provider_registry.py`` (so
   provider routing resolves the model name).
3. Mirror the vendor metadata in
   ``frontend/src/components/settings/InstanceWizard.tsx::VENDORS``.
4. (Optional) add a real client adapter in ``src/models/`` and register
   it in ``src/models/video_dispatcher.py``.

### Provider routing (critical concept)

ManjuForge is **DashScope-first** but supports vendor-direct routing per model family.

- `src/utils/provider_registry.py` defines `ProviderFamilyConfig` for each model family (`wan2.6-`, `kling-`, `vidu`, `pixverse-`). Each family declares: `backend_default`, `backend_env_key`, `credential_sources`, supported modalities, and `image_input_mode` / `audio_input_mode` / `reference_video_input_mode` per backend.
- `resolve_provider_backend(model_name, env)` reads the family's env key (e.g. `KLING_PROVIDER_MODE`) and returns `"dashscope"` or `"vendor"`.
- `src/utils/provider_media.py` translates a `media_ref` (the project-side stable handle) into the `resolved_media_input` payload the chosen provider actually wants (DashScope multimodal message / temp file URL / vendor base64 / vendor URL).
- `src/utils/media_refs.py` defines the `media_ref` abstraction (local relative path or OSS object key).

When touching provider code, **preserve these invariants** (also called out in `CONTRIBUTING.md`):
1. **Local-first storage** — every uploaded/generated asset is written to `output/` first; that is the durable project source.
2. **OSS is optional** — purely a mirror + signed-URL service; no feature should hard-require it.
3. **DashScope-first** — default backend for every supported family.
4. **Vendor-direct stays available** — Kling/Vidu/Pixverse direct APIs remain when the user opts in.

Vocabulary used consistently across code, PRs, and docs:
- `storage_mode`: `local_only` | `local_plus_oss`
- `provider_backend`: `dashscope` | `vendor`
- `media_ref`: stable project-side reference
- `resolved_media_input`: provider-ready request payload

### Frontend (`frontend/`)

- **Next.js 14 App Router**, mostly client-rendered. The whole product lives behind a hash router in `src/app/page.tsx` that switches between Library / Series detail / Project / Settings / Asset Library views.
- **State**: a single Zustand store at `src/store/projectStore.ts` (~23 KB).
- **Backend client**: `src/lib/api.ts` (~28 KB) wraps every FastAPI route. Dev rewrites `/api-proxy/*` → backend (`next.config.mjs`).
- **Build target**: in production, `next build` outputs to `../static/` with `basePath: '/static'` so the FastAPI server can serve it directly from the desktop bundle. The Docker build sets `DOCKER_BUILD=true` to flip to a standalone `out/` dir served by nginx.
- **Three.js / R3F** is used in `components/canvas/` for the creative canvas; `framer-motion` and `lucide-react` cover motion + icons.
- Tests use **Vitest** with two configs (`vitest.config.mts` for headless, `vitest.ui.config.mts` for UI-component tests).

## Common Commands

### Local development (the easy way)

```bash
# From the repo root — concurrently runs backend, frontend, and opens the browser
npm install
npm run dev
```

This is wired by `package.json` → `scripts/dev-setup.js` + `scripts/start-backend.js` + `scripts/open-browser.js`.

### Run pieces individually

```bash
# Backend (port 17177, with reload)
./start_backend.sh
# equivalent to:  python -m uvicorn src.apps.comic_gen.api:app --reload --port 17177 --host 0.0.0.0

# Frontend (port 3000)
./start_frontend.sh
# equivalent to:  cd frontend && npm install && npm run dev
```

The default ports differ between modes: dev backend uses **17177**, desktop bundle also uses **17177**, but the README's quick-start references **8000** — the actual binding is 17177.

### Tests

```bash
# Python tests (pytest config in pyproject.toml — testpaths = tests/)
pytest
pytest tests/test_provider_registry.py        # one file
pytest --cov=src tests/                       # with coverage

# Frontend tests (Vitest)
cd frontend && npm test
cd frontend && npm run test:ui                # UI/jsdom variant
cd frontend && npm run test:all               # both
```

### Lint / format

```bash
# Python — black + isort + flake8 (configs in pyproject.toml)
black src/
flake8 src/

# Frontend
cd frontend && npm run lint
```

### Desktop packaging

```bash
./build_mac.sh         # produces dist_mac/ManjuForge Studio.app + .dmg
./build_windows.ps1    # Windows equivalent
```

The Mac script also builds the frontend into `static/` and bundles `bin/ffmpeg`. **Do not commit** `static/`, `output/`, `dist_mac/`, `dist_windows/`, or `bin/` — they are all in `.gitignore`.

### Docker

```bash
cp .env.example .env   # fill in DASHSCOPE_API_KEY (and OSS keys if needed)
docker compose up -d --build
# backend :17177, frontend (nginx) :3000
```

## Configuration

Configuration is driven entirely by environment variables, loaded via `python-dotenv` from `.env` at the project root. The desktop app additionally writes to `~/.manju-forge/config.json` and the in-app Settings page persists changes back to `.env` via `POST /config/env`.

Four supported runtime modes (see README §"运行模式与必填配置" / USER_MANUAL.md):

| Mode | Required env | Notes |
|------|--------------|-------|
| 1. DashScope-only | `DASHSCOPE_API_KEY` | Single-machine local creation, no OSS. |
| 2. DashScope + OSS | + `ALIBABA_CLOUD_ACCESS_KEY_ID/SECRET`, `OSS_BUCKET_NAME`, `OSS_ENDPOINT` | Adds cloud mirror + signed URLs. |
| 3. + Kling vendor | + `KLING_PROVIDER_MODE=vendor`, `KLING_ACCESS_KEY`, `KLING_SECRET_KEY` | Only Kling models route to vendor API. |
| 4. + Vidu vendor | + `VIDU_PROVIDER_MODE=vendor`, `VIDU_API_KEY` | Only Vidu models route to vendor API. |

Optional LLM swap: set `LLM_PROVIDER=openai` plus `OPENAI_API_KEY` / `OPENAI_BASE_URL` / `OPENAI_MODEL` to use any OpenAI-compatible endpoint (DeepSeek, Ollama, etc.) for script processing — see `.env.example` for examples.

International endpoints: override `DASHSCOPE_BASE_URL`, `KLING_BASE_URL`, `VIDU_BASE_URL` for overseas deployment.

## Code Style

From `pyproject.toml`:
- **Python 3.11+**, line length **100**, formatted with **black** + **isort** (black profile), linted with **flake8** (`E203`, `W503` ignored).
- Type hints expected on public functions; docstrings on public APIs.
- `mypy` is configured but `disallow_untyped_defs = false` — typing is encouraged, not enforced.

Frontend:
- TypeScript strict, ESLint `next/core-web-vitals`. Prefer functional components + named exports. `npm run lint` (build does not block on lint/type errors — see `next.config.mjs`).

Commit messages follow **Conventional Commits**: `feat(scope): ...`, `fix(scope): ...`, etc. Branch naming: `feature/...`, `fix/...`, `docs/...`, `refactor/...`, `test/...`. Details in `CONTRIBUTING.md`.

## Things to Watch

- **Storage layout**: `output/` is the source of truth. Subfolders include `output/uploads`, `output/video`, `output/assets`, `output/storyboard`, `output/audio`, `output/export`, `output/video_inputs`. Project state lives in `output/projects.json`.
- **Static mounts**: `api.py` mounts several aliased paths (`/files/outputs/videos`, `/files/outputs/assets`, `/files/videos`, `/files/assets`, `/files`) to absorb legacy plural/singular paths in older `projects.json` entries. Don't simplify without checking project-data migration.
- **PyInstaller hidden imports**: `build_mac.sh` and `build_windows.ps1` enumerate `--hidden-import` flags explicitly. New top-level dependencies usually need a corresponding entry, plus possibly a hook in `.pyinstaller-hooks/`.
- **FFmpeg**: required at runtime for export. Bundled to `bin/ffmpeg` on Mac/Windows packaging; on Docker installed via apt; locally must be on `PATH`. Lookup logic lives in `src/utils/system_check.py::get_ffmpeg_path`.
- **Proxy bypass**: `start_backend.sh`, `Dockerfile.backend`, and `docker-compose.yml` all set `NO_PROXY=*.aliyuncs.com,localhost,127.0.0.1`. macOS PAC rules can otherwise break DashScope/OSS traffic.
- **Path-traversal**: when adding endpoints that accept user-supplied IDs or relative paths, use `pipeline._validate_safe_id` and `pipeline._safe_resolve_path` rather than ad-hoc `os.path.join`.
- **Docker nginx allowlist**: every new top-level FastAPI prefix (e.g. adding `@app.get("/registry/...")`) MUST be added to the proxied path alternation in `docker/nginx.conf`. Otherwise nginx falls back to the SPA `index.html` and the browser gets `Unexpected token '<', "<!DOCTYPE "...` instead of JSON. The `tests/test_nginx_routing.py` guard auto-enumerates FastAPI prefixes and fails CI if the nginx config drifts — keep both in sync.
- **Settings is ModelInstance-driven**: per-user model configurations live in the `model_instances` table; the Settings page CRUDs them via `/me/instances/*`. Vendor + model catalog files (`vendor_connectors.py`, `model_catalog.py`) are pure metadata (display names, suggested model ids, docs links) — adding a new provider means: (1) `VendorConnector` entry, (2) `ProviderFamilyConfig` in `provider_registry.py`, (3) (optional) real client + dispatcher adapter, (4) mirror in `InstanceWizard.tsx::VENDORS`. **Do not** add per-user keys to `src/auth/credentials.py::ALLOWED_KEYS` for new vendors — those are now stored on the instance row's encrypted blob.

## Useful Pointers

- API surface: live Swagger UI at `http://localhost:17177/docs` once the backend is running.
- Diagnostics: `GET /debug/config` shows OSS state + cwd; `GET /system/check` reports environment readiness.
- Style presets: `src/apps/comic_gen/style_presets.json` (referenced by Art Direction stage).
- User-facing docs: `README.md` (中文) / `README_EN.md` / `USER_MANUAL.md` / `CONTRIBUTING.md`.
