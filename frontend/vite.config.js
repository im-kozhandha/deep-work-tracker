import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Port 5173 is in the backend's default CORS allow-list; strictPort avoids silently
// moving to a port the backend would reject.
export default defineConfig({
  plugins: [react()],
  server: { port: 5173, strictPort: true },
});