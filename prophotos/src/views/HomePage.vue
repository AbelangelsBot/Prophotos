<template> 
  <div class="home">
    <NavigationBar :token="token" />
    <main class="container py-4">
      <h1 class="display-4 mb-4 text-center">ProPhotos</h1>
      
      <div>
        <div class="d-flex mb-4">
          <button v-if="currentPath !== '/'" @click="goRoot" class="btn btn-secondary me-2">
            Root
          </button>
          <button v-if="currentPath !== '/'" @click="goBack" class="btn btn-secondary">
            Back
          </button>
        </div>

        <div v-if="charging" class="text-center">
          <h2 class="display-6 mb-4">Charging . . .</h2>
        </div>

        <!-- Grille style explorateur -->
        <div class="row g-4">
          <div 
            v-for="(item, index) in directoryContent" 
            :key="index" 
            class="col-6 col-sm-4 col-md-3 col-lg-2"
          >
            <div class="card h-100 text-center p-2 shadow-sm">
              <!-- Si c’est une image -->
              <div v-if="item.Img" class="mb-2">
                <img 
                  :src="item.Img" 
                  alt="Preview" 
                  class="img-fluid rounded clickable-image"
                  style="height: 8rem; object-fit: cover; cursor: pointer;" 
                  @click="viewImage(item)" 
                />
              </div>

              <!-- Si c’est un dossier -->
              <div v-else-if="item.isDirectory" class="mb-2" style="font-size: 3rem;">
                📁
              </div>

              <!-- Nom -->
              <div class="fw-bold text-truncate" :title="item.Name">
                {{ item.Name }}
              </div>

              <!-- Boutons -->
              <div class="mt-2">
                <button 
                  v-if="item.isDirectory" 
                  @click="navigateToFolder(item.Path)" 
                  class="btn btn-outline-primary btn-sm"
                >
                  Open
                </button>
                <button 
                  v-else-if="item.Img && token" 
                  @click="downloadImage(item.Path, item.Name)" 
                  class="btn btn-primary btn-sm"
                >
                  Télécharger
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
    <FooterSection />
  </div>
</template>


<script>
import NavigationBar from "@/components/NavBar.vue";
import FooterSection from "@/components/FootSection.vue";
import axios from "axios";

import { FILES_API_URL } from "@/constants";
export default {
  name: "HomePage",
  data() {
    return {
      token: localStorage.getItem("token") || null, 
      directoryContent: [],
      currentPath: "/",
      pathHistory: [],
      charging: false,
    };
  },
  components: {
    NavigationBar,
    FooterSection,
  },
  methods: {
    async fetchDirectoryContent() {
      try {
        this.directoryContent = [];
        this.charging = true;
        const response = await axios.get(
  `${FILES_API_URL}/files/?path=${this.currentPath}`
);

        this.directoryContent = response.data;
      } catch (error) {
        console.error("Error fetching directory content:", error);
      } finally {
        this.charging = false;
      }
    },

    navigateToFolder(folderPath) {
      this.pathHistory.push(this.currentPath);
      this.currentPath = folderPath;
      this.fetchDirectoryContent();
    },
    goBack() {
      if (this.pathHistory.length > 0) {
        this.currentPath = this.pathHistory.pop();
        this.fetchDirectoryContent();
      }
    },
    goRoot() {
      this.currentPath = "/";
      this.fetchDirectoryContent();
    },
    viewImage(item) {
      this.$router.push({ path: '/image', query: { path: item.Path } });
    },
    async downloadImage(imagePath, imageName) {
      try {
        const response = await axios.get(`${FILES_API_URL}/files/image/download`, {
          params: { path: imagePath },
          headers: { Authorization: `Bearer ${this.token}` },
          responseType: "blob",
        });

        const url = window.URL.createObjectURL(new Blob([response.data]));
        const link = document.createElement("a");
        link.href = url;
        link.setAttribute("download", imageName);
        document.body.appendChild(link);
        link.click();
      } catch (error) {
        console.error("Erreur lors du téléchargement de l'image :", error);
      }
    },
  },
  mounted() {
    this.fetchDirectoryContent();
  },
};
</script>

<style scoped>
.home {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

main {
  flex: 1;
}

.clickable-image {
  cursor: pointer;
  transition: transform 0.2s;
}

.clickable-image:hover {
  transform: scale(1.05);
}
</style>
