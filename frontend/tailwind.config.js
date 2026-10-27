/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/features/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        navy: {
          900: "#0B132B",
          850: "#0F1A36",
          800: "#1C2541",
          700: "#2B3A67",
        },
        aicte: {
          blue: "#1E3A8A",
          accent: "#2563EB",
          light: "#EFF6FF",
          gold: "#D97706",
          green: "#059669",
          red: "#DC2626",
          amber: "#D97706",
        }
      },
    },
  },
  plugins: [],
}
