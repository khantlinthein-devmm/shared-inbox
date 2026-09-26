import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#f1eefe",
          100: "#e6e1fd",
          200: "#cfc5fb",
          300: "#ae9df8",
          400: "#8e74f4",
          500: "#7360f2",
          600: "#5f4ae0",
          700: "#503cc4",
          800: "#44349c",
          900: "#3a2f7a",
          950: "#221c4a",
        },
      },
      fontFamily: {
        sans: ["var(--font-inter)", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      boxShadow: {
        soft: "0 1px 2px rgb(16 16 40 / 0.05), 0 8px 24px -12px rgb(115 96 242 / 0.25)",
        glow: "0 0 0 4px rgb(115 96 242 / 0.15)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.25s ease-out both",
      },
    },
  },
  plugins: [],
};

export default config;