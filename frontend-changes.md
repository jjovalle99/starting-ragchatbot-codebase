# Frontend Changes

## Code Quality (Prettier)

Added Prettier as the automatic code formatter for the frontend codebase, applied consistent formatting to all frontend source files, and created development scripts for running quality checks.

### New Files
- `frontend/package.json` — Node.js project with Prettier dev dependency and npm scripts (`format`, `format:check`, `quality`)
- `frontend/.prettierrc` — Prettier config (semicolons, single quotes, 4-space indent, trailing commas, 100-char width, LF)
- `frontend/.prettierignore` — Ignores `node_modules/` and `package-lock.json`
- `frontend/quality.sh` — Shell script to run all frontend quality checks

### How to Use
```bash
cd frontend && npm install
npm run format          # Auto-format
npm run format:check    # Check only (CI-friendly)
./quality.sh            # Full quality check
```

## Dark/Light Theme Toggle

Added a toggle button that allows users to switch between dark and light themes with smooth transitions and localStorage persistence.

### Changes
- `frontend/index.html` — Added theme toggle button with moon/sun SVG icons and accessibility attributes
- `frontend/style.css` — Added light theme CSS variables, smooth transitions, and toggle button styles
- `frontend/script.js` — Added `initializeTheme()` and `toggleTheme()` functions with localStorage persistence
