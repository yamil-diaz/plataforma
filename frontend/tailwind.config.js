/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        ae: {
          bg: '#0A0A0A',
          elevated: '#121212',
          subtle: '#181818',
          border: 'rgba(255,255,255,0.08)',
          text: '#F5F5F5',
          muted: '#A0A0A0',
          faint: '#707070',
          brand: '#D92B2B',
          gold: '#D4AF37',
        },
      },
      fontFamily: {
        sans: ['Outfit', 'system-ui', 'sans-serif'],
        serif: ['Lora', 'Georgia', 'serif'],
      },
      borderRadius: {
        control: '8px',
        card: '12px',
        modal: '16px',
      },
      transitionTimingFunction: {
        'ae-out': 'cubic-bezier(0.23, 1, 0.32, 1)',
        'ae-in-out': 'cubic-bezier(0.77, 0, 0.175, 1)',
      },
      transitionDuration: {
        fast: '150ms',
        DEFAULT: '200ms',
        slow: '280ms',
      },
      maxWidth: {
        prose: '65ch',
      },
      zIndex: {
        dropdown: '50',
        sticky: '40',
        modal: '60',
        toast: '70',
      },
    },
  },
  plugins: [],
}
