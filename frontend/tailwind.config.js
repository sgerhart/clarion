/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        clarion: {
          blue: '#1e3a5f',
          teal: '#2dd4bf',
          purple: '#a855f7',
          orange: '#f97316',
          green: '#10b981',
        },
      },
    },
  },
  plugins: [],
}


