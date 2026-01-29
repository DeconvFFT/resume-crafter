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
        // Workflow node colors
        "node-trigger": "hsl(var(--node-trigger))",
        "node-action": "hsl(var(--node-action))",
        "node-condition": "hsl(var(--node-condition))",
        "node-output": "hsl(var(--node-output))",
        // Midnight Teal specific colors
        teal: {
          50: "#f0fdfa",
          100: "#ccfbf1",
          200: "#99f6e4",
          300: "#5eead4",
          400: "#2dd4bf",
          500: "#14b8a6",
          600: "#0d9488",
          700: "#0f766e",
          800: "#115e59",
          900: "#134e4a",
          950: "#042f2e",
        },
        cyan: {
          50: "#ecfeff",
          100: "#cffafe",
          200: "#a5f3fc",
          300: "#67e8f9",
          400: "#22d3ee",
          500: "#06b6d4",
          600: "#0891b2",
          700: "#0e7490",
          800: "#155e75",
          900: "#164e63",
          950: "#083344",
        },
        emerald: {
          50: "#ecfdf5",
          100: "#d1fae5",
          200: "#a7f3d0",
          300: "#6ee7b7",
          400: "#34d399",
          500: "#10b981",
          600: "#059669",
          700: "#047857",
          800: "#065f46",
          900: "#064e3b",
          950: "#022c22",
        },
      },
      borderRadius: {
        lg: "var(--radius-lg)",
        md: "var(--radius-md)",
        sm: "var(--radius-sm)",
        xl: "var(--radius-xl)",
      },
      fontFamily: {
        sans: ["var(--font-sans)", "DM Sans", "system-ui", "sans-serif"],
        display: ["var(--font-display)", "Plus Jakarta Sans", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "JetBrains Mono", "Menlo", "monospace"],
      },
      fontSize: {
        "2xs": ["0.625rem", { lineHeight: "0.875rem" }],   // 10px
        xs: ["0.75rem", { lineHeight: "1rem" }],           // 12px
        sm: ["0.875rem", { lineHeight: "1.25rem" }],       // 14px
        base: ["1rem", { lineHeight: "1.5rem" }],          // 16px
        lg: ["1.125rem", { lineHeight: "1.75rem" }],       // 18px
        xl: ["1.25rem", { lineHeight: "1.75rem" }],        // 20px
        "2xl": ["1.5rem", { lineHeight: "2rem" }],         // 24px
        "3xl": ["1.875rem", { lineHeight: "2.25rem" }],    // 30px
        "4xl": ["2.25rem", { lineHeight: "2.5rem" }],      // 36px
        "5xl": ["3rem", { lineHeight: "1.1" }],            // 48px
        "6xl": ["3.75rem", { lineHeight: "1" }],           // 60px
        "7xl": ["4.5rem", { lineHeight: "1" }],            // 72px
      },
      letterSpacing: {
        tightest: "-0.05em",
        tighter: "-0.025em",
        tight: "-0.015em",
        normal: "0",
        wide: "0.025em",
        wider: "0.05em",
        widest: "0.1em",
      },
      spacing: {
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
      boxShadow: {
        sm: "0 1px 2px 0 rgb(0 0 0 / 0.05)",
        DEFAULT: "0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)",
        md: "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)",
        lg: "0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)",
        xl: "0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)",
        "2xl": "0 25px 50px -12px rgb(0 0 0 / 0.25)",
        card: "0 1px 3px 0 rgb(0 0 0 / 0.08), 0 1px 2px -1px rgb(0 0 0 / 0.08)",
        elevated: "0 4px 12px 0 rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.08)",
        // Premium shadows with teal glow
        "glow-sm": "0 0 10px rgba(20, 184, 166, 0.2)",
        "glow": "0 0 20px rgba(20, 184, 166, 0.3)",
        "glow-lg": "0 0 30px rgba(20, 184, 166, 0.4)",
        "glow-xl": "0 0 40px rgba(20, 184, 166, 0.5)",
        // Cyan glow for accent states
        "glow-cyan-sm": "0 0 10px rgba(6, 182, 212, 0.2)",
        "glow-cyan": "0 0 20px rgba(6, 182, 212, 0.3)",
        "glow-cyan-lg": "0 0 30px rgba(6, 182, 212, 0.4)",
        // Emerald glow for success states
        "glow-emerald-sm": "0 0 10px rgba(16, 185, 129, 0.2)",
        "glow-emerald": "0 0 20px rgba(16, 185, 129, 0.3)",
        "glow-emerald-lg": "0 0 30px rgba(16, 185, 129, 0.4)",
        // Glass shadows
        "glass": "0 8px 32px rgba(0, 0, 0, 0.12), 0 0 0 1px rgba(255, 255, 255, 0.05) inset",
        "glass-dark": "0 8px 32px rgba(0, 0, 0, 0.4), 0 0 0 1px rgba(255, 255, 255, 0.03) inset",
      },
      backdropBlur: {
        xs: "2px",
        sm: "4px",
        DEFAULT: "8px",
        md: "12px",
        lg: "16px",
        xl: "24px",
        "2xl": "40px",
        "3xl": "64px",
      },
      animation: {
        "fade-in": "fadeIn 0.2s ease-out",
        "fade-up": "fadeUp 0.3s ease-out forwards",
        "scale-in": "scaleIn 0.2s ease-out",
        "slide-in-right": "slideInRight 0.3s ease-out",
        "slide-in-left": "slideInLeft 0.3s ease-out",
        "pulse-subtle": "pulseSubtle 2s ease-in-out infinite",
        shimmer: "shimmer 1.5s infinite",
        // Premium animations
        "glow-pulse": "glowPulse 2s ease-in-out infinite",
        "float": "float 3s ease-in-out infinite",
        "gradient-shift": "gradientShift 15s ease infinite",
        // Workflow animations
        "flow-pulse": "flowPulse 1.5s ease-in-out infinite",
        "node-appear": "nodeAppear 0.4s ease-out",
        // Collapsible animations
        "collapsible-down": "collapsibleDown 0.2s ease-out",
        "collapsible-up": "collapsibleUp 0.2s ease-out",
        // Entrance animations
        "slide-up-fade": "slideUpFade 0.4s ease-out",
        "slide-down-fade": "slideDownFade 0.4s ease-out",
        "scale-up-fade": "scaleUpFade 0.3s ease-out",
      },
      keyframes: {
        fadeIn: {
          from: { opacity: "0" },
          to: { opacity: "1" },
        },
        fadeUp: {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        scaleIn: {
          from: { opacity: "0", transform: "scale(0.95)" },
          to: { opacity: "1", transform: "scale(1)" },
        },
        slideInRight: {
          from: { opacity: "0", transform: "translateX(10px)" },
          to: { opacity: "1", transform: "translateX(0)" },
        },
        slideInLeft: {
          from: { opacity: "0", transform: "translateX(-10px)" },
          to: { opacity: "1", transform: "translateX(0)" },
        },
        pulseSubtle: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.7" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        glowPulse: {
          "0%, 100%": { boxShadow: "0 0 20px rgba(20, 184, 166, 0.3)" },
          "50%": { boxShadow: "0 0 40px rgba(20, 184, 166, 0.5)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-10px)" },
        },
        gradientShift: {
          "0%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
          "100%": { backgroundPosition: "0% 50%" },
        },
        flowPulse: {
          "0%, 100%": { strokeDashoffset: "0" },
          "50%": { strokeDashoffset: "10" },
        },
        nodeAppear: {
          from: { opacity: "0", transform: "scale(0.8)" },
          to: { opacity: "1", transform: "scale(1)" },
        },
        collapsibleDown: {
          from: { height: "0" },
          to: { height: "var(--radix-collapsible-content-height)" },
        },
        collapsibleUp: {
          from: { height: "var(--radix-collapsible-content-height)" },
          to: { height: "0" },
        },
        slideUpFade: {
          from: { opacity: "0", transform: "translateY(20px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        slideDownFade: {
          from: { opacity: "0", transform: "translateY(-20px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        scaleUpFade: {
          from: { opacity: "0", transform: "scale(0.9)" },
          to: { opacity: "1", transform: "scale(1)" },
        },
      },
      maxWidth: {
        prose: "65ch",
        content: "800px",
        page: "1200px",
        screen: "1440px",
      },
      backgroundImage: {
        // Premium gradients
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "gradient-conic": "conic-gradient(from 180deg at 50% 50%, var(--tw-gradient-stops))",
        "gradient-primary": "linear-gradient(135deg, #14b8a6 0%, #06b6d4 100%)",
        "gradient-primary-subtle": "linear-gradient(135deg, rgba(20, 184, 166, 0.15) 0%, rgba(6, 182, 212, 0.1) 100%)",
        "gradient-success": "linear-gradient(135deg, #14b8a6 0%, #10b981 100%)",
        "gradient-accent": "linear-gradient(135deg, #14b8a6 0%, #0ea5e9 100%)",
        // Mesh gradients
        "mesh-teal": `
          radial-gradient(at 40% 20%, rgba(20, 184, 166, 0.15) 0px, transparent 50%),
          radial-gradient(at 80% 0%, rgba(6, 182, 212, 0.1) 0px, transparent 50%),
          radial-gradient(at 0% 50%, rgba(16, 185, 129, 0.08) 0px, transparent 50%)
        `,
      },
    },
  },
  plugins: [],
};

export default config;
