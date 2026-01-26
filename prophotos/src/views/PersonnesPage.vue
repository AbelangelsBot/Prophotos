<template>
  <div class="personnes-page">
    <NavigationBar :token="token" @update-token="handleTokenUpdate" />

    <div class="page-layout">
      <!-- Sidebar avec liste des personnes -->
      <aside class="persons-sidebar" :class="{ 'sidebar-collapsed': sidebarCollapsed }">
        <div class="sidebar-header">
          <h5 class="mb-0">Personnes</h5>
          <button class="btn-collapse d-md-none" @click="sidebarCollapsed = !sidebarCollapsed">
            <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline v-if="sidebarCollapsed" points="9 18 15 12 9 6"></polyline>
              <polyline v-else points="15 18 9 12 15 6"></polyline>
            </svg>
          </button>
        </div>

        <!-- Search input with tags -->
        <div class="sidebar-search">
          <div class="search-tags-container" @click="focusSearchInput">
            <!-- Selected persons tags -->
            <span
              v-for="name in selectedPersons"
              :key="name"
              class="search-tag"
            >
              {{ name }}
              <button class="search-tag-remove" @click.stop="removePersonFromSelection(name)">×</button>
            </span>
            <!-- Search input -->
            <input
              ref="searchInput"
              v-model="searchQuery"
              type="text"
              class="search-input-inline"
              :placeholder="selectedPersons.length === 0 ? 'Rechercher une personne...' : ''"
              @input="onSearchInput"
              @focus="showSuggestions = true"
              @keydown.backspace="onBackspace"
              @keydown.enter="onEnterKey"
              @keydown.escape="closeSuggestions"
              @keydown.down.prevent="navigateSuggestions(1)"
              @keydown.up.prevent="navigateSuggestions(-1)"
            />
          </div>

          <!-- Suggestions dropdown -->
          <div v-if="showSuggestions && filteredSuggestions.length > 0" class="suggestions-dropdown">
            <button
              v-for="(person, index) in filteredSuggestions"
              :key="person.name"
              class="suggestion-item"
              :class="{ 'suggestion-highlighted': index === highlightedIndex }"
              @click="addPersonToSelection(person.name)"
              @mouseenter="highlightedIndex = index"
            >
              <div class="suggestion-avatar">
                <span>{{ getInitials(person.name) }}</span>
              </div>
              <div class="suggestion-info">
                <span class="suggestion-name">{{ person.name }}</span>
                <span class="suggestion-count">{{ person.faces_count }} photo(s)</span>
              </div>
              <span v-if="isPersonSelected(person.name)" class="suggestion-check">✓</span>
            </button>
          </div>
        </div>

        <div class="sidebar-content">
          <!-- Loading -->
          <div v-if="loadingPersons" class="text-center py-4">
            <div class="spinner-border spinner-border-sm text-primary" role="status"></div>
            <p class="small text-muted mt-2 mb-0">Chargement...</p>
          </div>

          <!-- Empty state -->
          <div v-else-if="persons.length === 0" class="empty-state">
            <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path>
              <circle cx="9" cy="7" r="4"></circle>
              <path d="M23 21v-2a4 4 0 0 0-3-3.87"></path>
              <path d="M16 3.13a4 4 0 0 1 0 7.75"></path>
            </svg>
            <p class="text-muted small mt-2">Aucune personne identifiee</p>
            <p class="text-muted small">Scannez des photos pour detecter des visages</p>
          </div>

          <!-- Persons list -->
          <div v-else class="persons-list">
            <button
              v-for="person in persons"
              :key="person.name"
              class="person-item"
              :class="{ 'active': isPersonSelected(person.name) }"
              @click="togglePersonInSelection(person.name)"
            >
              <div class="person-checkbox">
                <input
                  type="checkbox"
                  :checked="isPersonSelected(person.name)"
                  @click.stop="togglePersonInSelection(person.name)"
                />
              </div>
              <div class="person-avatar">
                <span>{{ getInitials(person.name) }}</span>
              </div>
              <div class="person-info">
                <span class="person-name">{{ person.name }}</span>
                <span class="person-count">{{ person.faces_count }} photo(s)</span>
              </div>
            </button>
          </div>
        </div>

        <!-- Stats & Selection info -->
        <div class="sidebar-footer" v-if="persons.length > 0">
          <div v-if="selectedPersons.length > 0" class="selection-info">
            <span class="badge bg-primary me-2">{{ selectedPersons.length }} selectionnee(s)</span>
            <button class="btn btn-sm btn-link p-0" @click="clearPersonSelection">Effacer</button>
          </div>
          <small class="text-muted d-block mt-1">
            {{ persons.length }} personne(s) -
            {{ totalFaces }} visage(s)
          </small>
        </div>
      </aside>

      <!-- Main content -->
      <main class="main-content">
        <!-- No selection state -->
        <div v-if="selectedPersons.length === 0" class="no-selection">
          <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="11" cy="11" r="8"></circle>
            <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
          </svg>
          <h4 class="mt-3">Recherche par personne</h4>
          <p class="text-muted">Tapez un nom ou cliquez sur une personne pour la selectionner</p>
          <p class="text-muted small">Selection multiple supportee</p>

          <!-- Quick stats -->
          <div class="quick-stats mt-4" v-if="persons.length > 0">
            <div class="stat-card">
              <span class="stat-value">{{ persons.length }}</span>
              <span class="stat-label">Personnes</span>
            </div>
            <div class="stat-card">
              <span class="stat-value">{{ totalFaces }}</span>
              <span class="stat-label">Visages</span>
            </div>
          </div>
        </div>

        <!-- Loading results -->
        <div v-else-if="loadingResults" class="loading-results">
          <div class="spinner-border text-primary" role="status"></div>
          <p class="mt-3 text-muted">Chargement des photos...</p>
        </div>

        <!-- Results -->
        <div v-else class="results-container">
          <!-- Results header -->
          <div class="results-header">
            <div class="results-info">
              <h4 class="mb-1">
                <span v-if="selectedPersons.length === 1">{{ selectedPersons[0] }}</span>
                <span v-else>{{ selectedPersons.length }} personnes selectionnees</span>
              </h4>
              <p class="text-muted mb-0">{{ searchResults.length }} photo(s) trouvee(s)</p>
            </div>
            <div class="results-actions">
              <!-- Mode toggle (only for multiple selection) -->
              <div v-if="selectedPersons.length > 1" class="search-mode-toggle me-2">
                <div class="btn-group btn-group-sm" role="group">
                  <button
                    type="button"
                    class="btn"
                    :class="searchMode === 'union' ? 'btn-primary' : 'btn-outline-secondary'"
                    @click="setSearchMode('union')"
                    title="Photos avec AU MOINS UNE des personnes"
                  >
                    OU
                  </button>
                  <button
                    type="button"
                    class="btn"
                    :class="searchMode === 'intersection' ? 'btn-primary' : 'btn-outline-secondary'"
                    @click="setSearchMode('intersection')"
                    title="Photos avec TOUTES les personnes"
                  >
                    ET
                  </button>
                </div>
              </div>
              <select v-model="sortBy" class="form-select form-select-sm" style="width: auto;">
                <option value="default">Ordre par defaut</option>
                <option value="name-asc">Nom A-Z</option>
                <option value="name-desc">Nom Z-A</option>
              </select>
              <button class="btn btn-outline-secondary btn-sm" @click="clearPersonSelection">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
                Fermer
              </button>
            </div>
          </div>

          <!-- Empty results -->
          <div v-if="searchResults.length === 0" class="empty-results">
            <p class="text-muted">
              <span v-if="searchMode === 'intersection' && selectedPersons.length > 1">
                Aucune photo ne contient toutes ces personnes ensemble
              </span>
              <span v-else>
                Aucune photo trouvee
              </span>
            </p>
          </div>

          <!-- Selection Actions Bar -->
          <div v-if="selectedPhotos.length > 0" class="selection-bar bg-primary text-white p-3 mb-3 rounded d-flex justify-content-between align-items-center">
            <div>
              <strong>{{ selectedPhotos.length }}</strong> / {{ sortedResults.length }} photo(s) selectionnee(s)
              <button @click="selectAllPhotos" class="btn btn-sm btn-light ms-2" v-if="selectedPhotos.length < sortedResults.length">
                Tout selectionner
              </button>
              <button @click="clearPhotoSelection" class="btn btn-sm btn-outline-light ms-2">
                Annuler
              </button>
            </div>
            <div class="d-flex gap-2">
              <button
                v-if="token"
                @click="downloadSelected"
                class="btn btn-sm btn-light"
                :disabled="isProcessingSelection"
              >
                Telecharger
              </button>
              <button
                v-if="token && isAdmin"
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

          <!-- Photos grid -->
          <div v-if="searchResults.length > 0" class="photos-grid">
            <div
              v-for="(result, index) in sortedResults"
              :key="result.path || index"
              class="photo-card"
              :class="{ 'photo-selected': isPhotoSelected(result) }"
              @click="openImage(result.path)"
              @contextmenu.prevent="showContextMenu($event, result)"
              @touchstart="handleTouchStart($event, result)"
              @touchend="handleTouchEnd"
              @touchmove="handleTouchMove"
            >
              <!-- Selection zone -->
              <div
                class="selection-zone"
                v-if="token"
                @click.stop="togglePhotoSelection(result)"
              >
                <div
                  class="selection-indicator"
                  :class="{ 'is-selected': isPhotoSelected(result) }"
                >
                  <svg v-if="isPhotoSelected(result)" class="checkmark" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
                    <polyline points="20 6 9 17 4 12"></polyline>
                  </svg>
                </div>
              </div>

              <div class="photo-wrapper">
                <img
                  v-if="result.img"
                  :src="result.img"
                  :alt="result.name"
                  class="photo-image"
                  loading="lazy"
                />
                <div v-else class="photo-placeholder">
                  <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
                    <circle cx="8.5" cy="8.5" r="1.5"></circle>
                    <polyline points="21 15 16 10 5 21"></polyline>
                  </svg>
                </div>
                <div class="photo-overlay">
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="11" cy="11" r="8"></circle>
                    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                    <line x1="11" y1="8" x2="11" y2="14"></line>
                    <line x1="8" y1="11" x2="14" y2="11"></line>
                  </svg>
                </div>
              </div>
              <div class="photo-info">
                <span class="photo-name" :title="result.name">{{ result.name }}</span>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>

    <!-- Context Menu -->
    <div
      v-if="contextMenu.show"
      class="context-menu"
      :style="{ top: contextMenu.y + 'px', left: contextMenu.x + 'px' }"
      @click.stop
    >
      <ul class="list-unstyled mb-0">
        <li v-if="contextMenu.item">
          <a href="#" @click.prevent="openImage(contextMenu.item.path); hideContextMenu()">
            Voir l'image
          </a>
        </li>
        <li v-if="contextMenu.item && token">
          <a href="#" @click.prevent="downloadImage(contextMenu.item.path, contextMenu.item.name); hideContextMenu()">
            Telecharger
          </a>
        </li>
        <li v-if="contextMenu.item && !isPhotoSelected(contextMenu.item) && token">
          <a href="#" @click.prevent="togglePhotoSelection(contextMenu.item); hideContextMenu()">
            Selectionner
          </a>
        </li>
        <li v-if="contextMenu.item && isPhotoSelected(contextMenu.item) && token">
          <a href="#" @click.prevent="togglePhotoSelection(contextMenu.item); hideContextMenu()">
            Deselectionner
          </a>
        </li>
        <li v-if="token && isAdmin && contextMenu.item" class="separator">
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

    <FooterSection />
  </div>
</template>

<script>
import NavigationBar from "@/components/NavBar.vue";
import FooterSection from "@/components/FootSection.vue";
import axios from "axios";
import { FILES_API_URL, RECFAC_API_URL, USERS_API_URL } from "@/constants";

export default {
  name: "PersonnesPage",
  components: {
    NavigationBar,
    FooterSection,
  },
  data() {
    return {
      token: localStorage.getItem("token") || null,
      persons: [],
      loadingPersons: false,
      selectedPersons: [],
      searchResults: [],
      loadingResults: false,
      sortBy: "default",
      sidebarCollapsed: false,
      searchQuery: "",
      searchMode: "union",
      showSuggestions: false,
      highlightedIndex: -1,
      // Admin
      isAdmin: false,
      // Photo selection
      selectedPhotos: [],
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
    };
  },
  computed: {
    totalFaces() {
      return this.persons.reduce((sum, p) => sum + p.faces_count, 0);
    },
    filteredSuggestions() {
      if (!this.searchQuery) {
        return [];
      }
      const query = this.searchQuery.toLowerCase();
      return this.persons.filter(p =>
        p.name.toLowerCase().includes(query) && !this.isPersonSelected(p.name)
      ).slice(0, 8); // Limite à 8 suggestions
    },
    sortedResults() {
      if (this.sortBy === "default") {
        return this.searchResults;
      }

      const sorted = [...this.searchResults];
      if (this.sortBy === "name-asc") {
        sorted.sort((a, b) => (a.name || "").localeCompare(b.name || ""));
      } else if (this.sortBy === "name-desc") {
        sorted.sort((a, b) => (b.name || "").localeCompare(a.name || ""));
      }
      return sorted;
    },
    hasSelectedPhotos() {
      return this.selectedPhotos.length > 0;
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
    "$route.query.person"(newPerson) {
      if (newPerson && !this.isPersonSelected(newPerson)) {
        this.selectedPersons = [newPerson];
        this.loadPersonsPhotos();
      }
    },
  },
  methods: {
    handleTokenUpdate(newToken) {
      this.token = newToken;
      if (newToken) {
        this.loadPersons();
        this.determineAdmin();
      } else {
        this.persons = [];
        this.selectedPersons = [];
        this.searchResults = [];
        this.isAdmin = false;
      }
    },
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
    getInitials(name) {
      if (!name) return "?";
      const parts = name.split(" ");
      if (parts.length >= 2) {
        return (parts[0][0] + parts[1][0]).toUpperCase();
      }
      return name.slice(0, 2).toUpperCase();
    },
    isPersonSelected(name) {
      return this.selectedPersons.includes(name);
    },
    async loadPersons() {
      if (!this.token) return;

      this.loadingPersons = true;
      try {
        const response = await axios.get(`${RECFAC_API_URL}/recfac/persons/`, {
          headers: { Authorization: `Bearer ${this.token}` },
        });
        this.persons = response.data.persons || [];
      } catch (error) {
        console.error("Error loading persons:", error);
        this.persons = [];
      } finally {
        this.loadingPersons = false;
      }
    },
    focusSearchInput() {
      this.$refs.searchInput?.focus();
    },
    onSearchInput() {
      this.showSuggestions = true;
      this.highlightedIndex = -1;
    },
    closeSuggestions() {
      this.showSuggestions = false;
      this.highlightedIndex = -1;
    },
    navigateSuggestions(direction) {
      if (!this.showSuggestions || this.filteredSuggestions.length === 0) return;

      this.highlightedIndex += direction;

      if (this.highlightedIndex < 0) {
        this.highlightedIndex = this.filteredSuggestions.length - 1;
      } else if (this.highlightedIndex >= this.filteredSuggestions.length) {
        this.highlightedIndex = 0;
      }
    },
    onEnterKey() {
      if (this.highlightedIndex >= 0 && this.highlightedIndex < this.filteredSuggestions.length) {
        this.addPersonToSelection(this.filteredSuggestions[this.highlightedIndex].name);
      } else if (this.filteredSuggestions.length === 1) {
        this.addPersonToSelection(this.filteredSuggestions[0].name);
      }
    },
    onBackspace() {
      // Si le champ est vide et qu'on appuie sur backspace, supprimer le dernier tag
      if (this.searchQuery === "" && this.selectedPersons.length > 0) {
        this.removePersonFromSelection(this.selectedPersons[this.selectedPersons.length - 1]);
      }
    },
    addPersonToSelection(personName) {
      if (!this.isPersonSelected(personName)) {
        this.selectedPersons = [...this.selectedPersons, personName];
        this.loadPersonsPhotos();
      }
      this.searchQuery = "";
      this.showSuggestions = false;
      this.highlightedIndex = -1;
      this.$refs.searchInput?.focus();
    },
    removePersonFromSelection(personName) {
      this.selectedPersons = this.selectedPersons.filter(n => n !== personName);
      if (this.selectedPersons.length > 0) {
        this.loadPersonsPhotos();
      } else {
        this.searchResults = [];
      }
    },
    togglePersonInSelection(personName) {
      if (this.isPersonSelected(personName)) {
        this.removePersonFromSelection(personName);
      } else {
        this.addPersonToSelection(personName);
      }
    },
    clearPersonSelection() {
      this.selectedPersons = [];
      this.searchResults = [];
      this.searchQuery = "";
    },
    setSearchMode(mode) {
      if (this.searchMode !== mode) {
        this.searchMode = mode;
        if (this.selectedPersons.length > 1) {
          this.loadPersonsPhotos();
        }
      }
    },
    async loadPersonsPhotos() {
      if (this.selectedPersons.length === 0) {
        this.searchResults = [];
        return;
      }

      this.loadingResults = true;
      this.searchResults = [];
      this.sidebarCollapsed = true; // Collapse on mobile

      try {
        let imagePaths = [];

        if (this.selectedPersons.length === 1) {
          const facesResponse = await axios.get(`${RECFAC_API_URL}/recfac/person/faces/`, {
            params: { name: this.selectedPersons[0] },
            headers: { Authorization: `Bearer ${this.token}` },
          });

          const faces = facesResponse.data.faces || [];
          imagePaths = [...new Set(faces.map(face => face.image_path))];
        } else {
          const response = await axios.post(
            `${RECFAC_API_URL}/recfac/persons/faces-multiple/`,
            {
              names: this.selectedPersons,
              mode: this.searchMode,
            },
            { headers: { Authorization: `Bearer ${this.token}` } }
          );

          imagePaths = response.data.image_paths || [];
        }

        if (imagePaths.length === 0) {
          this.searchResults = [];
          return;
        }

        const imagesResponse = await axios.post(
          `${FILES_API_URL}/files/images-batch/`,
          { paths: imagePaths },
          { headers: { Authorization: `Bearer ${this.token}` } }
        );

        const results = imagesResponse.data.results || [];
        this.searchResults = results.filter(r => r.success);
      } catch (error) {
        console.error("Error fetching persons photos:", error);
        this.searchResults = [];
      } finally {
        this.loadingResults = false;
      }
    },
    openImage(imagePath) {
      this.$router.push({ path: "/image", query: { path: imagePath } });
    },

    // === Photo Selection Methods ===
    isPhotoSelected(item) {
      return this.selectedPhotos.some(p => p.path === item.path);
    },
    togglePhotoSelection(item) {
      if (this.isPhotoSelected(item)) {
        this.selectedPhotos = this.selectedPhotos.filter(p => p.path !== item.path);
      } else {
        this.selectedPhotos.push(item);
      }
    },
    clearPhotoSelection() {
      this.selectedPhotos = [];
    },
    selectAllPhotos() {
      this.selectedPhotos = [...this.sortedResults];
    },
    handleKeydown(event) {
      // Escape pour annuler la selection
      if (event.key === 'Escape') {
        this.clearPhotoSelection();
        this.hideContextMenu();
      }
      // Ctrl+A pour tout selectionner
      if ((event.ctrlKey || event.metaKey) && event.key === 'a' && this.token && this.sortedResults.length > 0) {
        event.preventDefault();
        this.selectAllPhotos();
      }
    },

    // === Context Menu Methods ===
    showContextMenu(event, item) {
      const menuWidth = 200;
      const menuHeight = 250;
      const viewportWidth = window.innerWidth;
      const viewportHeight = window.innerHeight;
      const padding = 10;

      let x = event.clientX;
      let y = event.clientY;

      if (x + menuWidth + padding > viewportWidth) {
        x = Math.max(padding, x - menuWidth);
      }

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
      const touch = event.touches[0];
      this.touchStartPos = { x: touch.clientX, y: touch.clientY };

      this.touchTimer = setTimeout(() => {
        if (navigator.vibrate) {
          navigator.vibrate(50);
        }
        this.showContextMenu({ clientX: touch.clientX, clientY: touch.clientY }, item);
      }, 500);
    },
    handleTouchEnd() {
      if (this.touchTimer) {
        clearTimeout(this.touchTimer);
        this.touchTimer = null;
      }
    },
    handleTouchMove(event) {
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

    // === Actions Methods ===
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
        link.remove();
        window.URL.revokeObjectURL(url);
      } catch (error) {
        console.error("Erreur lors du telechargement:", error);
        alert("Erreur lors du telechargement");
      }
    },
    async downloadSelected() {
      for (const item of this.selectedPhotos) {
        await this.downloadImage(item.path, item.name);
      }
    },
    async scanSingleImage(item) {
      if (!this.token || !this.isAdmin) return;

      try {
        const response = await axios.post(
          `${RECFAC_API_URL}/recfac/scan-image/`,
          { path: item.path },
          { headers: { Authorization: `Bearer ${this.token}` } }
        );

        const data = response.data;
        if (data.already_scanned) {
          alert(`Image deja scannee (${data.faces_count} visage(s))`);
        } else {
          alert(`Scan termine! ${data.faces_count} visage(s) detecte(s)`);
        }
      } catch (error) {
        console.error("Erreur lors du scan:", error);
        alert("Erreur lors du scan de l'image");
      }
    },
    async scanSelected() {
      if (!this.token || !this.isAdmin) return;
      if (this.selectedPhotos.length === 0) return;

      this.isProcessingSelection = true;

      try {
        const paths = this.selectedPhotos.map(item => item.path);
        const response = await axios.post(
          `${RECFAC_API_URL}/recfac/scan-multiple/`,
          { paths },
          { headers: { Authorization: `Bearer ${this.token}` } }
        );

        const data = response.data;
        alert(
          `Scan termine!\n` +
          `${data.scanned_count} image(s) scannee(s)\n` +
          `${data.already_scanned_count} deja scannee(s)\n` +
          `${data.total_faces} visage(s) detecte(s)\n` +
          `${data.errors_count} erreur(s)`
        );

        this.clearPhotoSelection();
      } catch (error) {
        console.error("Erreur lors du scan:", error);
        alert("Erreur lors du scan des images");
      } finally {
        this.isProcessingSelection = false;
      }
    },
    async deleteItem(item) {
      if (!this.token || !this.isAdmin) return;

      if (!window.confirm(`Supprimer cette image ?`)) {
        return;
      }

      try {
        await axios.post(
          `${FILES_API_URL}/files/delete/`,
          { path: item.path },
          { headers: { Authorization: `Bearer ${this.token}` } }
        );
        // Rafraichir les resultats
        this.searchResults = this.searchResults.filter(r => r.path !== item.path);
        this.selectedPhotos = this.selectedPhotos.filter(p => p.path !== item.path);
      } catch (error) {
        console.error("Erreur lors de la suppression:", error);
        alert("Erreur lors de la suppression");
      }
    },
    async deleteSelected() {
      if (!this.token || !this.isAdmin) return;

      if (!confirm(`Supprimer ${this.selectedPhotos.length} photo(s) ?`)) {
        return;
      }

      this.isProcessingSelection = true;

      try {
        const paths = this.selectedPhotos.map(item => item.path);
        const response = await axios.post(
          `${FILES_API_URL}/files/delete-multiple/`,
          { paths },
          { headers: { Authorization: `Bearer ${this.token}` } }
        );

        const data = response.data;
        alert(
          `Suppression terminee!\n` +
          `${data.deleted_count} element(s) supprime(s)\n` +
          `${data.errors_count} erreur(s)`
        );

        // Retirer les images supprimees des resultats
        const deletedPaths = new Set(paths);
        this.searchResults = this.searchResults.filter(r => !deletedPaths.has(r.path));
        this.clearPhotoSelection();
      } catch (error) {
        console.error("Erreur lors de la suppression:", error);
        alert("Erreur lors de la suppression");
      } finally {
        this.isProcessingSelection = false;
      }
    },

    handleClickOutside(event) {
      const searchContainer = this.$el.querySelector('.sidebar-search');
      if (searchContainer && !searchContainer.contains(event.target)) {
        this.closeSuggestions();
      }
    },
  },
  mounted() {
    this.loadPersons();
    this.determineAdmin();

    const personParam = this.$route.query.person;
    if (personParam) {
      this.selectedPersons = [personParam];
      this.loadPersonsPhotos();
    }

    document.addEventListener('click', this.handleClickOutside);
    document.addEventListener('click', this.hideContextMenu);
    document.addEventListener('keydown', this.handleKeydown);
  },
  beforeUnmount() {
    document.removeEventListener('click', this.handleClickOutside);
    document.removeEventListener('click', this.hideContextMenu);
    document.removeEventListener('keydown', this.handleKeydown);
  },
};
</script>

<style scoped>
.personnes-page {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: #f8f9fa;
}

.page-layout {
  flex: 1;
  display: flex;
  overflow: hidden;
}

/* Sidebar */
.persons-sidebar {
  width: 280px;
  background: #ffffff;
  border-right: 1px solid #e9ecef;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-header {
  padding: 1rem 1.25rem;
  border-bottom: 1px solid #e9ecef;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.btn-collapse {
  background: none;
  border: none;
  padding: 0.25rem;
  color: #6c757d;
  cursor: pointer;
}

/* Search with tags */
.sidebar-search {
  padding: 0.75rem;
  border-bottom: 1px solid #e9ecef;
  position: relative;
}

.search-tags-container {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.25rem;
  padding: 0.375rem 0.5rem;
  border: 1px solid #ced4da;
  border-radius: 0.375rem;
  background: #fff;
  min-height: 38px;
  cursor: text;
}

.search-tags-container:focus-within {
  border-color: #86b7fe;
  box-shadow: 0 0 0 0.25rem rgba(13, 110, 253, 0.25);
}

.search-tag {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
  padding: 0.125rem 0.375rem;
  background: #0d6efd;
  color: white;
  border-radius: 0.25rem;
  font-size: 0.8rem;
  white-space: nowrap;
}

.search-tag-remove {
  background: none;
  border: none;
  color: white;
  padding: 0;
  margin-left: 0.125rem;
  font-size: 1rem;
  line-height: 1;
  cursor: pointer;
  opacity: 0.8;
}

.search-tag-remove:hover {
  opacity: 1;
}

.search-input-inline {
  flex: 1;
  min-width: 80px;
  border: none;
  outline: none;
  padding: 0.125rem;
  font-size: 0.875rem;
  background: transparent;
}

.search-input-inline::placeholder {
  color: #6c757d;
}

/* Suggestions dropdown */
.suggestions-dropdown {
  position: absolute;
  top: 100%;
  left: 0.75rem;
  right: 0.75rem;
  background: #fff;
  border: 1px solid #dee2e6;
  border-radius: 0.375rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  max-height: 300px;
  overflow-y: auto;
}

.suggestion-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: none;
  background: transparent;
  text-align: left;
  cursor: pointer;
  transition: background-color 0.1s ease;
}

.suggestion-item:hover,
.suggestion-highlighted {
  background: #f3f4f6;
}

.suggestion-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.7rem;
  flex-shrink: 0;
}

.suggestion-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.suggestion-name {
  font-weight: 500;
  color: #1f2937;
  font-size: 0.875rem;
}

.suggestion-count {
  font-size: 0.7rem;
  color: #6b7280;
}

.suggestion-check {
  color: #0d6efd;
  font-weight: bold;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem;
}

.sidebar-footer {
  padding: 0.75rem 1rem;
  border-top: 1px solid #e9ecef;
  text-align: center;
}

.selection-info {
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Empty state */
.empty-state {
  padding: 2rem 1rem;
  text-align: center;
  color: #6c757d;
}

.empty-state svg {
  opacity: 0.5;
}

/* Persons list */
.persons-list {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.person-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 0.75rem;
  background: transparent;
  border: none;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: background-color 0.15s ease;
  text-align: left;
  width: 100%;
}

.person-item:hover {
  background: #f3f4f6;
}

.person-item.active {
  background: #e7f1ff;
}

.person-checkbox {
  flex-shrink: 0;
}

.person-checkbox input {
  width: 16px;
  height: 16px;
  cursor: pointer;
}

.person-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.8rem;
  flex-shrink: 0;
}

.person-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.person-name {
  font-weight: 500;
  color: #1f2937;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 0.9rem;
}

.person-count {
  font-size: 0.7rem;
  color: #6b7280;
}

/* Main content */
.main-content {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
}

/* No selection */
.no-selection {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  text-align: center;
  color: #6c757d;
}

.no-selection svg {
  opacity: 0.4;
}

.quick-stats {
  display: flex;
  gap: 1.5rem;
}

.stat-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 1rem 2rem;
  background: #ffffff;
  border-radius: 0.75rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.stat-value {
  font-size: 2rem;
  font-weight: 700;
  color: #1f2937;
}

.stat-label {
  font-size: 0.875rem;
  color: #6b7280;
}

/* Loading results */
.loading-results {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
}

/* Results */
.results-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.results-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
  gap: 1rem;
}

.results-actions {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.search-mode-toggle .btn {
  font-size: 0.75rem;
  padding: 0.25rem 0.5rem;
}

.empty-results {
  text-align: center;
  padding: 3rem;
}

/* Photos grid */
.photos-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 1rem;
}

.photo-card {
  background: #ffffff;
  border-radius: 0.75rem;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
  position: relative;
  border: 2px solid transparent;
}

.photo-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.photo-card.photo-selected {
  border-color: #0d6efd;
  box-shadow: 0 0 0 3px rgba(13, 110, 253, 0.25);
}

.photo-wrapper {
  position: relative;
  aspect-ratio: 1;
  overflow: hidden;
}

.photo-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.photo-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #e9ecef;
  color: #6c757d;
}

.photo-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.15s ease;
  color: white;
}

.photo-card:hover .photo-overlay {
  opacity: 1;
}

.photo-info {
  padding: 0.75rem;
}

.photo-name {
  font-size: 0.8rem;
  color: #374151;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: block;
}

/* Mobile responsive */
@media (max-width: 768px) {
  .page-layout {
    flex-direction: column;
  }

  .persons-sidebar {
    width: 100%;
    max-height: 50vh;
    border-right: none;
    border-bottom: 1px solid #e9ecef;
  }

  .persons-sidebar.sidebar-collapsed {
    max-height: 60px;
  }

  .persons-sidebar.sidebar-collapsed .sidebar-content,
  .persons-sidebar.sidebar-collapsed .sidebar-footer,
  .persons-sidebar.sidebar-collapsed .sidebar-search {
    display: none;
  }

  .main-content {
    padding: 1rem;
  }

  .photos-grid {
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: 0.75rem;
  }

  .results-header {
    flex-direction: column;
    align-items: stretch;
  }

  .results-actions {
    justify-content: space-between;
    flex-wrap: wrap;
  }

  .quick-stats {
    flex-direction: column;
    gap: 1rem;
  }

  .stat-card {
    padding: 0.75rem 1.5rem;
  }

  /* Selection bar responsive */
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

/* Selection zone styles */
.selection-zone {
  position: absolute;
  top: 0;
  left: 0;
  z-index: 10;
  width: 2.5rem;
  height: 2.5rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.selection-indicator {
  width: 1.5rem;
  height: 1.5rem;
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
  width: 1rem;
  height: 1rem;
  color: white;
}

/* Mobile: zone tactile plus grande */
@media (max-width: 768px) {
  .selection-zone {
    width: 3rem;
    height: 3rem;
  }

  .selection-indicator {
    opacity: 1;
    width: 1.75rem;
    height: 1.75rem;
  }

  .selection-indicator .checkmark {
    width: 1.2rem;
    height: 1.2rem;
  }
}

/* Selection bar styles */
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
}
</style>
