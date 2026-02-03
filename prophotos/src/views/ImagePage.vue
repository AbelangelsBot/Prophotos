<template>
  <div class="image-page-container">
    <NavigationBar :token="token" />

    <div class="container mt-4">
      <!-- Navigation entre images -->
      <div class="image-viewer-wrapper">
        <!-- Bouton précédent (PC) -->
        <button
          v-if="hasPreviousImage"
          @click="goToPreviousImage"
          class="nav-btn nav-btn-left d-none d-md-flex"
          title="Image précédente"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
        </button>

        <!-- Image principale avec swipe -->
        <div
          class="card shadow-lg image-card"
          @touchstart="handleSwipeStart"
          @touchmove="handleSwipeMove"
          @touchend="handleSwipeEnd"
        >
          <div class="image-container">
            <img
              :src="imageData.Img"
              class="card-img-top"
              alt="Image Preview"
              :style="{ transform: `translateX(${swipeOffset}px)` }"
              @contextmenu.prevent
              @dragstart.prevent
            />

            <!-- Indicateur de swipe (mobile) -->
            <div v-if="isSwipingLeft" class="swipe-indicator swipe-indicator-left">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="15 18 9 12 15 6"></polyline>
              </svg>
            </div>
            <div v-if="isSwipingRight" class="swipe-indicator swipe-indicator-right">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <polyline points="9 18 15 12 9 6"></polyline>
              </svg>
            </div>
          </div>

          <div class="card-body">
            <h5 class="card-title">{{ imageData.Name }}</h5>
            <p class="card-text"><strong>Path:</strong> {{ imageData.Path }}</p>
            <p class="card-text"><strong>Size:</strong> {{ imageData.Size }}</p>
            <p class="card-text"><strong>Type:</strong> {{ imageData.Type }}</p>

            <!-- Boutons d'action AVANT la section recfac -->
            <div class="mt-3 d-flex flex-wrap gap-2 align-items-center">
              <button v-if="token" @click="downloadImage" class="btn btn-primary">
                Télécharger l'image
              </button>
              <button @click="goBackToFolder" class="btn btn-outline-secondary">
                Retour au dossier
              </button>
              <p v-if="!token" class="text-danger mb-0">Vous devez être connecté pour télécharger cette image.</p>
            </div>

            <!-- Navigation mobile (bas de page) -->
            <div class="d-flex d-md-none justify-content-between mt-3 mobile-nav">
              <button
                @click="goToPreviousImage"
                class="btn btn-outline-primary"
                :disabled="!hasPreviousImage"
              >
                &larr; Précédente
              </button>
              <span class="align-self-center text-muted small">
                {{ currentImageIndex + 1 }} / {{ folderImages.length }}
              </span>
              <button
                @click="goToNextImage"
                class="btn btn-outline-primary"
                :disabled="!hasNextImage"
              >
                Suivante &rarr;
              </button>
            </div>

            <!-- Section Reconnaissance Faciale (collapsible) -->
            <div v-if="recfacData" class="mt-4">
              <hr>
              <div class="recfac-section">
                <button
                  class="btn btn-link text-primary p-0 d-flex align-items-center w-100 text-start"
                  type="button"
                  @click="recfacExpanded = !recfacExpanded"
                >
                  <svg
                    class="collapse-icon me-2"
                    :class="{ 'rotated': recfacExpanded }"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    stroke-width="2"
                  >
                    <polyline points="9 18 15 12 9 6"></polyline>
                  </svg>
                  <span class="fw-bold">Reconnaissance Faciale</span>
                  <span v-if="recfacData.exists_in_db && recfacData.scanned" class="ms-2">
                    <span class="badge bg-info">{{ recfacData.faces_count }} visage(s)</span>
                    <span v-if="recfacData.persons_count > 0" class="badge bg-success ms-1">
                      {{ recfacData.persons_count }} identifié(s)
                    </span>
                  </span>
                </button>

                <div v-show="recfacExpanded" class="recfac-content mt-3">
                  <div v-if="recfacData.exists_in_db && recfacData.scanned">
                    <div v-if="recfacData.persons_count > 0" class="mb-3">
                      <p class="card-text mb-2">
                        <strong>Personnes identifiées:</strong>
                      </p>
                      <div class="d-flex flex-wrap gap-2">
                        <span
                          v-for="person in recfacData.persons"
                          :key="person.name"
                          class="badge bg-primary"
                        >
                          {{ person.name }} ({{ person.faces_count }} visage{{ person.faces_count > 1 ? 's' : '' }})
                        </span>
                      </div>
                    </div>

                    <p class="card-text text-muted">
                      <small>Scannée le: {{ formatDate(recfacData.scan_date) }}</small>
                    </p>
                  </div>

                  <div v-else-if="recfacData.exists_in_db && !recfacData.scanned">
                    <p class="text-muted">Image non scannée</p>
                    <button
                      v-if="token && isAdmin"
                      @click="scanImage"
                      class="btn btn-sm btn-outline-primary"
                      :disabled="isScanning"
                    >
                      <span v-if="isScanning" class="spinner-border spinner-border-sm me-2"></span>
                      {{ isScanning ? 'Scan en cours...' : 'Scanner cette image' }}
                    </button>
                  </div>

                  <div v-else>
                    <p class="text-muted">Image non indexée dans le système recfac</p>
                  </div>

                  <!-- Faces Tagging Section (Admin only) -->
                  <div v-if="token && isAdmin && recfacData && recfacData.faces && recfacData.faces.length > 0" class="mt-4">
                    <hr>
                    <h6 class="text-warning">Tagger les visages</h6>

                    <!-- Canvas pour afficher l'image avec les faces -->
                    <div class="position-relative mb-3" style="max-width: 800px;">
                      <canvas
                        ref="facesCanvas"
                        @mousemove="onCanvasHover"
                        @mouseleave="onCanvasLeave"
                        style="cursor: pointer; border: 1px solid #ddd; width: 100%; height: auto;"
                      ></canvas>
                    </div>

                    <!-- Liste des visages détectés -->
                    <div class="row g-3">
                      <div
                        v-for="(face, index) in recfacData.faces"
                        :key="face.face_id"
                        class="col-md-6 col-lg-4"
                      >
                        <div
                          class="card face-card"
                          :class="{ 'border-warning': hoveredFaceIndex === index }"
                          :style="{ borderColor: getFaceColor(index) }"
                        >
                          <div class="card-body">
                            <!-- Header avec apercu du visage -->
                            <div class="face-header mb-3">
                              <!-- Apercu du visage (crop) -->
                              <div
                                class="face-thumbnail"
                                :style="{ borderColor: getFaceColor(index) }"
                              >
                                <canvas
                                  :ref="'faceCrop' + index"
                                  class="face-crop-canvas"
                                ></canvas>
                              </div>

                              <!-- Info du visage -->
                              <div class="face-info">
                                <h6 class="card-title mb-1">
                                  <span
                                    class="face-number"
                                    :style="{ backgroundColor: getFaceColor(index), color: getContrastColor(getFaceColor(index)) }"
                                  >
                                    #{{ index + 1 }}
                                  </span>
                                  <span class="badge bg-secondary ms-2">{{ Math.round(face.det_score * 100) }}%</span>
                                </h6>

                                <p v-if="face.person_name" class="text-success mb-0 small">
                                  <strong>{{ face.person_name }}</strong>
                                </p>
                                <p v-else class="text-muted mb-0 small">
                                  <em>Non taggé</em>
                                </p>
                              </div>
                            </div>

                            <!-- Toggle: Personne existante ou nouvelle -->
                            <div class="btn-group btn-group-sm w-100 mb-2" role="group">
                              <input
                                type="radio"
                                class="btn-check"
                                :id="'useExisting' + index"
                                :name="'tagMode' + index"
                                v-model="face.useExisting"
                                :value="true"
                                @change="onFaceTagModeChange(face)"
                              />
                              <label class="btn btn-outline-secondary" :for="'useExisting' + index">
                                <small>Existante</small>
                              </label>

                              <input
                                type="radio"
                                class="btn-check"
                                :id="'useNew' + index"
                                :name="'tagMode' + index"
                                v-model="face.useExisting"
                                :value="false"
                              />
                              <label class="btn btn-outline-secondary" :for="'useNew' + index">
                                <small>Nouvelle</small>
                              </label>
                            </div>

                            <!-- Select existing person -->
                            <div v-if="face.useExisting" class="mb-2">
                              <select v-model="face.newTagName" class="form-select form-select-sm">
                                <option value="">-- Choisir --</option>
                                <option v-for="person in personsList" :key="person.name" :value="person.name">
                                  {{ person.name }}
                                </option>
                              </select>
                            </div>

                            <!-- Input new person -->
                            <div v-else class="mb-2">
                              <input
                                v-model="face.newTagName"
                                type="text"
                                class="form-control form-control-sm"
                                placeholder="Nom de la personne"
                                @keyup.enter="tagFace(face)"
                              />
                            </div>

                            <!-- Tag button -->
                            <button
                              @click="tagFace(face)"
                              class="btn btn-warning btn-sm w-100 mb-2"
                              :disabled="!face.newTagName || face.isTagging"
                            >
                              {{ face.isTagging ? 'Tagging...' : 'Tagger' }}
                            </button>

                            <div class="form-check form-check-sm">
                              <input
                                v-model="face.autoTagSimilar"
                                type="checkbox"
                                class="form-check-input"
                                :id="'autoTag' + index"
                              />
                              <label class="form-check-label" :for="'autoTag' + index">
                                <small>Auto-tagger visages similaires (≥60%)</small>
                              </label>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Bouton suivant (PC) -->
        <button
          v-if="hasNextImage"
          @click="goToNextImage"
          class="nav-btn nav-btn-right d-none d-md-flex"
          title="Image suivante"
        >
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </button>
      </div>

      <!-- Compteur d'images (PC) -->
      <div class="text-center mt-2 d-none d-md-block text-muted">
        <small v-if="folderImages.length > 0">
          Image {{ currentImageIndex + 1 }} sur {{ folderImages.length }}
          <span class="ms-2">
            (← → pour naviguer)
          </span>
        </small>
      </div>
    </div>

    <FooterSection />
  </div>
</template>

<script>
import NavigationBar from "@/components/NavBar.vue";
import FooterSection from "@/components/FootSection.vue";
import axios from "axios";

import { FILES_API_URL, RECFAC_API_URL } from "@/constants";
import { USERS_API_URL } from "@/constants";
export default {
  name: "ImagePage",

  data() {
    return {
      token: localStorage.getItem("token") || null,
      imageData: {},
      recfacData: null,
      isAdmin: false,
      isScanning: false,
      hoveredFaceIndex: null,
      canvasImage: null,
      personsList: [],
      // Navigation entre images
      folderImages: [],
      currentImageIndex: -1,
      // Swipe (mobile)
      swipeStartX: null,
      swipeOffset: 0,
      isSwiping: false,
      // Section recfac collapsible
      recfacExpanded: false,
    };
  },
  computed: {
    hasPreviousImage() {
      return this.currentImageIndex > 0;
    },
    hasNextImage() {
      return this.currentImageIndex < this.folderImages.length - 1;
    },
    isSwipingLeft() {
      return this.swipeOffset > 50;
    },
    isSwipingRight() {
      return this.swipeOffset < -50;
    },
  },
  methods: {
    async fetchImageData() {
      try {
        const response = await axios.get(`${FILES_API_URL}/files/image/`, {
          params: { path: this.$route.query.path },
          headers: { Authorization: `Bearer ${this.token}` },
        });
        this.imageData = response.data;

        // Charger les images du même dossier pour la navigation
        await this.loadFolderImages();
      } catch (error) {
        console.error("Erreur lors de la récupération de l'image :", error);
      }
    },

    async loadFolderImages() {
      if (!this.imageData.Path) return;

      // Extraire le chemin du dossier parent
      const pathParts = this.imageData.Path.split("/");
      pathParts.pop(); // Enlever le nom du fichier
      const folderPath = pathParts.join("/");

      try {
        // Inclure le token si connecte pour obtenir des miniatures de meilleure qualite
        const config = {
          params: { path: folderPath },
        };
        if (this.token) {
          config.headers = { Authorization: `Bearer ${this.token}` };
        }

        const response = await axios.get(`${FILES_API_URL}/files/`, config);

        // Filtrer uniquement les images (pas les dossiers)
        const PHOTO_EXTENSIONS = [".png", ".jpg", ".jpeg", ".gif", ".webp"];
        this.folderImages = (response.data || []).filter(item => {
          if (item.isDirectory) return false;
          const name = item.Name || "";
          const dotIndex = name.lastIndexOf(".");
          if (dotIndex === -1) return false;
          const ext = name.slice(dotIndex).toLowerCase();
          return PHOTO_EXTENSIONS.includes(ext);
        });

        // Trouver l'index de l'image actuelle
        this.currentImageIndex = this.folderImages.findIndex(
          img => img.Path === this.imageData.Path
        );
      } catch (error) {
        console.error("Erreur lors du chargement des images du dossier:", error);
        this.folderImages = [];
      }
    },

    goToPreviousImage() {
      if (this.hasPreviousImage) {
        const prevImage = this.folderImages[this.currentImageIndex - 1];
        this.$router.push({ path: "/image", query: { path: prevImage.Path } });
      }
    },

    goToNextImage() {
      if (this.hasNextImage) {
        const nextImage = this.folderImages[this.currentImageIndex + 1];
        this.$router.push({ path: "/image", query: { path: nextImage.Path } });
      }
    },

    goBackToFolder() {
      if (!this.imageData.Path) {
        this.$router.push("/images");
        return;
      }
      const pathParts = this.imageData.Path.split("/");
      pathParts.pop();
      const folderPath = pathParts.join("/");
      this.$router.push({ name: "Images", params: { pathMatch: folderPath } });
    },

    // Swipe handlers (mobile)
    handleSwipeStart(event) {
      this.swipeStartX = event.touches[0].clientX;
      this.isSwiping = true;
    },

    handleSwipeMove(event) {
      if (!this.isSwiping || this.swipeStartX === null) return;

      const currentX = event.touches[0].clientX;
      const diff = currentX - this.swipeStartX;

      // Limiter le déplacement
      const maxOffset = 150;
      this.swipeOffset = Math.max(-maxOffset, Math.min(maxOffset, diff));
    },

    handleSwipeEnd() {
      if (!this.isSwiping) return;

      const threshold = 80;

      if (this.swipeOffset > threshold && this.hasPreviousImage) {
        this.goToPreviousImage();
      } else if (this.swipeOffset < -threshold && this.hasNextImage) {
        this.goToNextImage();
      }

      // Reset
      this.swipeOffset = 0;
      this.swipeStartX = null;
      this.isSwiping = false;
    },

    // Keyboard navigation
    handleKeydown(event) {
      if (event.key === "ArrowLeft") {
        this.goToPreviousImage();
      } else if (event.key === "ArrowRight") {
        this.goToNextImage();
      } else if (event.key === "Escape") {
        this.goBackToFolder();
      }
    },

    async loadImagePage() {
      // Reset state
      this.recfacData = null;
      this.canvasImage = null;

      await this.fetchImageData();
      await this.verifyAdmin();

      // Fetch recfac data after image data is loaded
      if (this.imageData.Path) {
        await this.fetchRecfacData();

        // Wait for recfac data and draw faces on canvas
        this.$nextTick(() => {
          // Initialize faces with additional properties for UI
          if (this.recfacData && this.recfacData.faces) {
            this.recfacData.faces = this.recfacData.faces.map(face => ({
              ...face,
              newTagName: "",
              autoTagSimilar: true,
              isTagging: false,
              useExisting: true,
            }));
            this.drawFacesOnCanvas();
          }
        });
      }
    },

    async fetchRecfacData() {
      if (!this.token || !this.imageData.Path) {
        return;
      }

      try {
        const response = await axios.get(`${RECFAC_API_URL}/recfac/image-details/`, {
          params: { path: this.imageData.Path },
          headers: { Authorization: `Bearer ${this.token}` },
        });
        this.recfacData = response.data;
      } catch (error) {
        console.error("Erreur lors de la récupération des données recfac :", error);
        // Don't show error to user, recfac data is optional
      }
    },

    async verifyAdmin() {
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
        console.error("Erreur lors de la vérification admin :", error);
        this.isAdmin = false;
      }
    },

    async scanImage() {
      if (!this.token || !this.isAdmin || !this.imageData.Path) {
        return;
      }

      this.isScanning = true;
      try {
        const response = await axios.post(
          `${RECFAC_API_URL}/recfac/scan-image/`,
          { path: this.imageData.Path },
          { headers: { Authorization: `Bearer ${this.token}` } }
        );

        // Refresh recfac data after successful scan
        if (response.status === 200) {
          await this.fetchRecfacData();
        }
      } catch (error) {
        console.error("Erreur lors du scan de l'image :", error);
        alert("Erreur lors du scan de l'image");
      } finally {
        this.isScanning = false;
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

    formatDate(dateString) {
      if (!dateString) return "N/A";
      const date = new Date(dateString);
      return date.toLocaleString("fr-FR", {
        year: "numeric",
        month: "long",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
    },

    // Face tagging methods
    drawFacesOnCanvas() {
      if (!this.recfacData || !this.recfacData.faces || !this.$refs.facesCanvas) {
        return;
      }

      const canvas = this.$refs.facesCanvas;
      const ctx = canvas.getContext("2d");

      // Load image
      const img = new Image();
      img.crossOrigin = "anonymous";
      img.src = this.imageData.Img;

      img.onload = () => {
        this.canvasImage = img;

        // Set canvas size to match image
        canvas.width = img.width;
        canvas.height = img.height;

        // Draw image
        ctx.drawImage(img, 0, 0);

        // Draw all faces
        this.recfacData.faces.forEach((face, index) => {
          this.drawFaceBox(ctx, face, index, false);
        });

        // Generer les crops des visages
        this.$nextTick(() => {
          this.generateFaceCrops();
        });
      };
    },

    // Genere les aperçus (crops) de chaque visage
    generateFaceCrops() {
      if (!this.canvasImage || !this.recfacData || !this.recfacData.faces) {
        return;
      }

      this.recfacData.faces.forEach((face, index) => {
        const refName = "faceCrop" + index;
        const canvasRefs = this.$refs[refName];
        if (!canvasRefs || canvasRefs.length === 0) return;

        const cropCanvas = canvasRefs[0];
        const ctx = cropCanvas.getContext("2d");

        const [x1, y1, x2, y2] = face.bbox;

        // Ajouter un peu de marge autour du visage (20%)
        const width = x2 - x1;
        const height = y2 - y1;
        const margin = 0.2;

        const cropX = Math.max(0, x1 - width * margin);
        const cropY = Math.max(0, y1 - height * margin);
        const cropWidth = Math.min(this.canvasImage.width - cropX, width * (1 + margin * 2));
        const cropHeight = Math.min(this.canvasImage.height - cropY, height * (1 + margin * 2));

        // Taille du canvas de sortie (carre 80x80)
        const outputSize = 80;
        cropCanvas.width = outputSize;
        cropCanvas.height = outputSize;

        // Calculer le ratio pour garder les proportions
        const scale = Math.min(outputSize / cropWidth, outputSize / cropHeight);
        const scaledWidth = cropWidth * scale;
        const scaledHeight = cropHeight * scale;
        const offsetX = (outputSize - scaledWidth) / 2;
        const offsetY = (outputSize - scaledHeight) / 2;

        // Fond gris
        ctx.fillStyle = "#f0f0f0";
        ctx.fillRect(0, 0, outputSize, outputSize);

        // Dessiner le crop du visage
        ctx.drawImage(
          this.canvasImage,
          cropX, cropY, cropWidth, cropHeight,
          offsetX, offsetY, scaledWidth, scaledHeight
        );
      });
    },

    // Palette de couleurs pastel douces pour les visages
    getFaceColor(index) {
      const colors = [
        "#7eb8a2", // Vert sauge
        "#b8a07e", // Taupe doux
        "#8fa7b8", // Bleu gris
        "#b89e8f", // Beige rose
        "#9ab88f", // Vert olive clair
        "#a78fb8", // Lavande
        "#b8a58f", // Sable
        "#8fb8b3", // Vert d'eau
        "#b88f9a", // Vieux rose
        "#8f9eb8", // Bleu ardoise
        "#b8b08f", // Kaki clair
        "#9b8fb8", // Mauve doux
      ];
      return colors[index % colors.length];
    },

    drawFaceBox(ctx, face, index, isHovered) {
      const [x1, y1, x2, y2] = face.bbox;
      const canvas = this.$refs.facesCanvas;

      // Calculer les tailles proportionnelles a l'image
      const imageSize = Math.max(canvas.width, canvas.height);
      const scaleFactor = imageSize / 800; // Base: 800px

      // Epaisseur du trait proportionnelle (min 2, max 8)
      const baseLineWidth = Math.max(2, Math.min(8, Math.round(3 * scaleFactor)));
      const lineWidth = isHovered ? baseLineWidth + 2 : baseLineWidth;

      // Couleur du visage (ou couleur hover si survole)
      const faceColor = isHovered ? "#6b8e7a" : this.getFaceColor(index);

      // Draw rectangle
      ctx.strokeStyle = faceColor;
      ctx.lineWidth = lineWidth;
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);

      // Afficher le nom seulement si la personne est taggee
      if (face.person_name) {
        const baseFontSize = Math.max(14, Math.min(48, Math.round(18 * scaleFactor)));
        const fontSize = isHovered ? baseFontSize + 4 : baseFontSize;
        const padding = Math.round(6 * scaleFactor);

        // Ombre pour meilleure lisibilite
        ctx.shadowColor = "rgba(0, 0, 0, 0.3)";
        ctx.shadowBlur = 3;
        ctx.shadowOffsetX = 1;
        ctx.shadowOffsetY = 1;

        ctx.font = `bold ${fontSize}px Arial`;
        const textWidth = ctx.measureText(face.person_name).width;
        const labelHeight = fontSize + padding * 2;

        // Fond du label (couleur du visage avec transparence)
        ctx.fillStyle = faceColor;
        ctx.fillRect(x1, y1 - labelHeight - 2, textWidth + padding * 2, labelHeight);

        // Reset shadow pour le texte
        ctx.shadowColor = "transparent";
        ctx.shadowBlur = 0;
        ctx.shadowOffsetX = 0;
        ctx.shadowOffsetY = 0;

        // Texte
        const textColor = this.getContrastColor(faceColor);
        ctx.fillStyle = textColor;
        ctx.fillText(face.person_name, x1 + padding, y1 - padding - 4);
      }
    },

    // Calcule si le texte doit etre noir ou blanc selon la couleur de fond
    getContrastColor(hexColor) {
      const hex = hexColor.replace("#", "");
      const r = parseInt(hex.substr(0, 2), 16);
      const g = parseInt(hex.substr(2, 2), 16);
      const b = parseInt(hex.substr(4, 2), 16);
      // Formule de luminosite
      const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
      return luminance > 0.5 ? "#000000" : "#ffffff";
    },

    onCanvasHover(event) {
      if (!this.recfacData || !this.recfacData.faces || !this.$refs.facesCanvas) {
        return;
      }

      const canvas = this.$refs.facesCanvas;
      const rect = canvas.getBoundingClientRect();
      const scaleX = canvas.width / rect.width;
      const scaleY = canvas.height / rect.height;

      const mouseX = (event.clientX - rect.left) * scaleX;
      const mouseY = (event.clientY - rect.top) * scaleY;

      // Find which face is being hovered
      let hoveredIndex = null;
      for (let i = 0; i < this.recfacData.faces.length; i++) {
        const [x1, y1, x2, y2] = this.recfacData.faces[i].bbox;
        if (mouseX >= x1 && mouseX <= x2 && mouseY >= y1 && mouseY <= y2) {
          hoveredIndex = i;
          break;
        }
      }

      if (hoveredIndex !== this.hoveredFaceIndex) {
        this.hoveredFaceIndex = hoveredIndex;
        this.redrawCanvas();
      }
    },

    onCanvasLeave() {
      if (this.hoveredFaceIndex !== null) {
        this.hoveredFaceIndex = null;
        this.redrawCanvas();
      }
    },

    redrawCanvas() {
      if (!this.canvasImage || !this.$refs.facesCanvas) {
        return;
      }

      const canvas = this.$refs.facesCanvas;
      const ctx = canvas.getContext("2d");

      // Redraw image
      ctx.drawImage(this.canvasImage, 0, 0);

      // Redraw all faces
      this.recfacData.faces.forEach((face, index) => {
        const isHovered = index === this.hoveredFaceIndex;
        this.drawFaceBox(ctx, face, index, isHovered);
      });
    },

    onFaceTagModeChange(face) {
      // Charger la liste des personnes si elle n'est pas déjà chargée
      if (face.useExisting && this.personsList.length === 0) {
        this.loadPersonsList();
      }
      // Réinitialiser le nom de personne lors du changement de mode
      face.newTagName = "";
    },

    async loadPersonsList() {
      if (!this.token) return;

      try {
        const response = await axios.get(`${RECFAC_API_URL}/recfac/persons/`, {
          headers: { Authorization: `Bearer ${this.token}` },
        });
        this.personsList = response.data.persons || [];
      } catch (error) {
        console.error("Erreur lors du chargement des personnes:", error);
      }
    },

    async tagFace(face) {
      if (!face.newTagName || !this.token || !this.isAdmin) {
        return;
      }

      face.isTagging = true;

      try {
        const endpoint = face.autoTagSimilar
          ? `${RECFAC_API_URL}/recfac/face/tag-with-similarity/`
          : `${RECFAC_API_URL}/recfac/face/tag/`;

        const body = {
          face_id: face.face_id,
          person_name: face.newTagName.trim(),
        };

        if (face.autoTagSimilar) {
          body.similarity_threshold = 0.6;
        }

        const response = await axios.post(endpoint, body, {
          headers: { Authorization: `Bearer ${this.token}` },
        });

        // Update the face with the new tag
        face.person_name = face.newTagName.trim();

        // Si c'était une nouvelle personne, recharger la liste
        if (!face.useExisting && this.personsList.length > 0) {
          await this.loadPersonsList();
        }

        face.newTagName = "";

        // Show success message
        if (face.autoTagSimilar && response.data.similar_faces_tagged > 0) {
          alert(
            `Tag ajouté avec succès! ${response.data.similar_faces_tagged} visage(s) similaire(s) ont aussi été taggés.`
          );
        } else {
          alert("Tag ajouté avec succès!");
        }

        // Refresh recfac data
        await this.fetchRecfacData();
        // Redraw canvas
        this.$nextTick(() => {
          this.drawFacesOnCanvas();
        });
      } catch (error) {
        console.error("Erreur lors du tagging:", error);
        alert("Erreur lors du tagging du visage");
      } finally {
        face.isTagging = false;
      }
    },
  },

  watch: {
    // Recharger les données quand la route change (navigation entre images)
    "$route.query.path": {
      handler() {
        this.loadImagePage();
      },
    },
  },

  async mounted() {
    await this.loadImagePage();

    // Ajouter l'écouteur clavier pour la navigation
    document.addEventListener("keydown", this.handleKeydown);
  },

  beforeUnmount() {
    // Nettoyer l'écouteur clavier
    document.removeEventListener("keydown", this.handleKeydown);
  },

  components: {
    NavigationBar,
    FooterSection,
  },
};
</script>

<style scoped>
.image-page-container {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.container {
  max-width: 900px;
  flex: 1;
}

/* Wrapper pour la navigation */
.image-viewer-wrapper {
  position: relative;
  display: flex;
  align-items: flex-start;
  gap: 1rem;
}

.image-card {
  flex: 1;
  overflow: hidden;
}

.image-container {
  position: relative;
  overflow: hidden;
  /* Prevent iOS native context menu on long press */
  -webkit-touch-callout: none;
  -webkit-user-select: none;
  user-select: none;
  touch-action: manipulation;
}

.card-img-top {
  max-height: 500px;
  width: 100%;
  object-fit: contain;
  user-select: none;
  transition: transform 0.1s ease-out;
  /* Prevent iOS native context menu on long press */
  -webkit-touch-callout: none;
  -webkit-user-select: none;
}

/* Boutons de navigation (PC) - positionnés par rapport à l'image */
.nav-btn {
  position: sticky;
  top: 50vh;
  z-index: 20;
  width: 3rem;
  height: 3rem;
  border-radius: 50%;
  background-color: rgba(255, 255, 255, 0.9);
  border: 1px solid #dee2e6;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

.nav-btn:hover {
  background-color: #fff;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  transform: scale(1.1);
}

.nav-btn svg {
  width: 1.5rem;
  height: 1.5rem;
  color: #333;
}

.nav-btn-left {
  margin-right: -0.5rem;
}

.nav-btn-right {
  margin-left: -0.5rem;
}

/* Indicateurs de swipe (mobile) */
.swipe-indicator {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 3rem;
  height: 3rem;
  border-radius: 50%;
  background-color: rgba(13, 110, 253, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  animation: pulse 0.3s ease-in-out;
}

.swipe-indicator svg {
  width: 1.5rem;
  height: 1.5rem;
  color: white;
}

.swipe-indicator-left {
  left: 1rem;
}

.swipe-indicator-right {
  right: 1rem;
}

@keyframes pulse {
  0% { opacity: 0; transform: translateY(-50%) scale(0.8); }
  100% { opacity: 1; transform: translateY(-50%) scale(1); }
}

/* Navigation mobile en bas */
.mobile-nav {
  padding: 0.5rem;
  background-color: #f8f9fa;
  border-radius: 0.5rem;
}

/* Section Reconnaissance Faciale collapsible */
.recfac-section {
  border: 1px solid #e9ecef;
  border-radius: 0.5rem;
  padding: 1rem;
  background-color: #f8f9fa;
}

.collapse-icon {
  width: 1.25rem;
  height: 1.25rem;
  transition: transform 0.2s ease;
  flex-shrink: 0;
}

.collapse-icon.rotated {
  transform: rotate(90deg);
}

.recfac-content {
  padding-left: 1.75rem;
}

/* Face card avec apercu */
.face-card {
  border-width: 2px;
  transition: all 0.2s ease;
}

.face-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.face-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.face-thumbnail {
  flex-shrink: 0;
  width: 80px;
  height: 80px;
  border-radius: 8px;
  overflow: hidden;
  border: 3px solid;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.face-crop-canvas {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.face-info {
  flex: 1;
  min-width: 0;
}

.face-number {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: bold;
  font-size: 0.9rem;
}

/* Responsive: ajuster les boutons sur écrans moyens */
@media (max-width: 1100px) and (min-width: 768px) {
  .nav-btn {
    background-color: rgba(255, 255, 255, 0.95);
  }
}

/* Mobile: cacher les gros boutons, utiliser le swipe */
@media (max-width: 767px) {
  .image-viewer-wrapper {
    gap: 0;
  }

  .card-img-top {
    max-height: 350px;
  }
}
</style>
