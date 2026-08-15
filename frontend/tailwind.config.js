/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        fondo: "#faf8f5",
        tinta: "#3d3833",
        acento: {
          DEFAULT: "#c26d4a",
          oscuro: "#a85a3b",
        },
        ok: "#7da87d",
        warn: "#d9a441",
        fuera: "#c25b4e",
        arena: "#f3efe9",
        linea: "#e2dccf",
      },
      fontFamily: {
        sans: [
          '"Segoe UI"',
          "-apple-system",
          '"Helvetica Neue"',
          "Arial",
          "sans-serif",
        ],
      },
    },
  },
  plugins: [],
};
