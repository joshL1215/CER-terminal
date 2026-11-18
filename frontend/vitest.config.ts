import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: { environment: "jsdom", restoreMocks: true, unstubEnvs: true, unstubGlobals: true, setupFiles: ["src/test-setup.ts"] },
});
