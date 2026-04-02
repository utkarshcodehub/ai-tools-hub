import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: BASE_URL,
  timeout: 10000,
})

export const fetchTools = (params = {}) =>
  api.get('/tools', { params }).then(r => r.data)

export const fetchTool = (id) =>
  api.get(`/tools/${id}`).then(r => r.data)

export const fetchTrending = () =>
  api.get('/tools/trending').then(r => r.data)

export const fetchFreeTools = () =>
  api.get('/tools/free').then(r => r.data)

export const fetchCategories = () =>
  api.get('/categories').then(r => r.data)

export const fetchSearch = (q) =>
  api.get('/search', { params: { q } }).then(r => r.data)

export const fetchAlternatives = (id) =>
  api.get(`/tools/alternatives/${id}`).then(r => r.data)

export const fetchCompare = (ids = []) =>
  api.get('/tools/compare', { params: { ids: ids.join(',') } }).then(r => r.data)

export const fetchEnvTemplate = (ids = []) =>
  api.get('/tools/env-template', { params: { ids: ids.join(',') } }).then(r => r.data)