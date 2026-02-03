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

        <div class="d-flex flex-wrap align-items-center gap-2 mb-3">
          <label class="form-label mb-0" for="sort-type">Trier par</label>
          <select id="sort-type" v-model="sortType" class="form-select w-auto">
            <option value="photos-first">Photos d'abord (defaut)</option>
            <option value="name-asc">Nom A-Z</option>
            <option value="name-desc">Nom Z-A</option>
            <option value="type">Type (Dossiers, Photos, Fichiers)</option>
          </select>
        </div>

        <!-- Admin Actions Bar (compact icons) -->
        <div v-if="token && isAdmin" class="admin-actions-bar mb-4">
          <div class="d-flex align-items-center gap-2 flex-wrap">
            <span class="text-muted small me-2 path-display" :title="currentPath">{{ displayPath }}</span>

            <!-- Add Photos Button -->
            <button
              type="button"
              class="btn btn-action"
              :class="{ 'btn-action-active': pendingFiles.length }"
              @click="triggerFileInput"
              :disabled="uploading"
              title="Ajouter des photos"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                <circle cx="8.5" cy="8.5" r="1.5"></circle>
                <polyline points="21 15 16 10 5 21"></polyline>
              </svg>
              <span v-if="pendingFiles.length" class="badge-count">{{ pendingFiles.length }}</span>
            </button>
            <input
              ref="fileInput"
              type="file"
              multiple
              class="d-none"
              @change="onFilesSelected"
            />

            <!-- Upload Button (shows when files selected) -->
            <button
              v-if="pendingFiles.length"
              type="button"
              class="btn btn-primary btn-sm"
              :disabled="uploading"
              @click="uploadPhotos"
            >
              {{ uploading ? "Envoi..." : "Envoyer" }}
            </button>
            <button
              v-if="pendingFiles.length"
              type="button"
              class="btn btn-outline-secondary btn-sm"
              @click="clearPendingFiles"
            >
              Annuler
            </button>

            <!-- Create Folder Button -->
            <button
              type="button"
              class="btn btn-action"
              :class="{ 'btn-action-active': showFolderInput }"
              @click="toggleFolderInput"
              :disabled="creatingFolder"
              title="Créer un dossier"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"></path>
                <line x1="12" y1="11" x2="12" y2="17"></line>
                <line x1="9" y1="14" x2="15" y2="14"></line>
              </svg>
            </button>

            <!-- Folder Name Input (inline) -->
            <div v-if="showFolderInput" class="folder-input-inline d-flex align-items-center gap-2">
              <input
                ref="folderNameInput"
                v-model="newFolderName"
                type="text"
                class="form-control form-control-sm"
                placeholder="Nom du dossier"
                @keyup.enter="createFolder"
                @keyup.escape="toggleFolderInput"
                style="width: 180px;"
              />
              <button
                type="button"
                class="btn btn-primary btn-sm"
                :disabled="!newFolderName || creatingFolder"
                @click="createFolder"
              >
                {{ creatingFolder ? "..." : "Créer" }}
              </button>
            </div>

            <!-- Scan Folder Button -->
            <button
              type="button"
              class="btn btn-action"
              :class="{ 'btn-action-scanning': isScanningFolder }"
              @click="scanCurrentFolder"
              :disabled="isScanningFolder"
              title="Scanner ce dossier (Reconnaissance Faciale)"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
                <circle cx="12" cy="7" r="4"></circle>
              </svg>
              <span v-if="isScanningFolder" class="spinner-icon"></span>
            </button>

            <!-- Scan Progress (inline) -->
            <div v-if="folderScanProgress" class="scan-progress-inline d-flex align-items-center gap-2">
              <div class="progress" style="width: 100px; height: 6px;">
                <div
                  class="progress-bar bg-warning"
                  :style="{ width: folderScanProgress.percentage + '%' }"
                ></div>
              </div>
              <small class="text-muted">{{ folderScanProgress.processed }}/{{ folderScanProgress.total }}</small>
            </div>
          </div>

          <!-- Scan Results (dismissible) -->
          <div v-if="folderScanComplete" class="alert alert-success alert-dismissible mt-2 mb-0 py-2">
            <small>
              <strong>Scan terminé!</strong>
              {{ folderScanComplete.success }} scannée(s),
              {{ folderScanComplete.total_faces }} visage(s),
              {{ folderScanComplete.already_scanned }} déjà scannée(s),
              {{ folderScanComplete.errors }} erreur(s)
            </small>
            <button type="button" class="btn-close btn-close-sm" @click="folderScanComplete = null"></button>
          </div>
        </div>

        <!-- Selection Actions Bar -->
        <div v-if="selectedItems.length > 0" class="selection-bar bg-primary text-white p-3 mb-3 rounded d-flex justify-content-between align-items-center">
          <div>
            <strong>{{ selectedItems.length }}</strong> / {{ sortedDirectoryContent.length }} élément(s) sélectionné(s)
            <button @click="selectAll" class="btn btn-sm btn-light ms-2" v-if="selectedItems.length < sortedDirectoryContent.length">
              Tout sélectionner
            </button>
            <button @click="clearSelection" class="btn btn-sm btn-outline-light ms-2">
              Annuler
            </button>
          </div>
          <div class="d-flex gap-2">
            <button
              v-if="hasSelectedImages"
              @click="downloadSelected"
              class="btn btn-sm btn-light"
              :disabled="isProcessingSelection"
            >
              Télécharger
            </button>
            <button
              v-if="token && isAdmin && hasSelectedImages"
              @click="scanSelected"
              class="btn btn-sm btn-warning"
              :disabled="isProcessingSelection"
            >
              {{ isProcessingSelection ? 'Scan...' : 'Scanner' }}
            </button>
            <button
              v-if="token && isAdmin"
              @click="deleteSelected"
              class="btn btn-sm btn-danger"
              :disabled="isProcessingSelection"
            >
              {{ isProcessingSelection ? 'Suppression...' : 'Supprimer' }}
            </button>
          </div>
        </div>

        <!-- Grille style explorateur -->
        <div class="row g-4">
          <div
            v-for="(item, index) in sortedDirectoryContent"
            :key="index"
            class="col-6 col-sm-4 col-md-3 col-lg-2"
          >
            <div
              class="card h-100 shadow-sm item-card"
              :class="{ 'border-primary': isSelected(item), 'selected-item': isSelected(item) }"
              @contextmenu.prevent="showContextMenu($event, item)"
              @touchstart="handleTouchStart($event, item)"
              @touchend="handleTouchEnd"
              @touchmove="handleTouchMove"
            >
              <div class="item-card-inner">
                <!-- Zone de sélection avec indicateur - zone tactile agrandie -->
                <div
                  class="selection-zone"
                  v-if="token"
                  @click.stop="toggleSelection(item)"
                >
                  <div
                    class="selection-indicator"
                    :class="{ 'is-selected': isSelected(item) }"
                  >
                    <svg v-if="isSelected(item)" class="checkmark" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                      <polyline points="20 6 9 17 4 12"></polyline>
                    </svg>
                  </div>
                </div>

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

                <div class="item-fullname">{{ item.Name }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Context Menu -->
        <div
          v-if="contextMenu.show"
          class="context-menu"
          :style="{ top: contextMenu.y + 'px', left: contextMenu.x + 'px' }"
          @click.stop
        >
          <ul class="list-unstyled mb-0">
            <li v-if="contextMenu.item && contextMenu.item.Img">
              <a href="#" @click.prevent="viewImage(contextMenu.item); hideContextMenu()">
                Voir l'image
              </a>
            </li>
            <li v-if="contextMenu.item && contextMenu.item.Img && token">
              <a href="#" @click.prevent="downloadImage(contextMenu.item.Path, contextMenu.item.Name); hideContextMenu()">
                Télécharger
              </a>
            </li>
            <li v-if="contextMenu.item && !isSelected(contextMenu.item) && token">
              <a href="#" @click.prevent="toggleSelection(contextMenu.item); hideContextMenu()">
                Sélectionner
              </a>
            </li>
            <li v-if="contextMenu.item && isSelected(contextMenu.item) && token">
              <a href="#" @click.prevent="toggleSelection(contextMenu.item); hideContextMenu()">
                Désélectionner
              </a>
            </li>
            <li v-if="token && isAdmin && contextMenu.item && contextMenu.item.Img" class="separator">
              <a href="#" @click.prevent="scanSingleImage(contextMenu.item); hideContextMenu()">
                Scanner (Recfac)
              </a>
            </li>
            <li v-if="token && isAdmin && contextMenu.item" class="text-danger">
              <a href="#" class="text-danger" @click.prevent="deleteItem(contextMenu.item); hideContextMenu()">
                Supprimer
              </a>
            </li>
          </ul>
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

import { FILES_API_URL, USERS_API_URL, RECFAC_API_URL } from "@/constants";

const PHOTO_EXTENSIONS = new Set([".png", ".jpg", ".jpeg", ".gif", ".webp"]);

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
      sortType: "photos-first",
      // Folder scan
      isScanningFolder: false,
      folderScanProgress: null,
      folderScanComplete: null,
      folderScanEventSource: null,
      // Selection multiple
      selectedItems: [],
      isProcessingSelection: false,
      // Context menu
      contextMenu: {
        show: false,
        x: 0,
        y: 0,
        item: null,
      },
      // Touch long press (mobile)
      touchTimer: null,
      touchStartPos: null,
      // Folder input toggle
      showFolderInput: false,
    };
  },
  computed: {
    currentPathParam() {
      const pathMatch = this.$route.params.pathMatch;
      if (!pathMatch) return "";
      // pathMatch peut être un tableau avec /:pathMatch(.*)*
      if (Array.isArray(pathMatch)) {
        return pathMatch.join("/");
      }
      return String(pathMatch);
    },
    currentPath() {
      return this.currentPathParam ? `/${this.currentPathParam}` : "/";
    },
    currentPathSegments() {
      return this.currentPathParam ? this.currentPathParam.split("/").filter(Boolean) : [];
    },
    displayPath() {
      const segments = this.currentPathSegments;
      if (segments.length <= 3) {
        return this.currentPath;
      }
      // Garder les 3 derniers segments avec "..." au début
      const lastThree = segments.slice(-3);
      return "/.../" + lastThree.join("/");
    },
    canGoUp() {
      return this.currentPathSegments.length > 0;
    },
    hasSelectedImages() {
      return this.selectedItems.some(item => item.Img);
    },
    sortedDirectoryContent() {
      // S'assurer que directoryContent est un tableau
      const content = Array.isArray(this.directoryContent) ? this.directoryContent : [];

      // Filtrer pour ne garder que les photos et dossiers
      const filtered = content.filter(item =>
        item.isDirectory || this.isPhotoItem(item)
      );

      const decorated = filtered.map((item, index) => ({
        item,
        index,
      }));

      const byName = (a, b) =>
        a.item.Name.localeCompare(b.item.Name, "fr", {
          numeric: true,
          sensitivity: "base",
        });

      if (this.sortType === "name-asc") {
        return decorated.sort(byName).map((entry) => entry.item);
      }

      if (this.sortType === "name-desc") {
        return decorated.sort((a, b) => byName(b, a)).map((entry) => entry.item);
      }

      if (this.sortType === "type") {
        const typeRank = (entry) => {
          if (entry.item.isDirectory) {
            return 0;
          }
          if (this.isPhotoItem(entry.item)) {
            return 1;
          }
          return 2;
        };

        return decorated
          .sort((a, b) => {
            const rankDiff = typeRank(a) - typeRank(b);
            if (rankDiff !== 0) {
              return rankDiff;
            }
            return a.index - b.index;
          })
          .map((entry) => entry.item);
      }

      return decorated
        .sort((a, b) => {
          const aNonPhoto = this.isPhotoItem(a.item) ? 0 : 1;
          const bNonPhoto = this.isPhotoItem(b.item) ? 0 : 1;
          const diff = aNonPhoto - bNonPhoto;
          if (diff !== 0) {
            return diff;
          }
          return a.index - b.index;
        })
        .map((entry) => entry.item);
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
      this.clearSelection();
      this.hideContextMenu();
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

        // Inclure le token si connecte pour obtenir des miniatures de meilleure qualite
        const config = {
          params: { path: this.currentPathParam },
        };
        if (this.token) {
          config.headers = { Authorization: `Bearer ${this.token}` };
        }

        const response = await axios.get(`${FILES_API_URL}/files/`, config);

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
    isPhotoItem(item) {
      if (!item || item.isDirectory) {
        return false;
      }
      const name = item.Name || "";
      const dotIndex = name.lastIndexOf(".");
      if (dotIndex === -1) {
        return false;
      }
      const extension = name.slice(dotIndex).toLowerCase();
      return PHOTO_EXTENSIONS.has(extension);
    },

    // === Selection Methods ===
    isSelected(item) {
      return this.selectedItems.some(i => i.Path === item.Path);
    },
    toggleSelection(item) {
      if (this.isSelected(item)) {
        this.selectedItems = this.selectedItems.filter(i => i.Path !== item.Path);
      } else {
        this.selectedItems.push(item);
      }
    },
    clearSelection() {
      this.selectedItems = [];
    },
    selectAll() {
      this.selectedItems = [...this.sortedDirectoryContent];
    },
    handleKeydown(event) {
      // Escape pour annuler la sélection
      if (event.key === 'Escape') {
        this.clearSelection();
        this.hideContextMenu();
      }
      // Ctrl+A pour tout sélectionner
      if ((event.ctrlKey || event.metaKey) && event.key === 'a' && this.token) {
        event.preventDefault();
        this.selectAll();
      }
    },

    // === Context Menu Methods ===
    showContextMenu(event, item) {
      const menuWidth = 200; // Largeur approximative du menu
      const menuHeight = 250; // Hauteur approximative du menu
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;
      const padding = 10; // Marge de sécurité

      let x = event.clientX;
      let y = event.clientY;

      // Si le menu dépasse à droite, l'afficher à gauche du curseur
      if (x + menuWidth + padding > viewportWidth) {
        x = Math.max(padding, x - menuWidth);
      }

      // Si le menu dépasse en bas, l'afficher au-dessus du curseur
      if (y + menuHeight + padding > viewportHeight) {
        y = Math.max(padding, y - menuHeight);
      }

      this.contextMenu = {
        show: true,
        x: x,
        y: y,
        item: item,
      };
    },
    hideContextMenu() {
      this.contextMenu.show = false;
    },

    // === Touch/Mobile Methods (appui long) ===
    handleTouchStart(event, item) {
      // Sauvegarder la position initiale
      const touch = event.touches[0];
      this.touchStartPos = { x: touch.clientX, y: touch.clientY };

      // Démarrer le timer pour appui long (500ms)
      this.touchTimer = setTimeout(() => {
        // Vibration feedback si disponible
        if (navigator.vibrate) {
          navigator.vibrate(50);
        }
        // Afficher le menu contextuel à la position du touch
        this.showContextMenu({ clientX: touch.clientX, clientY: touch.clientY }, item);
      }, 500);
    },
    handleTouchEnd() {
      // Annuler le timer si le doigt est relevé avant 500ms
      if (this.touchTimer) {
        clearTimeout(this.touchTimer);
        this.touchTimer = null;
      }
    },
    handleTouchMove(event) {
      // Annuler si l'utilisateur bouge trop (scroll)
      if (this.touchTimer && this.touchStartPos) {
        const touch = event.touches[0];
        const deltaX = Math.abs(touch.clientX - this.touchStartPos.x);
        const deltaY = Math.abs(touch.clientY - this.touchStartPos.y);
        if (deltaX > 10 || deltaY > 10) {
          clearTimeout(this.touchTimer);
          this.touchTimer = null;
        }
      }
    },

    // === Selection Actions ===
    async downloadSelected() {
      // Télécharger chaque image sélectionnée
      const images = this.selectedItems.filter(item => item.Img);
      for (const item of images) {
        await this.downloadImage(item.Path, item.Name);
      }
    },
    async scanSelected() {
      if (!this.token || !this.isAdmin) return;

      const images = this.selectedItems.filter(item => item.Img);
      if (images.length === 0) return;

      this.isProcessingSelection = true;

      try {
        const paths = images.map(item => item.Path);
        const response = await axios.post(
          `${RECFAC_API_URL}/recfac/scan-multiple/`,
          { paths },
          { headers: { Authorization: `Bearer ${this.token}` } }
        );

        const data = response.data;
        alert(
          `Scan terminé!\n` +
          `${data.scanned_count} image(s) scannée(s)\n` +
          `${data.already_scanned_count} déjà scannée(s)\n` +
          `${data.total_faces} visage(s) détecté(s)\n` +
          `${data.errors_count} erreur(s)`
        );

        this.clearSelection();
      } catch (error) {
        console.error("Erreur lors du scan:", error);
        alert("Erreur lors du scan des images");
      } finally {
        this.isProcessingSelection = false;
      }
    },
    async deleteSelected() {
      if (!this.token || !this.isAdmin) return;

      if (!confirm(`Supprimer ${this.selectedItems.length} élément(s) ?`)) {
        return;
      }

      this.isProcessingSelection = true;

      try {
        const paths = this.selectedItems.map(item => item.Path);
        const response = await axios.post(
          `${FILES_API_URL}/files/delete-multiple/`,
          { paths },
          { headers: { Authorization: `Bearer ${this.token}` } }
        );

        const data = response.data;
        alert(
          `Suppression terminée!\n` +
          `${data.deleted_count} élément(s) supprimé(s)\n` +
          `${data.errors_count} erreur(s)`
        );

        this.clearSelection();
        await this.fetchDirectoryContent();
      } catch (error) {
        console.error("Erreur lors de la suppression:", error);
        alert("Erreur lors de la suppression");
      } finally {
        this.isProcessingSelection = false;
      }
    },
    async scanSingleImage(item) {
      if (!this.token || !this.isAdmin || !item.Img) return;

      try {
        const response = await axios.post(
          `${RECFAC_API_URL}/recfac/scan-image/`,
          { path: item.Path },
          { headers: { Authorization: `Bearer ${this.token}` } }
        );

        const data = response.data;
        if (data.already_scanned) {
          alert(`Image déjà scannée (${data.faces_count} visage(s))`);
        } else {
          alert(`Scan terminé! ${data.faces_count} visage(s) détecté(s)`);
        }
      } catch (error) {
        console.error("Erreur lors du scan:", error);
        alert("Erreur lors du scan de l'image");
      }
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
    triggerFileInput() {
      this.$refs.fileInput.click();
    },
    onFilesSelected(event) {
      this.pendingFiles = Array.from(event.target.files || []);
    },
    clearPendingFiles() {
      this.pendingFiles = [];
      if (this.$refs.fileInput) {
        this.$refs.fileInput.value = "";
      }
    },
    toggleFolderInput() {
      this.showFolderInput = !this.showFolderInput;
      if (this.showFolderInput) {
        this.$nextTick(() => {
          if (this.$refs.folderNameInput) {
            this.$refs.folderNameInput.focus();
          }
        });
      } else {
        this.newFolderName = "";
      }
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
        this.showFolderInput = false;
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

    // Folder scan methods
    async scanCurrentFolder() {
      if (!this.token || !this.isAdmin) {
        alert("Accès réservé aux administrateurs");
        return;
      }

      this.isScanningFolder = true;
      this.folderScanProgress = null;
      this.folderScanComplete = null;

      try {
        const folderPath = this.currentPathParam || "";
        const url = `${RECFAC_API_URL}/recfac/scan-folder/?token=${encodeURIComponent(this.token)}&folder_path=${encodeURIComponent(folderPath)}`;

        this.folderScanEventSource = new EventSource(url);

        this.folderScanEventSource.addEventListener("message", (event) => {
          try {
            const data = JSON.parse(event.data);

            if (data.status === "started") {
              this.folderScanProgress = {
                processed: 0,
                total: data.total,
                percentage: 0,
              };
            } else if (data.status === "progress") {
              this.folderScanProgress = {
                processed: data.processed,
                total: data.total,
                percentage: Math.round((data.processed / data.total) * 100),
              };
            } else if (data.status === "completed") {
              this.folderScanComplete = data;
              this.isScanningFolder = false;
              if (this.folderScanEventSource) {
                this.folderScanEventSource.close();
                this.folderScanEventSource = null;
              }
            } else if (data.status === "error") {
              alert("Erreur: " + data.message);
              this.isScanningFolder = false;
              if (this.folderScanEventSource) {
                this.folderScanEventSource.close();
                this.folderScanEventSource = null;
              }
            }
          } catch (error) {
            console.error("Error parsing SSE data:", error);
          }
        });

        this.folderScanEventSource.addEventListener("error", () => {
          console.error("SSE connection error");
          this.isScanningFolder = false;
          if (this.folderScanEventSource) {
            this.folderScanEventSource.close();
            this.folderScanEventSource = null;
          }
        });
      } catch (error) {
        console.error("Error starting folder scan:", error);
        alert("Erreur lors du démarrage du scan");
        this.isScanningFolder = false;
      }
    },
  },
  mounted() {
    this.fetchDirectoryContent();
    this.determineAdmin();
    // Event listeners pour menu contextuel et sélection
    document.addEventListener('click', this.hideContextMenu);
    document.addEventListener('keydown', this.handleKeydown);
  },
  beforeUnmount() {
    if (this.folderScanEventSource) {
      this.folderScanEventSource.close();
    }
    // Nettoyer les event listeners
    document.removeEventListener('click', this.hideContextMenu);
    document.removeEventListener('keydown', this.handleKeydown);
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
  position: relative;
  /* Prevent iOS native context menu on long press */
  -webkit-touch-callout: none;
  -webkit-user-select: none;
  user-select: none;
  touch-action: manipulation;
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
  /* Prevent iOS image save callout */
  -webkit-touch-callout: none;
  pointer-events: none;
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

.item-fullname {
  position: absolute;
  left: 0.5rem;
  right: 0.5rem;
  bottom: 3.25rem;
  padding: 0.35rem 0.5rem;
  background: rgba(15, 23, 42, 0.92);
  color: #ffffff;
  border-radius: 0.4rem;
  font-size: 0.75rem;
  line-height: 1.2;
  opacity: 0;
  transform: translateY(6px);
  transition: opacity 0.15s ease, transform 0.15s ease;
  pointer-events: none;
  word-break: break-word;
}

.item-card:hover .item-fullname {
  opacity: 1;
  transform: translateY(0);
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

/* Selection styles */
.selection-zone {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 10;
  /* Zone tactile plus grande que le cercle visible */
  width: 3rem;
  height: 3rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.selection-indicator {
  width: 1.75rem;
  height: 1.75rem;
  border-radius: 50%;
  background-color: rgba(255, 255, 255, 0.95);
  border: 2px solid #6c757d;
  opacity: 0.7;
  transition: opacity 0.15s ease, transform 0.15s ease, background-color 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.selection-zone:hover .selection-indicator {
  opacity: 1;
  transform: scale(1.1);
  box-shadow: 0 3px 8px rgba(0, 0, 0, 0.15);
}

.selection-indicator.is-selected {
  opacity: 1;
  background-color: #0d6efd;
  border-color: #0d6efd;
  transform: scale(1.1);
  box-shadow: 0 3px 8px rgba(13, 110, 253, 0.4);
}

.selection-indicator .checkmark {
  width: 1.1rem;
  height: 1.1rem;
  color: white;
}

/* Mobile: zone tactile encore plus grande */
@media (max-width: 768px) {
  .selection-zone {
    width: 3.5rem;
    height: 3.5rem;
  }

  .selection-indicator {
    opacity: 1;
    width: 2rem;
    height: 2rem;
  }

  .selection-indicator .checkmark {
    width: 1.3rem;
    height: 1.3rem;
  }
}

.selected-item {
  border-color: #0d6efd !important;
  box-shadow: 0 0 0 3px rgba(13, 110, 253, 0.25) !important;
}

.selection-bar {
  position: sticky;
  top: 0;
  z-index: 100;
}

/* Context Menu styles */
.context-menu {
  position: fixed;
  z-index: 1000;
  min-width: 180px;
  background: #ffffff;
  border: 1px solid #e9ecef;
  border-radius: 0.5rem;
  box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
  padding: 0.5rem 0;
}

.context-menu ul {
  margin: 0;
  padding: 0;
}

.context-menu li {
  list-style: none;
}

.context-menu li a {
  display: block;
  padding: 0.5rem 1rem;
  color: #1f2937;
  text-decoration: none;
  font-size: 0.875rem;
  transition: background-color 0.15s ease;
}

.context-menu li a:hover {
  background-color: #f3f4f6;
}

.context-menu li.separator {
  border-top: 1px solid #e9ecef;
  margin-top: 0.25rem;
  padding-top: 0.25rem;
}

.context-menu li a.text-danger:hover {
  background-color: #fef2f2;
}

/* Mobile context menu adjustments */
@media (max-width: 768px) {
  .context-menu {
    min-width: 200px;
    max-width: calc(100vw - 2rem);
  }

  .context-menu li a {
    padding: 0.75rem 1rem;
    font-size: 1rem;
  }

  /* Barre de sélection responsive */
  .selection-bar {
    flex-direction: column;
    gap: 0.75rem;
    text-align: center;
  }

  .selection-bar .d-flex.gap-2 {
    flex-wrap: wrap;
    justify-content: center;
  }
}

/* Admin Actions Bar styles */
.admin-actions-bar {
  background: #f8f9fa;
  border: 1px solid #e9ecef;
  border-radius: 0.5rem;
  padding: 0.75rem 1rem;
}

.btn-action {
  width: 42px;
  height: 42px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ffffff;
  border: 1px solid #dee2e6;
  border-radius: 0.5rem;
  color: #495057;
  transition: all 0.15s ease;
  position: relative;
}

.btn-action:hover {
  background: #e9ecef;
  border-color: #ced4da;
  color: #212529;
  transform: translateY(-1px);
}

.btn-action:active {
  transform: translateY(0);
}

.btn-action:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.btn-action-active {
  background: #0d6efd;
  border-color: #0d6efd;
  color: #ffffff;
}

.btn-action-active:hover {
  background: #0b5ed7;
  border-color: #0a58ca;
  color: #ffffff;
}

.btn-action-scanning {
  background: #ffc107;
  border-color: #ffc107;
  color: #212529;
}

.btn-action .badge-count {
  position: absolute;
  top: -6px;
  right: -6px;
  background: #dc3545;
  color: white;
  font-size: 0.7rem;
  font-weight: 600;
  min-width: 18px;
  height: 18px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-action .spinner-icon {
  position: absolute;
  top: -4px;
  right: -4px;
  width: 14px;
  height: 14px;
  border: 2px solid #ffc107;
  border-top-color: transparent;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.folder-input-inline,
.scan-progress-inline {
  animation: fadeIn 0.15s ease;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateX(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.alert-dismissible .btn-close-sm {
  padding: 0.5rem;
  font-size: 0.75rem;
}

.path-display {
  max-width: 200px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  cursor: help;
}

/* Mobile adjustments for admin bar */
@media (max-width: 576px) {
  .admin-actions-bar {
    padding: 0.5rem 0.75rem;
  }

  .btn-action {
    width: 38px;
    height: 38px;
  }

  .btn-action svg {
    width: 18px;
    height: 18px;
  }

  .folder-input-inline input {
    width: 140px !important;
  }
}
</style>
