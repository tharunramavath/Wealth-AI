/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // 915 Terminal Base Colors
        terminal: {
          bg: '#0a0a0c',
          surface: '#141519',
          card: '#1a1c23',
          border: '#2a2d38',
          hover: '#252830',
        },
        // Functional Colors
        bullish: '#10b981',    // Emerald Green - Buy/Profit
        bearish: '#dc2626',     // Crimson Red - Sell/Loss
        // Accents
        accent: {
          cyan: '#06b6d4',
          purple: '#8b5cf6',
          gold: '#f59e0b',     // Amber/Gold for warnings
        },
        // Text
        text: {
          primary: '#f8fafc',
          secondary: '#94a3b8',
          muted: '#64748b',
        },
        // Legacy support
        profit: '#10b981',
        loss: '#dc2626',
        brand: {
          500: '#10b981',
        },
        surface: {
          0: '#0a0a0c',
          50: '#0a0a0c',
          100: '#141519',
          200: '#1a1c23',
          300: '#2a2d38',
          400: '#3a3f4d',
          500: '#64748b',
          600: '#94a3b8',
          700: '#cbd5e1',
          800: '#e2e8f0',
          900: '#f8fafc',
        }
      },
      fontFamily: {
        mono: ['Roboto Mono', 'IBM Plex Mono', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      }
    },
  },
  plugins: [],
}
