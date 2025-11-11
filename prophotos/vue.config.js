const { defineConfig } = require('@vue/cli-service');

module.exports = defineConfig({
  transpileDependencies: true,
  
  
  // Configuration du serveur de développement
  devServer: {
    host: '0.0.0.0', // Autorise les connexions externes
    port: 8082, // Définit le port local pour le serveur
    https: false, // Mettre à true si vous voulez utiliser HTTPS localement
    allowedHosts: [
      '.ngrok-free.app', // Autorise les hôtes Ngrok
      'localhost', // Autorise localhost
    ],
    
  },
});
