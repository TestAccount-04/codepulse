/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        codepulse: {
          bg: "#0d1117",
          card: "#161b22",
          border: "#30363d",
          text: "#c9d1d9",
          muted: "#8b949e",
          accent: "#58a6ff",
        },
        status: {
          added: "#3fb950",
          modified: "#d29922",
          deleted: "#f85149",
          renamed: "#58a6ff",
          impacted: "#bc8cff",
          unchanged: "#8b949e",
        }
      }
    },
  },
  plugins: [],
}
