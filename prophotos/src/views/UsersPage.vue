<template>
  <div>
    <NavigationBar :token="token" @update-token="handleTokenUpdate" />
    <div class="container mt-4">
      <h1 class="mb-4">Gestion des Utilisateurs</h1>

      <!-- Utilisateurs en attente de validation -->
      <div class="card mb-4">
        <div class="card-header bg-warning text-dark d-flex justify-content-between align-items-center">
          <h5 class="mb-0">En attente de validation</h5>
          <span v-if="pendingUsers.length" class="badge bg-dark">{{ pendingUsers.length }}</span>
        </div>
        <div class="card-body">
          <div v-if="loadingUsers" class="text-center py-3">
            <span class="spinner-border spinner-border-sm me-2"></span>Chargement...
          </div>
          <div v-else-if="pendingUsers.length === 0" class="alert alert-success mb-0">
            Aucun utilisateur en attente de validation.
          </div>
          <div v-else class="table-responsive">
            <table class="table table-hover align-middle mb-0">
              <thead>
                <tr>
                  <th>Utilisateur</th>
                  <th>Email</th>
                  <th>Demande Admin</th>
                  <th>Date inscription</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="user in pendingUsers" :key="user.id">
                  <td><strong>{{ user.username }}</strong></td>
                  <td>{{ user.email }}</td>
                  <td>
                    <span v-if="user.admin" class="badge bg-info">Oui</span>
                    <span v-else class="badge bg-secondary">Non</span>
                  </td>
                  <td>{{ formatDate(user.created_at) }}</td>
                  <td>
                    <button
                      @click="verifyUser(user)"
                      class="btn btn-success btn-sm"
                      :disabled="user._loading"
                    >
                      <span v-if="user._loading" class="spinner-border spinner-border-sm"></span>
                      <span v-else>Valider</span>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Tous les utilisateurs -->
      <div class="card mb-4">
        <div class="card-header bg-primary text-white d-flex justify-content-between align-items-center">
          <h5 class="mb-0">Tous les utilisateurs</h5>
          <button @click="loadUsers" class="btn btn-light btn-sm" :disabled="loadingUsers">
            <span v-if="loadingUsers" class="spinner-border spinner-border-sm"></span>
            <span v-else>Rafraichir</span>
          </button>
        </div>
        <div class="card-body">
          <div v-if="loadingUsers" class="text-center py-3">
            <span class="spinner-border spinner-border-sm me-2"></span>Chargement...
          </div>
          <div v-else-if="allUsers.length === 0" class="alert alert-info mb-0">
            Aucun utilisateur.
          </div>
          <div v-else class="table-responsive">
            <table class="table table-hover align-middle mb-0">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Utilisateur</th>
                  <th>Email</th>
                  <th>Admin</th>
                  <th>Verifie</th>
                  <th>Date inscription</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="user in verifiedUsers" :key="user.id">
                  <td><small class="text-muted">{{ user.id }}</small></td>
                  <td><strong>{{ user.username }}</strong></td>
                  <td>{{ user.email }}</td>
                  <td>
                    <div class="form-check form-switch">
                      <input
                        class="form-check-input"
                        type="checkbox"
                        :checked="user.admin"
                        @change="toggleAdmin(user)"
                        :disabled="user.id === currentUserId"
                        :title="user.id === currentUserId ? 'Vous ne pouvez pas modifier vos propres droits' : ''"
                      >
                    </div>
                  </td>
                  <td>
                    <span v-if="user.verifie" class="badge bg-success">Oui</span>
                    <span v-else class="badge bg-warning">Non</span>
                  </td>
                  <td>{{ formatDate(user.created_at) }}</td>
                  <td>
                    <div class="btn-group btn-group-sm">
                      <button
                        @click="openEditModal(user)"
                        class="btn btn-outline-primary"
                        title="Modifier"
                      >
                        Modifier
                      </button>
                      <button
                        @click="confirmDelete(user)"
                        class="btn btn-outline-danger"
                        :disabled="user.id === currentUserId"
                        :title="user.id === currentUserId ? 'Vous ne pouvez pas supprimer votre propre compte' : 'Supprimer'"
                      >
                        Supprimer
                      </button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <!-- Modal Modifier Utilisateur -->
      <div v-if="editModal.show" class="modal d-block" tabindex="-1" style="background: rgba(0,0,0,0.5);">
        <div class="modal-dialog">
          <div class="modal-content">
            <div class="modal-header">
              <h5 class="modal-title">Modifier l'utilisateur</h5>
              <button type="button" class="btn-close" @click="editModal.show = false"></button>
            </div>
            <div class="modal-body">
              <div class="mb-3">
                <label class="form-label">Nom d'utilisateur</label>
                <input
                  v-model="editModal.username"
                  type="text"
                  class="form-control"
                  :class="{ 'is-invalid': editModal.error && editModal.error.includes('utilisateur') }"
                >
              </div>
              <div class="mb-3">
                <label class="form-label">Email</label>
                <input
                  v-model="editModal.email"
                  type="email"
                  class="form-control"
                  :class="{ 'is-invalid': editModal.error && editModal.error.includes('email') }"
                >
              </div>
              <div v-if="editModal.error" class="alert alert-danger py-2">
                {{ editModal.error }}
              </div>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn btn-secondary" @click="editModal.show = false">Annuler</button>
              <button
                type="button"
                class="btn btn-primary"
                @click="saveEdit"
                :disabled="editModal.saving"
              >
                <span v-if="editModal.saving" class="spinner-border spinner-border-sm me-1"></span>
                Sauvegarder
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Error Display -->
      <div v-if="error" class="alert alert-danger alert-dismissible fade show">
        <strong>Erreur:</strong> {{ error }}
        <button type="button" class="btn-close" @click="error = null"></button>
      </div>

      <!-- Success Display -->
      <div v-if="successMsg" class="alert alert-success alert-dismissible fade show">
        {{ successMsg }}
        <button type="button" class="btn-close" @click="successMsg = null"></button>
      </div>
    </div>
    <FooterSection />
  </div>
</template>

<script>
import { USERS_API_URL } from "@/constants";
import NavigationBar from "@/components/NavBar.vue";
import FooterSection from "@/components/FootSection.vue";

export default {
  name: "UsersPage",
  components: {
    NavigationBar,
    FooterSection,
  },
  data() {
    return {
      token: localStorage.getItem("token") || null,
      isAdmin: false,
      currentUserId: null,
      loadingUsers: false,
      error: null,
      successMsg: null,
      allUsers: [],
      editModal: {
        show: false,
        userId: null,
        username: "",
        email: "",
        error: null,
        saving: false,
      },
    };
  },
  computed: {
    pendingUsers() {
      return this.allUsers.filter(u => !u.verifie);
    },
    verifiedUsers() {
      return this.allUsers.filter(u => u.verifie);
    },
  },
  async created() {
    await this.verifyToken();
    if (this.isAdmin) {
      await this.loadUsers();
    }
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
          // Recuperer l'ID de l'admin connecte
          const meResponse = await fetch(USERS_API_URL + "/users/me/", {
            headers: { Authorization: `Bearer ${this.token}` },
          });
          if (meResponse.ok) {
            const meData = await meResponse.json();
            this.currentUserId = meData.id;
          }
        }
      } catch (error) {
        console.error("Erreur verification token:", error);
      }
    },

    async loadUsers() {
      this.loadingUsers = true;
      this.error = null;

      try {
        const response = await fetch(`${USERS_API_URL}/users/`, {
          headers: { Authorization: `Bearer ${this.token}` },
        });

        if (response.ok) {
          const data = await response.json();
          this.allUsers = data.map(u => ({ ...u, _loading: false }));
        } else {
          const data = await response.json();
          this.error = data.error || "Erreur lors du chargement des utilisateurs";
        }
      } catch (error) {
        this.error = "Erreur de connexion au serveur";
      } finally {
        this.loadingUsers = false;
      }
    },

    async verifyUser(user) {
      user._loading = true;
      this.error = null;

      try {
        const response = await fetch(`${USERS_API_URL}/users/${user.id}/verify/`, {
          method: "POST",
          headers: { Authorization: `Bearer ${this.token}` },
        });

        if (response.ok) {
          const data = await response.json();
          this.successMsg = data.message;
          await this.loadUsers();
        } else {
          const data = await response.json();
          this.error = data.error || "Erreur lors de la validation";
        }
      } catch (error) {
        this.error = "Erreur de connexion au serveur";
      } finally {
        user._loading = false;
      }
    },

    async toggleAdmin(user) {
      const newAdminStatus = !user.admin;

      try {
        const response = await fetch(`${USERS_API_URL}/users/${user.id}/update/`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${this.token}`,
          },
          body: JSON.stringify({ admin: newAdminStatus }),
        });

        if (response.ok) {
          const data = await response.json();
          this.successMsg = data.message;
          user.admin = newAdminStatus;
        } else {
          const data = await response.json();
          this.error = data.error || "Erreur lors de la modification";
          // Revert le switch visuellement
          await this.loadUsers();
        }
      } catch (error) {
        this.error = "Erreur de connexion au serveur";
        await this.loadUsers();
      }
    },

    openEditModal(user) {
      this.editModal = {
        show: true,
        userId: user.id,
        username: user.username,
        email: user.email,
        error: null,
        saving: false,
      };
    },

    async saveEdit() {
      this.editModal.saving = true;
      this.editModal.error = null;

      try {
        const response = await fetch(`${USERS_API_URL}/users/${this.editModal.userId}/update/`, {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${this.token}`,
          },
          body: JSON.stringify({
            username: this.editModal.username,
            email: this.editModal.email,
          }),
        });

        if (response.ok) {
          const data = await response.json();
          this.successMsg = data.message;
          this.editModal.show = false;
          await this.loadUsers();
        } else {
          const data = await response.json();
          this.editModal.error = data.error || "Erreur lors de la modification";
        }
      } catch (error) {
        this.editModal.error = "Erreur de connexion au serveur";
      } finally {
        this.editModal.saving = false;
      }
    },

    async confirmDelete(user) {
      if (!confirm(`Supprimer l'utilisateur "${user.username}" ? Cette action est irreversible.`)) {
        return;
      }

      try {
        const response = await fetch(`${USERS_API_URL}/users/${user.id}/delete/`, {
          method: "DELETE",
          headers: { Authorization: `Bearer ${this.token}` },
        });

        if (response.ok) {
          const data = await response.json();
          this.successMsg = data.message;
          await this.loadUsers();
        } else {
          const data = await response.json();
          this.error = data.error || "Erreur lors de la suppression";
        }
      } catch (error) {
        this.error = "Erreur de connexion au serveur";
      }
    },

    formatDate(dateStr) {
      if (!dateStr) return "-";
      const date = new Date(dateStr);
      return date.toLocaleDateString("fr-FR", {
        day: "2-digit",
        month: "2-digit",
        year: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      });
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
  },
};
</script>

<style scoped>
.card {
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.form-switch .form-check-input {
  cursor: pointer;
}

.form-switch .form-check-input:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.table th {
  font-size: 0.85rem;
  text-transform: uppercase;
  color: #6c757d;
}

.modal {
  z-index: 1050;
}
</style>
