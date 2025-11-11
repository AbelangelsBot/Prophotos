<template>
  <div>
    <NavigationBar />
    <div class="d-flex align-items-center justify-content-center min-vh-100 bg-light">
      <div class="row g-0 shadow-lg rounded-3 overflow-hidden bg-white" style="width: 90%; max-width: 900px;">
        <!-- Formulaire d'inscription -->
        <div class="col-md-6 border-end px-4 py-5">
          <h2 class="text-center mb-4">Inscription</h2>
          <form @submit.prevent="register">
            <div class="mb-3">
              <label for="username" class="form-label">Nom d'utilisateur</label>
              <input type="text" id="username" v-model="registerForm.username" class="form-control" required />
            </div>
            <div class="mb-3">
              <label for="email" class="form-label">Email</label>
              <input type="email" id="email" v-model="registerForm.email" class="form-control" required />
            </div>
            <div class="mb-3">
              <label for="password" class="form-label">Mot de passe</label>
              <input type="password" id="password" v-model="registerForm.password" class="form-control" required />
            </div>
            <button type="submit" class="btn btn-primary w-100">
              S'inscrire
            </button>
          </form>
        </div>

        <!-- Formulaire de connexion -->
        <div class="col-md-6 px-4 py-5 bg-light">
          <h2 class="text-center mb-4">Connexion</h2>
          <form @submit.prevent="login">
            <div class="mb-3">
              <label for="login-email" class="form-label">Email</label>
              <input type="email" id="login-email" v-model="loginForm.email" class="form-control" required />
            </div>
            <div class="mb-3">
              <label for="login-password" class="form-label">Mot de passe</label>
              <input type="password" id="login-password" v-model="loginForm.password" class="form-control" required />
            </div>
            <button type="submit" class="btn btn-primary w-100">
              Se connecter
            </button>
          </form>
        </div>
      </div>
    </div>
    <FooterSection />
  </div>
</template>

<script>
import NavigationBar from "@/components/NavBar.vue";
import FooterSection from "@/components/FootSection.vue";
import { USERS_API_URL } from "@/constants";
export default {
  components: {
    NavigationBar,
    FooterSection,
  },
  data() {
    return {
      registerForm: {
        username: "",
        email: "",
        password: "",
      },
      loginForm: {
        email: "",
        password: "",
      },
    };
  },
  methods: {
    async register() {
      try {
        const response = await fetch(USERS_API_URL + "/users/create/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(this.registerForm),
        });
        const data = await response.json();
        if (response.ok) {
          alert("Inscription réussie ! Veuillez patienter que l'administration valide votre compte.");
          // Pas de login auto car compte pas encore vérifié
        } else {
          alert(`Erreur : ${data.error}`);
        }
      } catch (error) {
        console.error("Erreur lors de l'inscription :", error);
      }
    },

    async login() {
      try {
        const response = await fetch(USERS_API_URL + "/users/login/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            email: this.loginForm.email,
            password: this.loginForm.password,
          }),
        });
        const data = await response.json();
        if (response.ok) {
          alert("Connexion réussie !");
          this.handleLoginSuccess(data.token);
        } else if (data.code === "not_verified") {
          alert("Votre compte n'a pas encore été validé par l'administration. Vous recevrez un email dès qu'il sera activé.");
        } else {
          alert(`Erreur : ${data.error}`);
        }
      } catch (error) {
        console.error("Erreur lors de la connexion :", error);
      }
    },

    handleLoginSuccess(token) {
      localStorage.setItem("token", token); // Stocker le token
      this.$router.push("/"); // Rediriger vers la home
      this.$emit("update-token", token); // Mettre à jour le token pour le NavBar
    },
  },
};
</script>


<style scoped>
body {
  font-family: Arial, sans-serif;
}
</style>
