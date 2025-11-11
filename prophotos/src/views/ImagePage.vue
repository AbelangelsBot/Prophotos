<template>
  <div class="container mt-5">
    <NavigationBar :token="token" />
    <div class="card shadow-lg">
      <router-link :to="{ path: '/image', query: { path: imageData.Path } }">
        <img 
          :src="imageData.Img" 
          class="card-img-top" 
          alt="Image Preview" 
          style="cursor: pointer;" 
          @contextmenu.prevent 
          @dragstart.prevent
        />
      </router-link>
      <div class="card-body">
        <h5 class="card-title">{{ imageData.Name }}</h5>
        <p class="card-text"><strong>Path:</strong> {{ imageData.Path }}</p>
        <p class="card-text"><strong>Size:</strong> {{ imageData.Size }}</p>
        <p class="card-text"><strong>Type:</strong> {{ imageData.Type }}</p>

        <button v-if="token" @click="downloadImage" class="btn btn-primary">
          Télécharger l'image
        </button>
        <p v-else class="text-danger">Vous devez être connecté pour télécharger cette image.</p>
      </div>
    </div>
    <FooterSection />
  </div>
</template>

<script>
import NavigationBar from "@/components/NavBar.vue";
import FooterSection from "@/components/FootSection.vue";
import axios from "axios";

import { FILES_API_URL } from "@/constants";

export default {
  name: "ImagePage",
  
  data() {
    return {
      token: localStorage.getItem("token") || null, 
      imageData: {},
    };
  },
  methods: {
    async fetchImageData() {
      try {
        const response = await axios.get(`${FILES_API_URL}/files/image/`, {
          params: { path: this.$route.query.path },
          headers: { Authorization: `Bearer ${this.token}` },
        });
        this.imageData = response.data;
      } catch (error) {
        console.error("Erreur lors de la récupération de l'image :", error);
      }
    },
    async downloadImage() {
      try {
        const response = await axios.get(`${FILES_API_URL}/files/image/download/`, {
          params: { path: this.imageData.Path },
          headers: { Authorization: `Bearer ${this.token}` },
          responseType: "blob",
        });

        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement("a");
        link.href = url;
        link.setAttribute("download", this.imageData.Name);
        document.body.appendChild(link);
        link.click();
      } catch (error) {
        console.error("Erreur lors du téléchargement de l'image :", error);
      }
    },
  },
  mounted() {
    this.fetchImageData();
  },
  components: {
    NavigationBar,
    FooterSection,
  },
};
</script>

<style scoped>
.container {
  max-width: 800px;
}
.card-img-top {
  max-height: 400px;
  object-fit: contain;
  pointer-events: none; /* Empêche le drag & drop */
  user-select: none; /* Désactive la sélection */
}
</style>
