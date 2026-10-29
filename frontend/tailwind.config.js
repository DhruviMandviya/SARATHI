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
        sarathi: {
          primary: "#0A4D2E",
          hover: "#083D24",
          dark: "#073F2A",
          darker: "#052E1F",
          light: "#F0FDF4",
          surface: "#F0F8F3",
          border: "#D9E2E7",
          saffron: "#FF9933",
          green: "#138808",
        },
        navy: {
          900: "#073F2A",
          850: "#052E1F",
          800: "#0A4D2E",
          700: "#0D5C3A",
        },
        aicte: {
          blue: "#0A4D2E",
          accent: "#0D5C3A",
          light: "#F0FDF4",
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
