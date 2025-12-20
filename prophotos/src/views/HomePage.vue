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
            <div class="card h-100 shadow-sm item-card">
              <div class="item-card-inner">
                <div
                  v-if="item.Img"
                  class="media-slot is-clickable"
                  @click="viewImage(item)"
                >
                  <img 
                    :src="item.Img" 
                    alt="Preview" 
                    class="media-image"
                  />
                </div>

                <div
                  v-else-if="item.isDirectory"
                  class="media-slot folder-slot is-clickable"
                  @click="navigateToFolder(item.Path)"
                >
                  <div class="folder-glyph">DIR</div>
                </div>

                <div v-else class="media-slot file-slot">
                  <div class="file-glyph">FILE</div>
                </div>

                <div class="item-meta">
                  <div class="item-name" :title="item.Name">{{ item.Name }}</div>
                  <div class="item-type">{{ item.isDirectory ? "Dossier" : "Fichier" }}</div>
                </div>

                <div class="item-actions">
                  <button 
                    v-if="item.Img && token"
                    @click.stop="downloadImage(item.Path, item.Name)" 
                    class="btn btn-primary btn-sm"
                  >
                    Telecharger
                  </button>
                  <button
                    v-if="token && isAdmin"
                    @click.stop="deleteItem(item)"
                    class="btn btn-danger btn-sm"
                  >
                    Supprimer
                  </button>
                </div>
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
    async deleteItem(item) {
      if (!this.token || !this.isAdmin) {
        return;
      }

      const label = item.isDirectory ? "dossier" : "fichier";
      if (!window.confirm(`Supprimer ce ${label} ?`)) {
        return;
      }

      try {
        await axios.post(
          `${FILES_API_URL}/files/delete/`,
          { path: item.Path },
          { headers: { Authorization: `Bearer ${this.token}` } }
        );
        this.fetchDirectoryContent();
      } catch (error) {
        console.error("Error deleting item:", error);
        alert("Erreur lors de la suppression.");
      }
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

.item-card {
  border: 1px solid #e9ecef;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
  overflow: hidden;
}

.item-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.08);
}

.item-card-inner {
  display: flex;
  flex-direction: column;
  height: 100%;
  text-align: center;
}

.media-slot {
  height: 9.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f7f8fb;
  border-bottom: 1px solid #eef1f4;
}

.media-slot.is-clickable {
  cursor: pointer;
}

.media-image {
  max-height: 100%;
  max-width: 100%;
  object-fit: contain;
}

.folder-slot {
  background: linear-gradient(135deg, #f4f7ff, #e7eeff);
}

.folder-glyph {
  width: 3.25rem;
  height: 3.25rem;
  border-radius: 12px;
  background: #eef3ff;
  border: 1px solid #d7e2ff;
  color: #1f2a44;
  font-size: 0.85rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  letter-spacing: 0.08em;
}

.file-slot {
  background: #f6f7f8;
}

.file-glyph {
  width: 3.25rem;
  height: 3.25rem;
  border-radius: 12px;
  background: #f0f1f3;
  border: 1px solid #e2e5e9;
  color: #4b5563;
  font-size: 0.85rem;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  letter-spacing: 0.08em;
}

.item-meta {
  padding: 0.6rem 0.75rem 0.35rem;
}

.item-name {
  font-size: 0.95rem;
  font-weight: 600;
  color: #1f2937;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.item-type {
  margin-top: 0.15rem;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #6b7280;
}

.item-actions {
  margin-top: auto;
  display: flex;
  gap: 0.5rem;
  justify-content: center;
  flex-wrap: wrap;
  padding: 0.5rem 0.75rem 0.75rem;
  border-top: 1px solid #eef1f4;
  background: #ffffff;
}
</style>
