import type { Config } from 'tailwindcss'

export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Geist', 'system-ui', 'sans-serif'],
      },
      colors: {
        brand: {
          50:  '#e6f9ff',
          100: '#b3eeff',
          400: '#33c9f0',
          500: '#00b4e5',
          600: '#0099c7',
          700: '#007da3',
          900: '#003a4d',
        },
        surface: {
          950: '#0d1117',
          900: '#161b27',
          800: '#1e2435',
          700: '#252d40',
          600: '#2e3854',
          500: '#3d4a66',
          400: '#5a6785',
          300: '#8a97b0',
          200: '#c2cad9',
          100: '#e8ebf2',
        },
      },
    },
  },
  plugins: [],
} satisfies Config
