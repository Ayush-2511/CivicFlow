/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        civic: {
          navy: '#0F172A',
          blue: '#1E293B',
          slate: '#334155',
          amber: '#F59E0B',
          emerald: '#10B981',
          rose: '#EF4444',
          bg: '#F8FAFC',
        }
      }
    },
  },
  plugins: [],
}

