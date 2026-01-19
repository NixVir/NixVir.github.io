# CSS Custom Properties Reference

This document describes the CSS custom properties (design tokens) defined in `/static/css/shared-theme.css`.

---

## Usage

Include the shared theme CSS in any HTML page:

```html
<link rel="stylesheet" href="/css/shared-theme.css">
```

Access variables in your CSS:

```css
.my-element {
    background: var(--bg-card);
    color: var(--text-primary);
    border: 1px solid var(--border);
}
```

---

## Background Colors

| Variable | Value | Usage |
|----------|-------|-------|
| `--bg-deep` | `#0a0e14` | Page background, deepest layer |
| `--bg-card` | `#111820` | Card backgrounds, panels |
| `--bg-elevated` | `#1a2230` | Elevated surfaces, hover states |

### Visual Hierarchy
```
--bg-deep (darkest) → --bg-card → --bg-elevated (lightest)
```

---

## Border Colors

| Variable | Value | Usage |
|----------|-------|-------|
| `--border` | `#2a3444` | Standard borders, dividers |
| `--border-light` | `#3a4454` | Subtle borders, secondary elements |

---

## Text Colors

| Variable | Value | Usage |
|----------|-------|-------|
| `--text-primary` | `#e8ecf2` | Main body text, headings |
| `--text-secondary` | `#8892a2` | Secondary text, labels |
| `--text-muted` | `#5c6678` | Disabled text, hints |

### Helper Classes
```css
.text-primary { color: var(--text-primary); }
.text-secondary { color: var(--text-secondary); }
.text-muted { color: var(--text-muted); }
```

---

## Accent Colors - Cold/Blue Spectrum

| Variable | Value | Usage |
|----------|-------|-------|
| `--accent-cold` | `#3b82f6` | Primary blue accent |
| `--accent-cold-bright` | `#60a5fa` | Bright blue for highlights |
| `--accent-blue` | `#3b82f6` | Alias for --accent-cold |
| `--accent-blue-bright` | `#60a5fa` | Alias for --accent-cold-bright |

---

## Accent Colors - Warm/Orange Spectrum

| Variable | Value | Usage |
|----------|-------|-------|
| `--accent-warm` | `#f97316` | Primary orange accent |
| `--accent-warm-bright` | `#fb923c` | Bright orange for highlights |
| `--accent-orange` | `#f97316` | Alias for --accent-warm |

---

## Status Colors

| Variable | Value | Usage |
|----------|-------|-------|
| `--success` | `#10b981` | Success states, positive values |
| `--accent-green` | `#10b981` | Alias for --success |
| `--warning` | `#f59e0b` | Warning states, caution |
| `--accent-yellow` | `#eab308` | Yellow accent |
| `--danger` | `#ef4444` | Error states, negative values |
| `--accent-red` | `#ef4444` | Alias for --danger |
| `--accent-purple` | `#a855f7` | Purple accent for special items |

### Helper Classes
```css
.text-success { color: var(--success); }
.text-warning { color: var(--warning); }
.text-danger { color: var(--danger); }
```

---

## Geographic/Map Colors

| Variable | Value | Usage |
|----------|-------|-------|
| `--geo-fill` | `#1e293b` | Map polygon fills |
| `--geo-stroke` | `#334155` | Map boundary strokes |

---

## Snow Visualization Colors

| Variable | Value | Usage |
|----------|-------|-------|
| `--snow-heavy` | `#dbeafe` | Heavy snow cover (>80%) |
| `--snow-moderate` | `#60a5fa` | Moderate snow cover (40-80%) |
| `--snow-light` | `#1e40af` | Light snow cover (10-40%) |
| `--snow-none` | `#475569` | No snow cover (<10%) |

---

## Snowpack Color Scale (SNOTEL)

Used for % of normal snowpack visualization:

| Variable | Value | Range | Description |
|----------|-------|-------|-------------|
| `--swe-drought` | `#dc2626` | <50% | Drought conditions |
| `--swe-below` | `#f97316` | 50-75% | Below normal |
| `--swe-low` | `#facc15` | 75-90% | Low normal |
| `--swe-normal` | `#22c55e` | 90-110% | Normal |
| `--swe-above` | `#3b82f6` | 110-130% | Above normal |
| `--swe-high` | `#8b5cf6` | >130% | Exceptional |

---

## Component Classes

### Cards

```css
.card {
    background: var(--bg-card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.25rem;
}

.card-elevated {
    background: var(--bg-elevated);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.25rem;
}
```

### Popup/Tooltip Rows

```css
.popup-grid {
    display: grid;
    gap: 4px;
    font-size: 0.9em;
}

.popup-row {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
}

.popup-label {
    color: var(--text-secondary);
}

.popup-value {
    font-family: 'JetBrains Mono', monospace;
}

.popup-value-bold {
    font-family: 'JetBrains Mono', monospace;
    font-weight: bold;
}
```

### Typography

```css
.mono {
    font-family: 'JetBrains Mono', monospace;
}
```

---

## Background Gradients

### Default (Blue/Orange)
```css
.bg-gradient {
    background:
        radial-gradient(ellipse at 15% 10%, rgba(59, 130, 246, 0.06) 0%, transparent 50%),
        radial-gradient(ellipse at 85% 90%, rgba(249, 115, 22, 0.04) 0%, transparent 50%),
        var(--bg-deep);
}
```

### Green Variant (Dashboard)
```css
.bg-gradient-green {
    background:
        radial-gradient(ellipse at 15% 10%, rgba(59, 130, 246, 0.06) 0%, transparent 50%),
        radial-gradient(ellipse at 85% 90%, rgba(16, 185, 129, 0.04) 0%, transparent 50%),
        var(--bg-deep);
}
```

---

## Site Banner & Navigation

```css
.site-banner {
    background-image: url('/images/mtnsky.jpg');
    background-size: cover;
    background-position: center bottom;
}

.site-banner-overlay {
    background: rgba(0, 0, 0, 0.6);
    padding-bottom: 1rem;
}

.site-nav {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 2rem;
    max-width: 1700px;
    margin: 0 auto;
}
```

---

## Theming Guidelines

### Adding New Colors
1. Define the variable in `:root` in `shared-theme.css`
2. Use semantic naming (e.g., `--accent-teal` not `--color-00bcd4`)
3. Document the variable in this reference

### Overriding Variables
Page-specific overrides can be done in `<style>` blocks:

```css
/* Override for dashboard green accent */
:root {
    --accent-primary: var(--success);
}
```

### Dark/Light Mode (Future)
Variables are structured to support future light mode:

```css
@media (prefers-color-scheme: light) {
    :root {
        --bg-deep: #ffffff;
        --bg-card: #f8fafc;
        --text-primary: #1e293b;
        /* etc. */
    }
}
```

---

*Documentation generated: 2026-01-18*
