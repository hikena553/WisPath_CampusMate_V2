import axios, { type AxiosRequestConfig } from 'axios'
import { getToken, removeToken } from './token'
import { ElMessage } from 'element-plus'

const instance = axios.create({ baseURL: '/api' })

instance.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

instance.interceptors.response.use(
  (res) => {
    // 对于 blob 响应，直接返回 data
    if (res.config?.responseType === 'blob') {
      return res.data
    }
    return res.data
  },
  (err) => {
    if (err.response?.status === 401 && !window.location.pathname.startsWith('/login')) {
      removeToken()
      window.location.href = '/login'
      return Promise.reject(err)
    }
    
    // 403错误 - 显示权限不足提示
    if (err.response?.status === 403) {
      ElMessage.error('权限不足')
      return Promise.reject(err)
    }
    
    return Promise.reject(err)
  }
)

const request = {
  get<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return instance.get(url, config) as any
  },
  post<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return instance.post(url, data, config) as any
  },
  put<T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> {
    return instance.put(url, data, config) as any
  },
  delete<T = any>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return instance.delete(url, config) as any
  },
}

export default request
