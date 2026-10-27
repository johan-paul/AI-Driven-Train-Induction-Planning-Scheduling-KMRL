module.exports = {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    fontFamily: {
      sans: ["Open Sans", "ui-sans-serif", "system-ui", "sans-serif", "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji"],
      title: ["Lato", "ui-sans-serif", "system-ui", "sans-serif"],
      body: ["Open Sans", "ui-sans-serif", "system-ui", "sans-serif"]
    },
    extend: {
      colors: {
        neutral: {
          50: "#f7f7f7",
          100: "#eeeeee",
          200: "#e0e0e0",
          300: "#cacaca",
          400: "#b1b1b1",
          500: "#999999",
          600: "#7f7f7f",
          700: "#676767",
          800: "#545454",
          900: "#464646",
          950: "#282828"
        },
        primary: {
          50: "#f3f1ff",
          100: "#e9e5ff",
          200: "#d5cfff",
          300: "#b7a9ff",
          400: "#9478ff",
          500: "#7341ff",
          600: "#631bff",
          700: "#611bf8",
          800: "#4607d0",
          900: "#3c08aa",
          950: "#220174",
          DEFAULT: "#611bf8"
        }
      }
    }
  },
  plugins: []
};