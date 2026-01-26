<template>
  <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
    <div class="container-fluid">
      <a class="navbar-brand" href="#">ProPhotos</a>
      <button
        class="navbar-toggler"
        type="button"
        data-bs-toggle="collapse"
        data-bs-target="#navbarNav"
        aria-controls="navbarNav"
        aria-expanded="false"
        aria-label="Toggle navigation"
      >
        <span class="navbar-toggler-icon"></span>
      </button>
      <div class="collapse navbar-collapse" id="navbarNav">
        <ul class="navbar-nav ms-auto">
          <li class="nav-item" v-if="token">
            <span class="nav-link">Bienvenue, {{ username }}</span>
          </li>
          <li class="nav-item">
            <router-link to="/images" class="nav-link">Home</router-link>
          </li>
          <li class="nav-item" v-if="token">
            <router-link to="/personnes" class="nav-link">Personnes</router-link>
          </li>
          <li class="nav-item" v-if="token && isAdmin">
            <router-link to="/recfac" class="nav-link">Reconnaissance Faciale</router-link>
          </li>
          <li class="nav-item" v-if="!token">
            <router-link to="/login" class="nav-link">Login</router-link>
          </li>

          <li class="nav-item" v-if="token">
            <span @click="logout" class="nav-link cursor-pointer">Logout</span>
          </li>
        </ul>
      </div>
    </div>
  </nav>
</template>

<script>
import { USERS_API_URL } from "@/constants";

export default {
  name: "NavBar",
  data() {
    return {
      token: localStorage.getItem("token") || null,
      username: "",
      isAdmin: false,
    };
  },
  created() {
    if (this.token) {
      this.verifyToken();
    }
  },
  watch: {
    token(newToken) {
      if (newToken) {
        this.verifyToken();
      } else {
        this.username = "";
        this.isAdmin = false;
      }
    },
  },
  methods: {
    async verifyToken() {
      try {
        const response = await fetch(USERS_API_URL + "/users/verify-token/", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${this.token}`,
          },
        });
        const data = await response.json();
        if (response.ok) {
          this.username = data.user.username;
          this.isAdmin = data.user.admin || false;
        } else {
          // token invalide/expiré → logout
          this.logout();
          alert("Votre session a expiré, veuillez vous reconnecter.");
        }
      } catch (error) {
        console.error("Erreur lors de la vérification du token :", error);
        this.logout();
      }
    },
    logout() {
      localStorage.removeItem("token");
      this.token = null;
      this.username = "";
      this.isAdmin = false;
      this.$emit("update-token", null);
      this.$router.push("/login");
    },
  },
};
</script>


<style scoped>
nav a {
  text-decoration: none;
}
</style>
