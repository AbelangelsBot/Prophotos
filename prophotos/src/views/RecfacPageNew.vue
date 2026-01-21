<template>
  <div>
    <NavigationBar :token="token" @update-token="handleTokenUpdate" />
    <div class="container mt-4">
      <h1 class="mb-4">Reconnaissance Faciale</h1>

      <!-- Tabs Navigation -->
      <ul class="nav nav-tabs mb-4" role="tablist">
        <li class="nav-item" role="presentation">
          <button
            class="nav-link"
            :class="{ active: activeTab === 'visages' }"
            @click="activeTab = 'visages'"
            type="button"
          >
            <i class="bi bi-camera"></i> Visages
          </button>
        </li>
        <li class="nav-item" role="presentation">
          <button
            class="nav-link"
            :class="{ active: activeTab === 'tags' }"
            @click="activeTab = 'tags'"
            type="button"
          >
            <i class="bi bi-tag"></i> Tags
          </button>
        </li>
        <li class="nav-item" role="presentation">
          <button
            class="nav-link"
            :class="{ active: activeTab === 'tests' }"
            @click="activeTab = 'tests'"
            type="button"
          >
            <i class="bi bi-wrench"></i> Tests
          </button>
        </li>
      </ul>

      <!-- Tab Content -->
      <div class="tab-content">

        <!-- ONGLET VISAGES -->
        <div v-if="activeTab === 'visages'" class="tab-pane">

          <!-- Health Check -->
          <div class="card mb-4">
            <div class="card-header bg-info text-white">
              <h5 class="mb-0">État du Service</h5>
            </div>
            <div class="card-body">
              <button @click="checkHealth" class="btn btn-info" :disabled="loading">
                <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
                Vérifier l'état du service
              </button>
              <div v-if="healthStatus" class="mt-3">
                <div class="alert" :class="healthStatus.ok ? 'alert-success' : 'alert-danger'">
                  <strong>Service:</strong> {{ healthStatus.service }}<br>
                  <strong>Status:</strong> {{ healthStatus.ok ? '✅ OK' : '❌ Erreur' }}<br>
                  <strong>GPU Worker:</strong> {{ healthStatus.gpu_worker_ok ? '✅ Connecté' : '❌ Non disponible' }}<br>
                  <strong>Images:</strong> {{ healthStatus.images_count }}<br>
                  <strong>Faces:</strong> {{ healthStatus.faces_count }}<br>
                  <strong>Personnes:</strong> {{ healthStatus.persons_count }}
                </div>
              </div>
            </div>
          </div>

          <!-- Scan Image -->
          <div class="card mb-4" v-if="isAdmin">
            <div class="card-header bg-primary text-white">
              <h5 class="mb-0">Scanner une Image</h5>
            </div>
            <div class="card-body">
              <div class="mb-3">
                <label class="form-label">Chemin de l'image (relatif)</label>
                <input
                  v-model="scanPath"
                  type="text"
                  class="form-control"
                  placeholder="ex: test/photo.jpg"
                >
              </div>
              <button @click="scanImage" class="btn btn-primary" :disabled="loading || !scanPath">
                <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
                Scanner l'image
              </button>
              <div v-if="scanResult" class="mt-3">
                <div class="alert alert-success">
                  <strong>Image ID:</strong> {{ scanResult.image_id }}<br>
                  <strong>Visages détectés:</strong> {{ scanResult.faces_count }}<br>
                  <strong>Date scan:</strong> {{ scanResult.scan_date }}<br>
                  <span v-if="scanResult.already_scanned" class="badge bg-warning">Déjà scannée</span>
                </div>
              </div>
            </div>
          </div>

          <!-- Search Face by Upload -->
          <div class="card mb-4" v-if="token">
            <div class="card-header bg-success text-white">
              <h5 class="mb-0">Rechercher un Visage</h5>
            </div>
            <div class="card-body">
              <div class="mb-3">
                <label class="form-label">Upload une image</label>
                <input
                  @change="onFileSelected"
                  type="file"
                  class="form-control"
                  accept="image/*"
                >
              </div>
              <div class="mb-3">
                <label class="form-label">Seuil de similarité (0-1)</label>
                <input
                  v-model.number="threshold"
                  type="number"
                  class="form-control"
                  step="0.05"
                  min="0"
                  max="1"
                >
              </div>
              <button @click="searchFaceByUpload" class="btn btn-success" :disabled="loading || !selectedFile">
                <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
                Rechercher
              </button>
              <div v-if="searchResults" class="mt-3">
                <div class="alert alert-info">
                  <strong>{{ searchResults.count }} résultat(s) trouvé(s)</strong> (seuil: {{ searchResults.threshold }})
                </div>

                <!-- Matches avec embeddings moyens des personnes -->
                <div v-if="searchResults.persons_matches && searchResults.persons_matches.length > 0" class="mb-3">
                  <h6>Correspondances avec personnes identifiées (embedding moyen):</h6>
                  <div class="row">
                    <div v-for="match in searchResults.persons_matches" :key="match.person_name" class="col-md-4 mb-3">
                      <div class="card border-success">
                        <div class="card-body">
                          <h6 class="text-success">Similarité: {{ (match.similarity * 100).toFixed(1) }}%</h6>
                          <p class="mb-1"><strong>Personne:</strong> {{ match.person_name }}</p>
                          <span class="badge bg-success">Embedding moyen</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- Résultats individuels des visages -->
                <h6>Correspondances avec visages individuels:</h6>
                <div class="row">
                  <div v-for="result in searchResults.results" :key="result.face_id" class="col-md-4 mb-3">
                    <div class="card">
                      <div class="card-body">
                        <h6>Similarité: {{ (result.similarity * 100).toFixed(1) }}%</h6>
                        <p class="mb-1"><strong>Image:</strong> {{ result.image_path }}</p>
                        <p class="mb-1"><strong>Personne:</strong> {{ result.person_name || 'Inconnue' }}</p>
                        <small class="text-muted">Face ID: {{ result.face_id.substring(0, 8) }}...</small>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Scan All Images (Admin) -->
          <div class="card mb-4" v-if="isAdmin">
            <div class="card-header bg-primary text-white">
              <h5 class="mb-0">Scanner Toutes les Images</h5>
            </div>
            <div class="card-body">
              <p class="text-muted">
                Lance le scan de toutes les images du serveur. Cette opération peut prendre plusieurs minutes.
              </p>
              <button @click="scanAllImages" class="btn btn-primary btn-lg" :disabled="loading || isScanning">
                <span v-if="isScanning" class="spinner-border spinner-border-sm me-2"></span>
                {{ isScanning ? 'Scan en cours...' : 'Démarrer le scan complet' }}
              </button>

              <!-- Progress Display -->
              <div v-if="scanProgress" class="mt-4">
                <div class="card bg-light">
                  <div class="card-body">
                    <h6>Progression du scan:</h6>
                    <div class="progress mb-3" style="height: 25px;">
                      <div
                        class="progress-bar progress-bar-striped progress-bar-animated"
                        role="progressbar"
                        :style="{width: scanProgress.percentage + '%'}"
                        :aria-valuenow="scanProgress.percentage"
                        aria-valuemin="0"
                        aria-valuemax="100"
                      >
                        {{ scanProgress.percentage }}%
                      </div>
                    </div>

                    <div class="row text-center">
                      <div class="col-md-3">
                        <strong>Traitées:</strong> {{ scanProgress.processed }}
                      </div>
                      <div class="col-md-3">
                        <strong>Total:</strong> {{ scanProgress.total }}
                      </div>
                      <div class="col-md-3">
                        <strong>Visages détectés:</strong> {{ scanProgress.total_faces }}
                      </div>
                      <div class="col-md-3">
                        <strong>Erreurs:</strong> {{ scanProgress.errors }}
                      </div>
                    </div>

                    <div v-if="scanProgress.current_image" class="mt-3">
                      <small class="text-muted">
                        En cours: {{ scanProgress.current_image }}
                      </small>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Scan Complete -->
              <div v-if="scanComplete" class="mt-3">
                <div class="alert alert-success">
                  <h5>Scan terminé!</h5>
                  <p class="mb-1"><strong>Images scannées:</strong> {{ scanComplete.images_scanned }}</p>
                  <p class="mb-1"><strong>Images déjà traitées:</strong> {{ scanComplete.images_skipped }}</p>
                  <p class="mb-1"><strong>Visages détectés:</strong> {{ scanComplete.total_faces_detected }}</p>
                  <p class="mb-1"><strong>Erreurs:</strong> {{ scanComplete.errors_count }}</p>
                  <p class="mb-0"><strong>Durée:</strong> {{ scanComplete.duration_seconds }}s</p>
                </div>
              </div>
            </div>
          </div>

        </div>
        <!-- FIN ONGLET VISAGES -->

        <!-- ONGLET TAGS -->
        <div v-if="activeTab === 'tags'" class="tab-pane">

          <!-- List Persons -->
          <div class="card mb-4">
            <div class="card-header bg-warning text-dark">
              <h5 class="mb-0">Liste des Personnes</h5>
            </div>
            <div class="card-body">
              <button @click="listPersons" class="btn btn-warning" :disabled="loading">
                <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
                Charger la liste
              </button>
              <div v-if="persons" class="mt-3">
                <div class="alert alert-info">
                  <strong>{{ persons.count }} personne(s) identifiée(s)</strong>
                </div>
                <ul class="list-group">
                  <li v-for="person in persons.persons" :key="person.name" class="list-group-item d-flex justify-content-between align-items-center">
                    {{ person.name }}
                    <span class="badge bg-primary rounded-pill">{{ person.faces_count }} visage(s)</span>
                  </li>
                </ul>
              </div>
            </div>
          </div>

          <!-- Tag Face (Admin) -->
          <div class="card mb-4" v-if="isAdmin">
            <div class="card-header bg-danger text-white">
              <h5 class="mb-0">Tagger un Visage</h5>
            </div>
            <div class="card-body">
              <div class="mb-3">
                <label class="form-label">Face ID (UUID)</label>
                <input
                  v-model="tagFaceId"
                  type="text"
                  class="form-control"
                  placeholder="ex: 123e4567-e89b-12d3-a456-426614174000"
                >
              </div>
              <div class="mb-3">
                <label class="form-label">Nom de la personne</label>
                <input
                  v-model="tagPersonName"
                  type="text"
                  class="form-control"
                  placeholder="ex: John Doe"
                >
              </div>
              <button @click="tagFace" class="btn btn-danger" :disabled="loading || !tagFaceId">
                <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
                Tagger le visage
              </button>
              <div v-if="tagResult" class="mt-3">
                <div class="alert alert-success">
                  <strong>Visage tagué avec succès !</strong><br>
                  Face ID: {{ tagResult.face_id }}<br>
                  Personne: {{ tagResult.person_name || 'Non tagué' }}
                </div>
              </div>
            </div>
          </div>

        </div>
        <!-- FIN ONGLET TAGS -->

        <!-- ONGLET TESTS -->
        <div v-if="activeTab === 'tests'" class="tab-pane">

          <!-- Test Vectorization -->
          <div class="card mb-4">
            <div class="card-header bg-secondary text-white">
              <h5 class="mb-0">Test Vectorisation</h5>
            </div>
            <div class="card-body">
              <div class="mb-3">
                <label class="form-label">Upload une image pour tester</label>
                <input
                  @change="onTestFileSelected"
                  type="file"
                  class="form-control"
                  accept="image/*"
                >
              </div>
              <button @click="testVectorize" class="btn btn-secondary" :disabled="loading || !testFile">
                <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
                Tester la vectorisation
              </button>
              <div v-if="testResult" class="mt-3">
                <div class="alert alert-info">
                  <strong>{{ testResult.faces_found }} visage(s) détecté(s)</strong><br>
                  <strong>Modèle:</strong> {{ testResult.model }}
                </div>

                <!-- Canvas pour afficher l'image avec les bounding boxes -->
                <div v-if="testResult.faces_found > 0" class="mt-3">
                  <canvas
                    ref="testCanvas"
                    class="img-fluid border"
                    style="max-width: 100%; height: auto;"
                  ></canvas>

                  <!-- Détails des visages détectés -->
                  <div class="mt-3">
                    <h6>Détails des visages:</h6>
                    <div v-for="(face, idx) in testResult.results" :key="idx" class="card mb-2">
                      <div class="card-body">
                        <p class="mb-1"><strong>Visage {{ idx + 1 }}</strong></p>
                        <p class="mb-1"><strong>Score de détection:</strong> {{ (face.det_score * 100).toFixed(1) }}%</p>
                        <p class="mb-1"><strong>Bounding Box:</strong> [{{ face.bbox.map(v => v.toFixed(1)).join(', ') }}]</p>
                        <p class="mb-1"><strong>Dimension embedding:</strong> {{ face.dim }}</p>
                        <small class="text-muted">Embedding: {{ face.embedding.slice(0, 5).map(v => v.toFixed(3)).join(', ') }}...</small>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Compare Two Faces -->
          <div class="card mb-4">
            <div class="card-header bg-dark text-white">
              <h5 class="mb-0">Comparer Deux Visages</h5>
            </div>
            <div class="card-body">
              <div class="row">
                <div class="col-md-6 mb-3">
                  <label class="form-label">Image 1</label>
                  <input
                    @change="onCompareImage1Selected"
                    type="file"
                    class="form-control"
                    accept="image/*"
                  >
                  <div v-if="compareImage1" class="mt-2">
                    <img :src="compareImage1Preview" class="img-thumbnail" style="max-height: 200px;">
                  </div>
                </div>
                <div class="col-md-6 mb-3">
                  <label class="form-label">Image 2</label>
                  <input
                    @change="onCompareImage2Selected"
                    type="file"
                    class="form-control"
                    accept="image/*"
                  >
                  <div v-if="compareImage2" class="mt-2">
                    <img :src="compareImage2Preview" class="img-thumbnail" style="max-height: 200px;">
                  </div>
                </div>
              </div>
              <button @click="compareFaces" class="btn btn-dark" :disabled="loading || !compareImage1 || !compareImage2">
                <span v-if="loading" class="spinner-border spinner-border-sm me-2"></span>
                Comparer les visages
              </button>
              <div v-if="compareResult" class="mt-3">
                <div class="alert" :class="getCompareAlertClass(compareResult.similarity)">
                  <h5>Résultat de la comparaison</h5>
                  <p class="mb-2"><strong>Similarité:</strong> {{ (compareResult.similarity * 100).toFixed(2) }}%</p>
                  <p class="mb-2"><strong>Distance:</strong> {{ compareResult.distance.toFixed(4) }}</p>
                  <p class="mb-2"><strong>Statut:</strong> {{ compareResult.match_status }}</p>
                  <hr>
                  <div class="row">
                    <div class="col-md-6">
                      <h6>Visage 1</h6>
                      <p class="mb-1">Score détection: {{ (compareResult.face1.det_score * 100).toFixed(1) }}%</p>
                      <p class="mb-1">BBox: [{{ compareResult.face1.bbox.map(v => v.toFixed(0)).join(', ') }}]</p>
                    </div>
                    <div class="col-md-6">
                      <h6>Visage 2</h6>
                      <p class="mb-1">Score détection: {{ (compareResult.face2.det_score * 100).toFixed(1) }}%</p>
                      <p class="mb-1">BBox: [{{ compareResult.face2.bbox.map(v => v.toFixed(0)).join(', ') }}]</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

        </div>
        <!-- FIN ONGLET TESTS -->

      </div>
      <!-- /tab-content -->

      <!-- Error Display -->
      <div v-if="error" class="alert alert-danger">
        <strong>Erreur:</strong> {{ error }}
      </div>
    </div>
    <FooterSection />
  </div>
</template>

<script>
import { RECFAC_API_URL } from "@/constants";
import { USERS_API_URL } from "@/constants";
import NavigationBar from "@/components/NavBar.vue";
import FooterSection from "@/components/FootSection.vue";

export default {
  name: "RecfacPage",
  components: {
    NavigationBar,
    FooterSection,
  },
  data() {
    return {
      token: localStorage.getItem("token") || null,
      isAdmin: false,
      loading: false,
      error: null,

      // Active Tab
      activeTab: 'visages',

      // Health Check
      healthStatus: null,

      // Scan Image
      scanPath: "",
      scanResult: null,

      // Search Face
      selectedFile: null,
      threshold: 0.6,
      searchResults: null,

      // List Persons
      persons: null,

      // Tag Face
      tagFaceId: "",
      tagPersonName: "",
      tagResult: null,

      // Test Vectorization
      testFile: null,
      testResult: null,

      // Compare Faces
      compareImage1: null,
      compareImage2: null,
      compareImage1Preview: null,
      compareImage2Preview: null,
      compareResult: null,

      // Scan All Images
      isScanning: false,
      scanProgress: null,
      scanComplete: null,
      eventSource: null,
    };
  },
  async created() {
    await this.verifyToken();
  },
  methods: {
    async verifyToken() {
      if (!this.token) return;

      try {
        const response = await fetch(USERS_API_URL + "/users/verify-token/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${this.token}`,
          },
        });

        if (response.ok) {
          const data = await response.json();
          this.isAdmin = data.user.admin || false;
        }
      } catch (error) {
        console.error("Erreur vérification token:", error);
      }
    },

    async checkHealth() {
      this.loading = true;
      this.error = null;
      this.healthStatus = null;

      try {
        const response = await fetch(`${RECFAC_API_URL}/recfac/check-health/`);
        if (response.ok) {
          this.healthStatus = await response.json();
        } else {
          this.error = "Erreur lors de la vérification du service";
        }
      } catch (error) {
        this.error = error.message;
      } finally {
        this.loading = false;
      }
    },

    async scanImage() {
      if (!this.token) {
        this.error = "Vous devez être connecté";
        return;
      }

      this.loading = true;
      this.error = null;
      this.scanResult = null;

      try {
        const response = await fetch(`${RECFAC_API_URL}/recfac/scan-image/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${this.token}`,
          },
          body: JSON.stringify({ path: this.scanPath }),
        });

        if (response.ok) {
          this.scanResult = await response.json();
        } else {
          const data = await response.json();
          this.error = data.error || "Erreur lors du scan";
        }
      } catch (error) {
        this.error = error.message;
      } finally {
        this.loading = false;
      }
    },

    onFileSelected(event) {
      this.selectedFile = event.target.files[0];
    },

    async searchFaceByUpload() {
      if (!this.token) {
        this.error = "Vous devez être connecté";
        return;
      }

      if (!this.selectedFile) {
        this.error = "Veuillez sélectionner une image";
        return;
      }

      this.loading = true;
      this.error = null;
      this.searchResults = null;

      try {
        const formData = new FormData();
        formData.append("image", this.selectedFile);

        const url = `${RECFAC_API_URL}/recfac/search-face/?threshold=${this.threshold}`;
        const response = await fetch(url, {
          method: "POST",
          headers: {
            Authorization: `Bearer ${this.token}`,
          },
          body: formData,
        });

        if (response.ok) {
          this.searchResults = await response.json();
        } else {
          const data = await response.json();
          this.error = data.error || "Erreur lors de la recherche";
        }
      } catch (error) {
        this.error = error.message;
      } finally {
        this.loading = false;
      }
    },

    async listPersons() {
      this.loading = true;
      this.error = null;
      this.persons = null;

      try {
        const response = await fetch(`${RECFAC_API_URL}/recfac/persons/`);
        if (response.ok) {
          this.persons = await response.json();
        } else {
          this.error = "Erreur lors du chargement des personnes";
        }
      } catch (error) {
        this.error = error.message;
      } finally {
        this.loading = false;
      }
    },

    async tagFace() {
      if (!this.token) {
        this.error = "Vous devez être connecté";
        return;
      }

      this.loading = true;
      this.error = null;
      this.tagResult = null;

      try {
        const response = await fetch(`${RECFAC_API_URL}/recfac/face/tag/`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${this.token}`,
          },
          body: JSON.stringify({
            face_id: this.tagFaceId,
            person_name: this.tagPersonName,
          }),
        });

        if (response.ok) {
          this.tagResult = await response.json();
        } else {
          const data = await response.json();
          this.error = data.error || "Erreur lors du tagging";
        }
      } catch (error) {
        this.error = error.message;
      } finally {
        this.loading = false;
      }
    },

    onTestFileSelected(event) {
      this.testFile = event.target.files[0];
      this.testResult = null;
    },

    async testVectorize() {
      if (!this.testFile) {
        this.error = "Veuillez sélectionner une image";
        return;
      }

      this.loading = true;
      this.error = null;
      this.testResult = null;

      try {
        const formData = new FormData();
        formData.append("image", this.testFile);

        const response = await fetch(`${RECFAC_API_URL}/recfac/test-vectorize/`, {
          method: "POST",
          body: formData,
        });

        if (response.ok) {
          this.testResult = await response.json();

          // Attendre le prochain tick pour que le canvas soit disponible
          this.$nextTick(() => {
            this.drawFacesOnCanvas();
          });
        } else {
          const data = await response.json();
          this.error = data.error || "Erreur lors de la vectorisation";
        }
      } catch (error) {
        this.error = error.message;
      } finally {
        this.loading = false;
      }
    },

    drawFacesOnCanvas() {
      if (!this.testResult || !this.testResult.results || this.testResult.results.length === 0) {
        return;
      }

      const canvas = this.$refs.testCanvas;
      if (!canvas) return;

      const ctx = canvas.getContext("2d");
      const img = new Image();

      img.onload = () => {
        // Définir la taille du canvas
        canvas.width = img.width;
        canvas.height = img.height;

        // Dessiner l'image
        ctx.drawImage(img, 0, 0);

        // Dessiner les bounding boxes
        this.testResult.results.forEach((face, idx) => {
          const [x1, y1, x2, y2] = face.bbox;
          const width = x2 - x1;
          const height = y2 - y1;

          // Dessiner le rectangle
          ctx.strokeStyle = "#00ff00";
          ctx.lineWidth = 3;
          ctx.strokeRect(x1, y1, width, height);

          // Dessiner le label
          ctx.fillStyle = "#00ff00";
          ctx.font = "16px Arial";
          const label = `Face ${idx + 1} (${(face.det_score * 100).toFixed(1)}%)`;
          const textWidth = ctx.measureText(label).width;

          // Fond pour le texte
          ctx.fillStyle = "rgba(0, 255, 0, 0.7)";
          ctx.fillRect(x1, y1 - 22, textWidth + 8, 22);

          // Texte
          ctx.fillStyle = "#000";
          ctx.fillText(label, x1 + 4, y1 - 6);
        });
      };

      // Charger l'image depuis le fichier uploadé
      img.src = URL.createObjectURL(this.testFile);
    },

    onCompareImage1Selected(event) {
      const file = event.target.files[0];
      if (file) {
        this.compareImage1 = file;
        this.compareImage1Preview = URL.createObjectURL(file);
        this.compareResult = null;
      }
    },

    onCompareImage2Selected(event) {
      const file = event.target.files[0];
      if (file) {
        this.compareImage2 = file;
        this.compareImage2Preview = URL.createObjectURL(file);
        this.compareResult = null;
      }
    },

    async compareFaces() {
      if (!this.compareImage1 || !this.compareImage2) {
        this.error = "Veuillez sélectionner deux images";
        return;
      }

      this.loading = true;
      this.error = null;
      this.compareResult = null;

      try {
        const formData = new FormData();
        formData.append("image1", this.compareImage1);
        formData.append("image2", this.compareImage2);

        const response = await fetch(`${RECFAC_API_URL}/recfac/test-compare-faces/`, {
          method: "POST",
          body: formData,
        });

        if (response.ok) {
          this.compareResult = await response.json();
        } else {
          const data = await response.json();
          this.error = data.error || "Erreur lors de la comparaison";
        }
      } catch (error) {
        this.error = error.message;
      } finally {
        this.loading = false;
      }
    },

    getCompareAlertClass(similarity) {
      if (similarity >= 0.6) {
        return "alert-success";
      } else if (similarity >= 0.4) {
        return "alert-warning";
      } else {
        return "alert-danger";
      }
    },

    handleTokenUpdate(newToken) {
      this.token = newToken;
      if (newToken) {
        localStorage.setItem("token", newToken);
        this.verifyToken();
      } else {
        localStorage.removeItem("token");
        this.isAdmin = false;
      }
    },

    async scanAllImages() {
      if (!this.token) {
        this.error = "Vous devez être connecté";
        return;
      }

      if (!this.isAdmin) {
        this.error = "Accès réservé aux administrateurs";
        return;
      }

      this.isScanning = true;
      this.error = null;
      this.scanProgress = null;
      this.scanComplete = null;

      try {
        // Create EventSource for Server-Sent Events
        const url = `${RECFAC_API_URL}/recfac/scan-all-images/?token=${encodeURIComponent(this.token)}`;
        this.eventSource = new EventSource(url);

        this.eventSource.addEventListener("progress", (event) => {
          try {
            const data = JSON.parse(event.data);
            this.scanProgress = {
              processed: data.processed,
              total: data.total,
              total_faces: data.total_faces,
              errors: data.errors,
              percentage: Math.round((data.processed / data.total) * 100),
              current_image: data.current_image || null,
            };
          } catch (error) {
            console.error("Error parsing progress:", error);
          }
        });

        this.eventSource.addEventListener("complete", (event) => {
          try {
            const data = JSON.parse(event.data);
            this.scanComplete = data;
            this.isScanning = false;
            if (this.eventSource) {
              this.eventSource.close();
              this.eventSource = null;
            }
          } catch (error) {
            console.error("Error parsing complete:", error);
            this.isScanning = false;
          }
        });

        this.eventSource.addEventListener("error", () => {
          this.error = "Erreur de connexion au serveur";
          this.isScanning = false;
          if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
          }
        });

      } catch (error) {
        this.error = error.message;
        this.isScanning = false;
      }
    },
  },

  beforeUnmount() {
    // Clean up EventSource if component is destroyed
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  },
};
</script>

<style scoped>
.cursor-pointer {
  cursor: pointer;
}

.card {
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.card-header h5 {
  margin: 0;
}
</style>
