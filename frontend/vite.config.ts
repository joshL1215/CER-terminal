import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  // Set BASE_PATH when deploying under a sub-path (e.g. GitHub Pages: "/CER-terminal/").
  base: process.env.BASE_PATH ?? "/",
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          react: ["react", "react-dom"],
          recharts: ["recharts"],
          supabase: ["@supabase/supabase-js"],
        },
      },
    },
  },
});
