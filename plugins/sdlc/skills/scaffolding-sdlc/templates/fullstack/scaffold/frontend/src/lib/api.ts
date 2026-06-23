import axios from "axios";

/** Shared API client. Vite proxies /api to the Django backend in dev. */
export const api = axios.create({ baseURL: "/api" });
