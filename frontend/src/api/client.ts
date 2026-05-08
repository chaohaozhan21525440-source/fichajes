import axios from 'axios'

let _token: string | null = null

export const setToken = (t: string | null) => { _token = t }
export const getToken = () => _token

// En producción: VITE_API_URL = URL del backend en Railway
// En local (npm run dev): vacío → el proxy de Vite redirige /api a localhost:8000
const client = axios.create({ baseURL: import.meta.env.VITE_API_URL || '' })

client.interceptors.request.use((config) => {
  if (_token) config.headers.Authorization = `Bearer ${_token}`
  return config
})

client.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      _token = null
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export default client
