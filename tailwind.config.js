// tailwind.config.js
/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./documentation/templates/**/*.html", // Escanear templates do app documentation
    // Adicione outros caminhos se tiver templates em outros apps que usarão Tailwind
  ],
  theme: {
    extend: {
      // Defina cores Cyberpunk personalizadas aqui se desejar
      colors: {
        'neon-blue': '#00F0FF',
        'neon-pink': '#FF40A0',
        'dark-synth': '#1a1a2e',
        'deep-space': '#0f0e17',
        'glitch-red': '#FF3131',
      },
      // Defina fontes Cyberpunk personalizadas aqui
      fontFamily: {
          'cyber': ['"Share Tech Mono"', 'monospace'], // Exemplo de fonte, instale ou use CDN
          'sans': ['"Roboto Mono"', 'sans-serif'], // Outra opção
      },
      // Outras extensões de tema
    },
  },
  plugins: [
    // Adicione plugins Tailwind aqui se necessário
  ],
}