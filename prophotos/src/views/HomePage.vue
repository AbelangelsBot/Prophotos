<template>
  <div class="home">
    <NavigationBar :token="token" @update-token="handleTokenUpdate" />
    <main class="container py-4">
      <h1 class="display-4 mb-4 text-center">ProPhotos</h1>
      
      <div>
        <div class="d-flex mb-4">
          <button v-if="canGoUp" @click="goRoot" class="btn btn-secondary me-2">
            Root
          </button>
          <button v-if="canGoUp" @click="goBack" class="btn btn-secondary">
            Back
          </button>
        </div>

        <div v-if="charging" class="text-center">
          <h2 class="display-6 mb-4">Charging . . .</h2>
        </div>

        <div v-if="token && isAdmin" class="card mb-4">
          <div class="card-body">
            <h5 class="card-title d-flex justify-content-between align-items-center">
              <span>Actions administrateur</span>
              <small class="text-muted">Chemin: {{ currentPath || "/" }}</small>
            </h5>

            <div class="row g-3 align-items-end">
              <div class="col-md-6">
                <label class="form-label">Ajouter des photos ici</label>
                <input
                  ref="fileInput"
                  type="file"
                  multiple
                  class="form-control"
                  @change="onFilesSelected"
                />
              </div>
              <div class="col-md-3">
                <button
                  type="button"
                  class="btn btn-primary w-100"
                  :disabled="!pendingFiles.length || uploading"
                  @click="uploadPhotos"
                >
                  {{ uploading ? "Envoi..." : "Ajouter les photos" }}
                </button>
              </div>
              <div class="col-md-3 text-muted small">
                <div v-if="pendingFiles.length">
                  {{ pendingFiles.length }} fichier(s) selectionnes
                </div>
                <div v-else>
                  Aucun fichier selectionne
                </div>
              </div>
            </div>

            <hr class="my-3" />

            <form class="row g-3 align-items-end" @submit.prevent="createFolder">
              <div class="col-md-6">
                <label class="form-label" for="folder-name">Nouveau dossier</label>
                <input
                  id="folder-name"
                  v-model="newFolderName"
                  type="text"
                  class="form-control"
                  placeholder="Nom du dossier"
                />
              </div>
              <div class="col-md-3">
                <button
                  type="submit"
                  class="btn btn-outline-primary w-100"
                  :disabled="!newFolderName || creatingFolder"
                >
                  {{ creatingFolder ? "Creation..." : "Creer le dossier" }}
                </button>
              </div>
            </form>
          </div>
        </div>

        <!-- Grille style explorateur -->
        <div class="row g-4">
          <div 
            v-for="(item, index) in directoryContent" 
            :key="index" 
            class="col-6 col-sm-4 col-md-3 col-lg-2"
          >
            <div class="card h-100 text-center p-2 shadow-sm">
              <div v-if="item.Img" class="mb-2">
                <img 
                  :src="item.Img" 
                  alt="Preview" 
                  class="img-fluid rounded clickable-image"
                  style="height: 8rem; object-fit: cover; cursor: pointer;" 
                  @click="viewImage(item)" 
                />
              </div>

              <div v-else-if="item.isDirectory" class="mb-2 folder-icon">
                DIR
              </div>

              <div class="fw-bold text-truncate" :title="item.Name">
                {{ item.Name }}
              </div>

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
                  Telecharger
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

import { FILES_API_URL, USERS_API_URL } from "@/constants";

export default {
  name: "HomePage",
  components: {
    NavigationBar,
    FooterSection,
  },
  data() {
    return {
      token: localStorage.getItem("token") || null,
      directoryContent: [],
      charging: false,
      isAdmin: false,
      pendingFiles: [],
      newFolderName: "",
      uploading: false,
      creatingFolder: false,
    };
  },
  computed: {
    currentPathParam() {
      return this.$route.params.pathMatch ? String(this.$route.params.pathMatch) : "";
    },
    currentPath() {
      return this.currentPathParam ? `/${this.currentPathParam}` : "/";
    },
    currentPathSegments() {
      return this.currentPathParam ? this.currentPathParam.split("/").filter(Boolean) : [];
    },
    canGoUp() {
      return this.currentPathSegments.length > 0;
    },
  },
  watch: {
    token(newToken) {
      if (newToken) {
        this.determineAdmin();
      } else {
        this.isAdmin = false;
      }
    },
    $route() {
      this.fetchDirectoryContent();
    },
  },
  methods: {
    async determineAdmin() {
      if (!this.token) {
        this.isAdmin = false;
        return;
      }

      try {
        const response = await axios.post(
          `${USERS_API_URL}/users/verify-token/`,
          {},
          { headers: { Authorization: `Bearer ${this.token}` } }
        );
        const user = response.data && response.data.user;
        this.isAdmin = !!(user && user.admin);
      } catch (error) {
        console.error("Error verifying admin rights:", error);
        this.isAdmin = false;
      }
    },
    async fetchDirectoryContent() {
      try {
        this.directoryContent = [];
        this.charging = true;
        const response = await axios.get(`${FILES_API_URL}/files/`, {
          params: { path: this.currentPathParam },
        });

        this.directoryContent = response.data;
      } catch (error) {
        console.error("Error fetching directory content:", error);
      } finally {
        this.charging = false;
      }
    },
    navigateToFolder(folderPath) {
      this.$router.push({ name: "Images", params: { pathMatch: folderPath } });
    },
    goBack() {
      if (!this.currentPathSegments.length) {
        return;
      }
      const parentPath = this.currentPathSegments.slice(0, -1).join("/");
      const target = parentPath ? `/images/${parentPath}` : "/images";
      this.$router.push(target);
    },
    goRoot() {
      this.$router.push("/images");
    },
    onFilesSelected(event) {
      this.pendingFiles = Array.from(event.target.files || []);
    },
    async uploadPhotos() {
      if (!this.pendingFiles.length || !this.token) {
        return;
      }

      const formData = new FormData();
      formData.append("path", this.currentPathParam);
      this.pendingFiles.forEach((file) => formData.append("files", file));

      this.uploading = true;
      try {
        await axios.post(`${FILES_API_URL}/files/add/`, formData, {
          headers: {
            Authorization: `Bearer ${this.token}`,
            "Content-Type": "multipart/form-data",
          },
        });
        this.pendingFiles = [];
        if (this.$refs.fileInput) {
          this.$refs.fileInput.value = "";
        }
        this.fetchDirectoryContent();
      } catch (error) {
        console.error("Error uploading photos:", error);
      } finally {
        this.uploading = false;
      }
    },
    async createFolder() {
      if (!this.newFolderName.trim() || !this.token) {
        return;
      }

      this.creatingFolder = true;
      try {
        await axios.post(
          `${FILES_API_URL}/files/folder/`,
          {
            path: this.currentPathParam,
            folder_name: this.newFolderName.trim(),
          },
          {
            headers: { Authorization: `Bearer ${this.token}` },
          }
        );
        this.newFolderName = "";
        this.fetchDirectoryContent();
      } catch (error) {
        console.error("Error creating folder:", error);
      } finally {
        this.creatingFolder = false;
      }
    },
    viewImage(item) {
      this.$router.push({ path: "/image", query: { path: item.Path } });
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
        console.error("Erreur lors du telechargement de l'image :", error);
      }
    },
    handleTokenUpdate(newToken) {
      this.token = newToken;
      if (!newToken) {
        this.isAdmin = false;
        return;
      }
      this.determineAdmin();
    },
  },
  mounted() {
    this.fetchDirectoryContent();
    this.determineAdmin();
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

.folder-icon {
  font-size: 1.5rem;
  font-weight: 600;
}
</style>
