<template>
  <div>
    <NavigationBar :token="token" @update-token="handleTokenUpdate" />
    <div class="container mt-4">
      <h1 class="mb-4">Reconnaissance Faciale</h1>

      <!-- Tabs Navigation -->
      <ul class="nav nav-tabs mb-4">
        <li class="nav-item">
          <a
            class="nav-link"
            :class="{ active: activeTab === 'visages' }"
            @click.prevent="activeTab = 'visages'"
            href="#"
          >
            Visages
          </a>
        </li>
        <li class="nav-item">
          <a
            class="nav-link"
            :class="{ active: activeTab === 'tags' }"
            @click.prevent="activeTab = 'tags'"
            href="#"
          >
            Tags
          </a>
        </li>
        <li class="nav-item">
          <a
            class="nav-link"
            :class="{ active: activeTab === 'tests' }"
            @click.prevent="activeTab = 'tests'"
            href="#"
          >
            Tests
          </a>
        </li>
      </ul>

      <!-- Tab Content -->
      <div v-if="activeTab === 'visages'">
        <h2>Onglet Visages</h2>
        <p>Contenu de l'onglet Visages</p>
      </div>

      <div v-if="activeTab === 'tags'">
        <h2>Onglet Tags</h2>
        <p>Contenu de l'onglet Tags</p>
      </div>

      <div v-if="activeTab === 'tests'">
        <h2>Onglet Tests</h2>
        <p>Contenu de l'onglet Tests</p>
      </div>

      <!-- Error Display -->
      <div v-if="error" class="alert alert-danger mt-4">
        <strong>Erreur:</strong> {{ error }}
      </div>
    </div>
    <FooterSection />
  </div>
</template>

<script>
import NavigationBar from "@/components/NavBar.vue";
import FooterSection from "@/components/FootSection.vue";

export default {
  name: "RecfacPageSimple",
  components: {
    NavigationBar,
    FooterSection,
  },
  data() {
    return {
      token: localStorage.getItem("token") || null,
      activeTab: 'visages',
      error: null,
    };
  },
  methods: {
    handleTokenUpdate(newToken) {
      this.token = newToken;
      if (newToken) {
        localStorage.setItem("token", newToken);
      } else {
        localStorage.removeItem("token");
      }
    },
  },
};
</script>

<style scoped>
.nav-link {
  cursor: pointer;
}
</style>
