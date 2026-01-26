<template>
  <div>
    <NavigationBar />
    <div class="d-flex align-items-center justify-content-center min-vh-100 bg-light">
      <div class="row g-0 shadow-lg rounded-3 overflow-hidden bg-white" style="width: 90%; max-width: 900px;">
        <!-- Formulaire d'inscription -->
        <div class="col-md-6 border-end px-4 py-5">
          <h2 class="text-center mb-4">Inscription</h2>
          <form @submit.prevent="register">
            <!-- Username -->
            <div class="mb-3">
              <label for="username" class="form-label">Nom d'utilisateur</label>
              <input
                type="text"
                id="username"
                v-model="registerForm.username"
                class="form-control"
                :class="{ 'is-invalid': registerErrors.username }"
                @input="validateUsername"
                required
              />
              <div v-if="registerErrors.username" class="invalid-feedback">
                {{ registerErrors.username }}
              </div>
            </div>

            <!-- Email -->
            <div class="mb-3">
              <label for="email" class="form-label">Email</label>
              <input
                type="email"
                id="email"
                v-model="registerForm.email"
                class="form-control"
                :class="{ 'is-invalid': registerErrors.email }"
                @input="validateRegisterEmail"
                required
              />
              <div v-if="registerErrors.email" class="invalid-feedback">
                {{ registerErrors.email }}
              </div>
            </div>

            <!-- Password with toggle -->
            <div class="mb-3">
              <label for="password" class="form-label">Mot de passe</label>
              <div class="input-group">
                <input
                  :type="showRegisterPassword ? 'text' : 'password'"
                  id="password"
                  v-model="registerForm.password"
                  class="form-control"
                  :class="{ 'is-invalid': registerErrors.password }"
                  @input="validateRegisterPassword"
                  required
                />
                <button
                  type="button"
                  class="btn btn-outline-secondary"
                  @click="showRegisterPassword = !showRegisterPassword"
                  tabindex="-1"
                >
                  <span v-if="showRegisterPassword">Masquer</span>
                  <span v-else>Afficher</span>
                </button>
              </div>
              <div v-if="registerErrors.password" class="text-danger small mt-1">
                {{ registerErrors.password }}
              </div>
              <!-- Password strength indicator -->
              <div v-if="registerForm.password" class="mt-2">
                <div class="progress" style="height: 5px;">
                  <div
                    class="progress-bar"
                    :class="passwordStrengthClass"
                    :style="{ width: passwordStrengthPercent + '%' }"
                  ></div>
                </div>
                <small :class="passwordStrengthTextClass">{{ passwordStrengthText }}</small>
              </div>
            </div>

            <!-- Admin request -->
            <div class="form-check mb-3">
              <input
                class="form-check-input"
                type="checkbox"
                id="register-admin"
                v-model="registerForm.admin_request"
              />
              <label class="form-check-label" for="register-admin">
                Demander un compte administrateur
              </label>
            </div>

            <!-- Submit button -->
            <button
              type="submit"
              class="btn btn-primary w-100"
              :disabled="registerLoading || !isRegisterFormValid"
            >
              <span v-if="registerLoading" class="spinner-border spinner-border-sm me-2" role="status"></span>
              {{ registerLoading ? 'Inscription...' : "S'inscrire" }}
            </button>

            <!-- Success/Error message -->
            <div v-if="registerMessage" class="alert mt-3 mb-0" :class="registerMessageClass">
              {{ registerMessage }}
            </div>
          </form>
        </div>

        <!-- Formulaire de connexion -->
        <div class="col-md-6 px-4 py-5 bg-light">
          <h2 class="text-center mb-4">Connexion</h2>
          <form @submit.prevent="login">
            <!-- Email -->
            <div class="mb-3">
              <label for="login-email" class="form-label">Email</label>
              <input
                type="email"
                id="login-email"
                v-model="loginForm.email"
                class="form-control"
                :class="{ 'is-invalid': loginErrors.email }"
                @input="validateLoginEmail"
                required
              />
              <div v-if="loginErrors.email" class="invalid-feedback">
                {{ loginErrors.email }}
              </div>
            </div>

            <!-- Password with toggle -->
            <div class="mb-3">
              <label for="login-password" class="form-label">Mot de passe</label>
              <div class="input-group">
                <input
                  :type="showLoginPassword ? 'text' : 'password'"
                  id="login-password"
                  v-model="loginForm.password"
                  class="form-control"
                  :class="{ 'is-invalid': loginErrors.password }"
                  required
                />
                <button
                  type="button"
                  class="btn btn-outline-secondary"
                  @click="showLoginPassword = !showLoginPassword"
                  tabindex="-1"
                >
                  <span v-if="showLoginPassword">Masquer</span>
                  <span v-else>Afficher</span>
                </button>
              </div>
              <div v-if="loginErrors.password" class="text-danger small mt-1">
                {{ loginErrors.password }}
              </div>
            </div>

            <!-- Submit button -->
            <button
              type="submit"
              class="btn btn-primary w-100"
              :disabled="loginLoading || !isLoginFormValid"
            >
              <span v-if="loginLoading" class="spinner-border spinner-border-sm me-2" role="status"></span>
              {{ loginLoading ? 'Connexion...' : 'Se connecter' }}
            </button>

            <!-- Error message -->
            <div v-if="loginMessage" class="alert mt-3 mb-0" :class="loginMessageClass">
              {{ loginMessage }}
            </div>
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
      // Register form
      registerForm: {
        username: "",
        email: "",
        password: "",
        admin_request: false,
      },
      registerErrors: {
        username: "",
        email: "",
        password: "",
      },
      registerLoading: false,
      registerMessage: "",
      registerMessageType: "success",
      showRegisterPassword: false,

      // Login form
      loginForm: {
        email: "",
        password: "",
      },
      loginErrors: {
        email: "",
        password: "",
      },
      loginLoading: false,
      loginMessage: "",
      loginMessageType: "error",
      showLoginPassword: false,
    };
  },
  computed: {
    // Password strength calculation
    passwordStrength() {
      const password = this.registerForm.password;
      if (!password) return 0;

      let strength = 0;
      if (password.length >= 6) strength += 1;
      if (password.length >= 10) strength += 1;
      if (/[a-z]/.test(password) && /[A-Z]/.test(password)) strength += 1;
      if (/\d/.test(password)) strength += 1;
      if (/[^a-zA-Z0-9]/.test(password)) strength += 1;

      return strength;
    },
    passwordStrengthPercent() {
      return (this.passwordStrength / 5) * 100;
    },
    passwordStrengthClass() {
      if (this.passwordStrength <= 1) return "bg-danger";
      if (this.passwordStrength <= 2) return "bg-warning";
      if (this.passwordStrength <= 3) return "bg-info";
      return "bg-success";
    },
    passwordStrengthText() {
      if (this.passwordStrength <= 1) return "Tres faible";
      if (this.passwordStrength <= 2) return "Faible";
      if (this.passwordStrength <= 3) return "Moyen";
      if (this.passwordStrength <= 4) return "Fort";
      return "Tres fort";
    },
    passwordStrengthTextClass() {
      if (this.passwordStrength <= 1) return "text-danger";
      if (this.passwordStrength <= 2) return "text-warning";
      if (this.passwordStrength <= 3) return "text-info";
      return "text-success";
    },

    // Form validation
    isRegisterFormValid() {
      return (
        this.registerForm.username.length >= 3 &&
        this.isValidEmail(this.registerForm.email) &&
        this.registerForm.password.length > 0 &&
        !this.registerErrors.username &&
        !this.registerErrors.email
      );
    },
    isLoginFormValid() {
      return (
        this.isValidEmail(this.loginForm.email) &&
        this.loginForm.password.length > 0
      );
    },

    // Message classes
    registerMessageClass() {
      return this.registerMessageType === "success" ? "alert-success" : "alert-danger";
    },
    loginMessageClass() {
      return this.loginMessageType === "success" ? "alert-success" : "alert-danger";
    },
  },
  methods: {
    isValidEmail(email) {
      const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
      return emailRegex.test(email);
    },

    // Validation methods
    validateUsername() {
      const username = this.registerForm.username;
      if (username.length > 0 && username.length < 3) {
        this.registerErrors.username = "Le nom d'utilisateur doit contenir au moins 3 caracteres";
      } else if (username && !/^[a-zA-Z0-9_-]+$/.test(username)) {
        this.registerErrors.username = "Caracteres autorises: lettres, chiffres, _ et -";
      } else {
        this.registerErrors.username = "";
      }
    },
    validateRegisterEmail() {
      const email = this.registerForm.email;
      if (email && !this.isValidEmail(email)) {
        this.registerErrors.email = "Adresse email invalide";
      } else {
        this.registerErrors.email = "";
      }
    },
    validateRegisterPassword() {
      this.registerErrors.password = "";
    },
    validateLoginEmail() {
      const email = this.loginForm.email;
      if (email && !this.isValidEmail(email)) {
        this.loginErrors.email = "Adresse email invalide";
      } else {
        this.loginErrors.email = "";
      }
    },

    async register() {
      // Reset messages
      this.registerMessage = "";

      // Validate
      this.validateUsername();
      this.validateRegisterEmail();

      if (!this.isRegisterFormValid) {
        return;
      }

      this.registerLoading = true;

      try {
        const response = await fetch(USERS_API_URL + "/users/create/", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(this.registerForm),
        });
        const data = await response.json();

        if (response.ok) {
          this.registerMessageType = "success";
          this.registerMessage = "Inscription reussie ! Veuillez patienter que l'administration valide votre compte.";
          // Reset form
          this.registerForm = {
            username: "",
            email: "",
            password: "",
            admin_request: false,
          };
        } else {
          this.registerMessageType = "error";
          this.registerMessage = data.error || "Erreur lors de l'inscription";
        }
      } catch (error) {
        this.registerMessageType = "error";
        this.registerMessage = "Erreur de connexion au serveur. Veuillez reessayer.";
      } finally {
        this.registerLoading = false;
      }
    },

    async login() {
      // Reset messages
      this.loginMessage = "";

      // Validate
      this.validateLoginEmail();

      if (!this.isLoginFormValid) {
        return;
      }

      this.loginLoading = true;

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
          this.loginMessageType = "success";
          this.loginMessage = "Connexion reussie !";
          this.handleLoginSuccess(data.token);
        } else if (data.code === "not_verified") {
          this.loginMessageType = "error";
          this.loginMessage = "Votre compte n'a pas encore ete valide par l'administration. Vous recevrez un email des qu'il sera active.";
        } else {
          this.loginMessageType = "error";
          this.loginMessage = data.error || "Email ou mot de passe incorrect";
        }
      } catch (error) {
        this.loginMessageType = "error";
        this.loginMessage = "Erreur de connexion au serveur. Veuillez reessayer.";
      } finally {
        this.loginLoading = false;
      }
    },

    handleLoginSuccess(token) {
      localStorage.setItem("token", token);
      this.$emit("update-token", token);

      // Redirect to the page the user was trying to access, or home
      const redirect = this.$route.query.redirect || "/images";
      this.$router.push(redirect);
    },
  },
};
</script>

<style scoped>
.progress {
  border-radius: 3px;
}

.input-group .btn {
  border-top-left-radius: 0;
  border-bottom-left-radius: 0;
}

.alert {
  font-size: 0.9rem;
}

.spinner-border-sm {
  width: 1rem;
  height: 1rem;
}
</style>