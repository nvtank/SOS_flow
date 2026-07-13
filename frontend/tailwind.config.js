/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        critical: "#b91c1c",
        high: "#ea580c",
        medium: "#ca8a04",
        low: "#15803d",
        command: "#17202a"
      }
    }
  },
  plugins: []
};
