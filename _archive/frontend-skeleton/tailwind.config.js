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
        whatsapp: {
          teal: '#128C7E',
          'teal-dark': '#075E54',
          green: '#25D366',
          light: '#DCF8C6',
          bg: '#ECE5DD',
          'dark-bg': '#111B21',
          'dark-panel': '#202C33',
          'dark-msg': '#005C4B'
        }
      }
    },
  },
  plugins: [],
}
