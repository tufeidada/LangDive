/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      keyframes: {
        'fade-in': {
          '0%': { opacity: '0', transform: 'translateY(4px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'fade-in': 'fade-in 0.2s ease-out',
      },
      colors: {
        primary: '#0c0c18',
        card: '#13132a',
        elevated: '#1c1c38',
        border: '#262648',
        accent: '#facc15',
        'text-primary': '#e4e4ec',
        'text-secondary': '#6a6a8a',
        'level-cet4': '#60a5fa',
        'level-cet6': '#34d399',
        'level-ielts': '#fbbf24',
        'level-adv': '#f87171',
        'status-due': '#ef4444',
        'status-soon': '#fbbf24',
        'status-mastered': '#22c55e',
      },
    },
  },
  plugins: [],
}
