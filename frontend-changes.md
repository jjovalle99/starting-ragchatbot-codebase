# Frontend Changes: Dark/Light Theme Toggle

## Overview
Added a toggle button that allows users to switch between dark and light themes with smooth transitions and localStorage persistence.

## Files Modified

### `frontend/index.html`
- Added a `<button>` element with id `themeToggle` positioned before the main container
- Button contains two inline SVGs: a moon icon (visible in dark mode) and a sun icon (visible in light mode)
- Includes `aria-label` and `title` attributes for accessibility

### `frontend/style.css`
- **Light theme variables**: Added `[data-theme="light"]` selector with a full set of light-friendly CSS custom properties (light backgrounds, dark text, adjusted surface/border colors)
- **Theme transition**: Added a global transition rule on `background-color`, `color`, `border-color`, and `box-shadow` (0.3s ease) for smooth switching
- **Toggle button styles**: Added `.theme-toggle` styles including fixed positioning (top-right), circular shape, hover/focus states, and icon visibility toggling via `[data-theme="light"]` selectors
- **Code block fix**: Changed `rgba(0, 0, 0, 0.2)` to `rgba(0, 0, 0, 0.1)` on `.message-content code` and `.message-content pre` for better readability in light mode

### `frontend/script.js`
- Added `themeToggle` DOM element reference
- Added `initializeTheme()` function that reads the saved theme from `localStorage` and applies it on page load
- Added `toggleTheme()` function that switches the `data-theme` attribute on `<body>`, updates the `aria-label`, and persists the choice to `localStorage`
- Wired up the toggle button click event in `setupEventListeners()`

## Design Decisions
- **CSS custom properties**: All theme colors are driven by CSS variables in `:root` (dark, default) and `[data-theme="light"]`, so every existing element automatically adapts
- **`data-theme` on `<body>`**: Used as the theme selector to keep specificity simple
- **localStorage persistence**: Theme preference survives page refreshes
- **Icon swap via CSS**: The sun/moon icons toggle visibility through CSS `display` rules based on the `data-theme` attribute, avoiding extra JS DOM manipulation
- **Accessibility**: Button has `aria-label` that updates dynamically, is keyboard-focusable, and has a visible focus ring
