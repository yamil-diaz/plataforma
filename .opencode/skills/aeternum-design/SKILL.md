---
name: aeternum-design
description: Design system AeternumLibrary - tokens, tipografia, espaciado, motion y reglas anti-slop. Usar al diseñar o polir UI de la plataforma (home, dashboard, checkout, navbar, footer).
metadata:
  origin: Aeternum + design-taste (emil kowalski / impeccable / taste)
---

# Aeternum Design System

Marketplace de lectura premium. Dark mode locked. Rojo carmesí + oro. No es Temu ni SaaS genérico.

## Tokens de color

| Token | Valor | Uso |
|-------|-------|-----|
| `--bg` | `#0A0A0A` | Fondo base (off-black, nunca #000) |
| `--bg-elevated` | `#121212` | Cards, dropdowns, modales |
| `--bg-subtle` | `#181818` | Hover fills, skeletons |
| `--border` | `rgba(255,255,255,0.08)` | Hairlines |
| `--border-strong` | `rgba(255,255,255,0.14)` | Controles activos |
| `--text` | `#F5F5F5` | Texto primario (off-white) |
| `--text-muted` | `#A0A0A0` | Secundario (contraste ≥4.5) |
| `--text-faint` | `#707070` | Meta, captions |
| `--brand` | `#D92B2B` | Acento único: CTA, logo, foco |
| `--brand-soft` | `rgba(217,43,43,0.12)` | Tintes suaves |
| `--gold` | `#D4AF37` | Rayos, precios, badges premium |
| `--success` | `#34D399` | Confirmaciones |
| `--danger` | `#F87171` | Errores |

Un solo acento de marca (rojo). Oro solo para economía/precio. No inventar gradientes morado-azul.

## Tipografía

- Display/UI: **Outfit** (ya cargada)
- Lectura larga / citas: **Lora** (serif solo en contenido editorial, no en dashboard)
- Escala (ratio ~1.25):
  - Display: `clamp(2rem, 4vw, 3.5rem)` max ~3.5rem en app; hero marketplace puede llegar a 4rem
  - H1 app: 2rem / weight 700 / tracking -0.02em
  - H2: 1.5rem
  - H3: 1.125rem
  - Body: 0.9375rem-1rem / line-height 1.55 / max 65ch
  - Caption: 0.75rem
- `text-wrap: balance` en h1-h3
- Sin Inter. Sin serif por defecto en UI de producto.
- No all-caps en párrafos. Labels cortos en uppercase solo si son UI chrome.

## Espaciado

Base 4px. Escala: 4, 8, 12, 16, 24, 32, 48, 64.
- Cards: padding 16-24px
- Secciones home: 48-80px vertical
- Grid catálogo: `repeat(auto-fill, minmax(160px, 1fr))` mobile, hasta 220px desktop
- Gap cards: 16-24px
- Radius: controls 8px, cards 12px, modales 16px, pills full. Un solo sistema.

## Motion

Tokens CSS:
```
--ease-out: cubic-bezier(0.23, 1, 0.32, 1);
--ease-in-out: cubic-bezier(0.77, 0, 0.175, 1);
--dur-fast: 150ms;
--dur: 200ms;
--dur-slow: 280ms;
```

Reglas:
- Enter/exit: ease-out. Nunca ease-in en UI.
- Duración UI < 300ms.
- Solo `transform` y `opacity` (y clip-path medido).
- Botones: `:active { scale(0.97) }`.
- Dropdowns/modales: fade + `scale(0.97)` o translateY(4px), origin-aware en dropdowns.
- Nunca `scale(0)`.
- `prefers-reduced-motion`: sin movimiento, mantener opacity.
- No animar acciones de teclado repetitivas.
- Prohibido `animate-pulse` decorativo permanente en badges (excepto notificación no leída real).

## Componentes clave

**Navbar:** sticky, blur sutil, height 64px, links muted → white on hover, no gradient flashy.
**Botón primario:** bg brand, text white, radius 8px, shadow solo si elevación real (no border+shadow ghost).
**Cards libro:** aspect 3/4 cover, título 1 línea, precio oro, hover lift suave 150ms.
**Dropdown perfil:** elevated bg, borde hairline, items 40px, role badge gold outline.
**Footer:** 4 columnas, sin dots decorativos, copyright simple.

## Anti-slop (aplicar siempre)

Prohibido:
- Gradient text (`background-clip: text`)
- Glassmorphism decorativo
- Cards anidadas
- Border-left de acento grueso
- Grid de 3 cards idénticas genéricas
- Eyebrow uppercase en cada sección
- Em-dash (U+2014) en UI copy
- Pure #000 / #fff
- Glow neón
- Bounce/elastic en UI
- Version labels en hero
- Scroll cues ("scroll to explore")
- Números fake 99.99%

Copy: verbos concretos ("Agregar al carrito", no "Eleva tu experiencia").
Roles UI: Comprador, Vendedor, Admin (DB: user, autor, admin).
Moneda: PEN / S/ en UI de Perú.

## Flujo al diseñar

1. Leer el brief (página, registro: Operate para dashboard/app, Persuade para home/marketing)
2. Declarar Design Read + dials (variance/motion/density)
3. Construir con tokens de este archivo
4. Criticar: contraste, espaciado, motion purpose, anti-slop
5. Pre-flight visual antes de deploy

## Referencias

- skill `design-taste` (en este repo)
- skill `impeccable`
- skill `emil-design`
- ECC `design-system`
