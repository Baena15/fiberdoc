import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // En desarrollo el SPA (puerto 5173) llama al backend Django (8000)
      // como same-origin gracias al proxy: las cookies de sesión y CSRF
      // funcionan sin configurar CORS.
      "/api": "http://localhost:8000",
      "/admin": "http://localhost:8000",
    },
  },
});
