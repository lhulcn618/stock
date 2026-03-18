import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const isTauriBuild = Boolean(process.env.TAURI_ENV_PLATFORM);

export default defineConfig({
  base: isTauriBuild ? "./" : "/",
  plugins: [react()],
  server: {
    port: 1420,
    strictPort: true
  }
});
