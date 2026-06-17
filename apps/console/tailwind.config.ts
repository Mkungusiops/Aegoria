import type { Config } from "tailwindcss";

/**
 * Aegoria design tokens.
 *
 * Neutral surfaces + text are CSS variables (RGB triplets) so a single `.light`
 * class on <html> flips the entire app between the dark "Veil" canvas and a
 * premium light theme — without touching a single component. Accent hues
 * (signature "Auralis" #16E0C4, Pulse, Verdant, Ion, Solar, Crimson) are fixed,
 * legible in both themes. `ink` is the dark text that sits on bright accents.
 */
const v = (name: string) => `rgb(var(${name}) / <alpha-value>)`;

const config: Config = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        veil: {
          DEFAULT: v("--veil"),
          1: v("--veil-1"),
          2: v("--veil-2"),
          3: v("--veil-3"),
        },
        hairline: v("--hairline"),
        lumen: v("--lumen"),
        muted: v("--muted"),
        faint: v("--faint"),
        ink: "#052a22", // dark text for placement on bright accents (both themes)
        auralis: {
          DEFAULT: "#16E0C4",
          deep: "#0BA98F",
          soft: "rgba(22,224,196,0.12)",
        },
        pulse: "#7B61FF",
        verdant: "#57E08A",
        ion: "#3FA9FF",
        solar: "#FFB454",
        crimson: "#FF5C72",
      },
      fontFamily: {
        display: ["var(--font-display)", "Inter Tight", "system-ui", "sans-serif"],
        sans: ["var(--font-sans)", "Inter", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "JetBrains Mono", "ui-monospace", "monospace"],
      },
      borderRadius: { sm: "8px", md: "12px", lg: "18px", xl: "26px" },
      boxShadow: {
        glow: "0 0 0 1px rgba(22,224,196,0.20), 0 12px 40px -12px rgba(22,224,196,0.30)",
        panel: "0 24px 60px -24px rgba(2,6,18,0.55)",
        "panel-sm": "0 12px 30px -16px rgba(2,6,18,0.45)",
      },
      backgroundImage: {
        "auralis-gradient": "linear-gradient(135deg, #16E0C4 0%, #21D6C9 55%, #7B61FF 100%)",
        "veil-glow":
          "radial-gradient(1200px 600px at 18% -10%, rgb(var(--glow-a) / 0.10), transparent 60%), radial-gradient(1000px 520px at 100% 0%, rgb(var(--glow-b) / 0.10), transparent 55%)",
        "grid-faint":
          "linear-gradient(to right, rgb(var(--grid) / 0.045) 1px, transparent 1px), linear-gradient(to bottom, rgb(var(--grid) / 0.045) 1px, transparent 1px)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(8px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "pulse-ring": {
          "0%": { transform: "scale(0.8)", opacity: "0.7" },
          "100%": { transform: "scale(2.2)", opacity: "0" },
        },
        float: {
          "0%,100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-6px)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.5s cubic-bezier(0.16,1,0.3,1) both",
        shimmer: "shimmer 2.5s linear infinite",
        "pulse-ring": "pulse-ring 2.4s ease-out infinite",
        float: "float 6s ease-in-out infinite",
      },
    },
  },
  plugins: [],
};

export default config;
