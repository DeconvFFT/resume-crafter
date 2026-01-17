import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        // Semantic colors
        success: {
          DEFAULT: "hsl(var(--success))",
          foreground: "hsl(var(--success-foreground))",
        },
        warning: {
          DEFAULT: "hsl(var(--warning))",
          foreground: "hsl(var(--warning-foreground))",
        },
        info: {
          DEFAULT: "hsl(var(--info))",
          foreground: "hsl(var(--info-foreground))",
        },
        // Editorial text colors
        ink: "hsl(var(--text-primary))",
        charcoal: "hsl(var(--text-secondary))",
        stone: "hsl(var(--text-muted))",
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius))",
        sm: "calc(var(--radius))",
        // Editorial style - no radius
        none: "0px",
      },
      fontFamily: {
        display: ["Playfair Display", "Georgia", "serif"],
        body: ["Source Serif 4", "Georgia", "serif"],
        mono: ["IBM Plex Mono", "Menlo", "monospace"],
      },
      fontSize: {
        // Editorial type scale
        "2xs": ["0.625rem", { lineHeight: "0.875rem" }],  // 10px
        xs: ["0.75rem", { lineHeight: "1rem" }],          // 12px
        sm: ["0.875rem", { lineHeight: "1.25rem" }],      // 14px
        base: ["1rem", { lineHeight: "1.625rem" }],       // 16px
        lg: ["1.125rem", { lineHeight: "1.75rem" }],      // 18px
        xl: ["1.25rem", { lineHeight: "1.75rem" }],       // 20px
        "2xl": ["1.5rem", { lineHeight: "2rem" }],        // 24px
        "3xl": ["1.875rem", { lineHeight: "2.25rem" }],   // 30px
        "4xl": ["2.25rem", { lineHeight: "2.5rem" }],     // 36px
        "5xl": ["3rem", { lineHeight: "1.1" }],           // 48px
        "6xl": ["3.75rem", { lineHeight: "1" }],          // 60px
      },
      spacing: {
        // 8px base rhythm
        "0.5": "0.125rem",   // 2px
        "1": "0.25rem",      // 4px
        "1.5": "0.375rem",   // 6px
        "2": "0.5rem",       // 8px
        "2.5": "0.625rem",   // 10px
        "3": "0.75rem",      // 12px
        "3.5": "0.875rem",   // 14px
        "4": "1rem",         // 16px
        "5": "1.25rem",      // 20px
        "6": "1.5rem",       // 24px
        "7": "1.75rem",      // 28px
        "8": "2rem",         // 32px
        "9": "2.25rem",      // 36px
        "10": "2.5rem",      // 40px
        "11": "2.75rem",     // 44px
        "12": "3rem",        // 48px
        "14": "3.5rem",      // 56px
        "16": "4rem",        // 64px
        "20": "5rem",        // 80px
        "24": "6rem",        // 96px
        "28": "7rem",        // 112px
        "32": "8rem",        // 128px
      },
      letterSpacing: {
        tighter: "-0.02em",
        tight: "-0.01em",
        normal: "0",
        wide: "0.02em",
        wider: "0.05em",
        widest: "0.1em",
        editorial: "0.2em",
      },
      lineHeight: {
        tight: "1.2",
        snug: "1.4",
        normal: "1.5",
        relaxed: "1.625",
        loose: "2",
      },
      boxShadow: {
        card: "0 1px 3px hsl(var(--text-primary) / 0.04), 0 4px 12px hsl(var(--text-primary) / 0.03)",
        elevated: "0 2px 8px hsl(var(--text-primary) / 0.06), 0 12px 32px hsl(var(--text-primary) / 0.08)",
        floating: "0 4px 16px hsl(var(--text-primary) / 0.08), 0 24px 48px hsl(var(--text-primary) / 0.12)",
      },
      animation: {
        "fade-slide-in": "fadeSlideIn 0.4s ease-out forwards",
        "draw-line": "drawLine 0.6s ease-out forwards",
      },
      keyframes: {
        fadeSlideIn: {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        drawLine: {
          from: { width: "0" },
          to: { width: "40px" },
        },
      },
      maxWidth: {
        prose: "65ch",
        content: "800px",
        page: "960px",
      },
    },
  },
  plugins: [],
};

export default config;
