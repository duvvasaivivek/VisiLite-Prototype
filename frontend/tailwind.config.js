/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#07111f",
        panel: "#102033",
        accent: "#7ee0c8",
        warn: "#f3c16b",
        danger: "#f07178",
      },
    },
  },
  plugins: [],
};
