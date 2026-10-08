# AeternumLibrary Brand Guidelines

> Nota: no se encontró `crabacadabra-brand-guidelines.zip` / `brand-guidelines.pdf` en el workspace ni en GitHub público. Estas guidelines son el brandbook vivo de Aeternum basado en la identidad actual de la plataforma.

## Brand

- **Nombre:** AETERNUM (wordmark) / AeternumLibrary (legal)
- **Tagline:** La primera plataforma donde la lectura tiene recompensas
- **Categoria:** Marketplace de lectura + cursos + IA (no fashion marketplace)
- **Personalidad:** Premium, formal, confiable, con recompensas (Rayos)

## Color

| Rol | Hex | Notas |
|-----|-----|-------|
| Ink / bg | `#0A0A0A` | Off-black. Nunca `#000` |
| Surface | `#121212` | Cards y paneles |
| Surface subtle | `#181818` | Hover / skeleton |
| Text | `#F5F5F5` | Off-white |
| Text muted | `#A0A0A0` | Secundario con contraste AA |
| Brand | `#D92B2B` | Acento único. CTA y logo |
| Gold | `#D4AF37` | Rayos, precios, premium |
| Border | `rgba(255,255,255,0.08)` | Hairline |

**Regla:** un solo acento de marca. Oro solo para economía/precio. Prohibido gradiente morado-azul AI.

## Typography

| Uso | Fuente | Pesos |
|-----|--------|-------|
| UI / Display | Outfit | 400-700 |
| Lectura editorial | Lora | 400-700 (solo contenido, no dashboard) |

Escala UI: 12 / 14 / 16 / 20 / 24 / 32 / 40 px con ratio ~1.25.
Body max-width 65ch. Headings tight (-0.02em).

## Spacing & shape

- Base 4px: 4, 8, 12, 16, 24, 32, 48, 64
- Radius: controls 8px, cards 12px, modales 16px
- Un solo sistema de radius por superficie

## Motion

- Ease-out fuerte: `cubic-bezier(0.23, 1, 0.32, 1)`
- Duración UI: 150-280ms, nunca >300ms
- Solo transform/opacity
- Botón active: scale 0.97
- Respetar `prefers-reduced-motion`

## Roles UI

| UI | DB |
|----|-----|
| Comprador | `user` |
| Vendedor | `autor` |
| Admin | `admin` |

## Moneda / Idioma

- Default UI: Español, PEN (S/)
- Checkout: USD, PEN, EUR, MXN, CLP, COP, ARS, BRL

## Voice

- Verbos concretos: "Agregar al carrito", "Publicar libro", "Solicitar retiro"
- Prohibido: "eleva", "seamless", "next-gen", "revoluciona"
- Sin em-dash en UI copy
- Roles claros, sin confusión lector/autor en la interfaz

## Assets

- Logo: rayo en cuadrado gradiente crimson → deep red
- Iconos: lucide-react (consistente)
- Covers de libros: reales, no placeholders rotos

## Aplicar al UI

Usar skill `aeternum-design` + `design-taste` + `impeccable` + `emil-design` al tocar frontend.
