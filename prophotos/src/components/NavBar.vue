<template>
  <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
    <div class="container-fluid px-3">
      <!-- Brand -->
      <router-link to="/images" class="navbar-brand d-flex align-items-center gap-2">
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
          <circle cx="8.5" cy="8.5" r="1.5"/>
          <polyline points="21 15 16 10 5 21"/>
        </svg>
        <span class="fw-bold">ProPhotos</span>
      </router-link>

      <!-- Mobile toggle -->
      <button
        class="navbar-toggler border-0"
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
        <!-- Left nav links -->
        <ul class="navbar-nav me-auto">
          <li class="nav-item">
            <router-link to="/images" class="nav-link" active-class="active">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="nav-icon">
                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                <polyline points="9 22 9 12 15 12 15 22"/>
              </svg>
              Home
            </router-link>
          </li>
          <li class="nav-item" v-if="token">
            <router-link to="/personnes" class="nav-link" active-class="active">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="nav-icon">
                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                <circle cx="9" cy="7" r="4"/>
                <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
                <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
              </svg>
              Personnes
            </router-link>
          </li>
        </ul>

        <!-- Right nav -->
        <ul class="navbar-nav align-items-lg-center">
          <!-- Admin section -->
          <template v-if="token && isAdmin">
            <li class="nav-item dropdown">
              <a
                class="nav-link dropdown-toggle"
                href="#"
                role="button"
                data-bs-toggle="dropdown"
                aria-expanded="false"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="nav-icon">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                </svg>
                Admin
              </a>
              <ul class="dropdown-menu dropdown-menu-end">
                <li>
                  <router-link to="/recfac" class="dropdown-item">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="me-2">
                      <circle cx="12" cy="12" r="3"/>
                      <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                    </svg>
                    Config
                  </router-link>
                </li>
                <li>
                  <router-link to="/utilisateurs" class="dropdown-item">
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="me-2">
                      <path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                      <circle cx="8.5" cy="7" r="4"/>
                      <line x1="20" y1="8" x2="20" y2="14"/>
                      <line x1="23" y1="11" x2="17" y2="11"/>
                    </svg>
                    Utilisateurs
                  </router-link>
                </li>
              </ul>
            </li>
          </template>

          <!-- Divider -->
          <li class="nav-item d-none d-lg-block" v-if="token">
            <span class="nav-separator"></span>
          </li>

          <!-- User info -->
          <li class="nav-item" v-if="token">
            <span class="nav-link user-badge">
              <span class="user-avatar">{{ userInitial }}</span>
              <span>{{ username }}</span>
              <span v-if="isAdmin" class="badge-admin">admin</span>
            </span>
          </li>

          <!-- Login / Logout -->
          <li class="nav-item" v-if="!token">
            <router-link to="/login" class="nav-link btn-login">
              Login
            </router-link>
          </li>
          <li class="nav-item" v-if="token">
            <span @click="logout" class="nav-link logout-link" role="button">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="nav-icon">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                <polyline points="16 17 21 12 16 7"/>
                <line x1="21" y1="12" x2="9" y2="12"/>
              </svg>
              Logout
            </span>
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
  computed: {
    userInitial() {
      return this.username ? this.username.charAt(0).toUpperCase() : "?";
    },
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
nav {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

nav a {
  text-decoration: none;
}

/* Nav icons */
.nav-icon {
  margin-right: 4px;
  vertical-align: -2px;
}

/* Active link style */
.nav-link.active {
  position: relative;
  font-weight: 600;
}

.nav-link.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 24px;
  height: 3px;
  background: rgba(255, 255, 255, 0.9);
  border-radius: 3px 3px 0 0;
}

/* Nav links hover */
.nav-link {
  transition: opacity 0.15s ease;
  font-size: 0.9rem;
}

.nav-link:hover {
  opacity: 0.85;
}

/* Separator */
.nav-separator {
  display: inline-block;
  width: 1px;
  height: 20px;
  background: rgba(255, 255, 255, 0.3);
  margin: 0 8px;
  vertical-align: middle;
}

/* User badge */
.user-badge {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: default !important;
}

.user-avatar {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  font-size: 0.75rem;
  font-weight: 700;
  letter-spacing: 0;
}

.badge-admin {
  font-size: 0.6rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: rgba(255, 255, 255, 0.2);
  padding: 2px 6px;
  border-radius: 10px;
}

/* Login button */
.btn-login {
  border: 1px solid rgba(255, 255, 255, 0.5) !important;
  border-radius: 6px !important;
  padding: 4px 16px !important;
  margin-left: 4px;
}

.btn-login:hover {
  background: rgba(255, 255, 255, 0.1) !important;
  border-color: rgba(255, 255, 255, 0.8) !important;
}

/* Logout */
.logout-link {
  cursor: pointer;
  opacity: 0.8;
}

.logout-link:hover {
  opacity: 1;
}

/* Dropdown */
.dropdown-menu {
  border: none;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  border-radius: 8px;
  padding: 4px;
  min-width: 180px;
}

.dropdown-item {
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 0.875rem;
  display: flex;
  align-items: center;
}

.dropdown-item:hover {
  background: #f0f4ff;
}

.dropdown-item.router-link-active {
  background: #e8edff;
  font-weight: 600;
}

/* Mobile adjustments */
@media (max-width: 991.98px) {
  .nav-separator {
    display: none;
  }

  .user-badge {
    padding-top: 8px;
    border-top: 1px solid rgba(255, 255, 255, 0.15);
    margin-top: 4px;
  }

  .nav-link.active::after {
    display: none;
  }
}
</style>
