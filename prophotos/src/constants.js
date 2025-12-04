// Define separate base URLs for Users and Files services (Vue CLI env vars)
// Configure in prophotos/.env.* as:
// VUE_APP_USERS_API_URL=http://localhost:8001
// VUE_APP_FILES_API_URL=http://localhost:8002

export const USERS_API_URL = process.env.VUE_APP_USERS_API_URL;
export const FILES_API_URL = process.env.VUE_APP_FILES_API_URL;

export const CURRENT_PATH_STORAGE_KEY = "currentPath";
export const PATH_HISTORY_STORAGE_KEY = "pathHistory";
