import axios, { type AxiosRequestConfig } from 'axios'
import { getToken, removeToken } from './token'
import { ElMessage } from 'element-plus'

const instance = axios.create({ baseURL: '/api', withCredentials: true })

instance.interceptors.request.use((config) => {
  // CSRF 纵深防护：所有请求带自定义头（后端对携带认证 Cookie 的写请求校验）
  config.headers['X-Requested-With'] = 'XMLHttpRequest'
  // Bearer 双通道：内存态 token 存在时注入（WebSocket 等显式场景）；
  // 刷新后内存态为空则依赖 httpOnly Cookie 自动认证
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
    
    // 403错误 - 优先展示后端返回的具体拦截原因（如强制改密），否则显示通用提示
    if (err.response?.status === 403) {
      const detail = err.response?.data?.detail
      const message = typeof detail === 'string' && detail ? detail : '权限不足'
      ElMessage.error(message)
      return Promise.reject(err)
    }
    
    return Promise.reject(err)
  }
)

const request = {
  get<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return instance.get(url, config) as unknown as Promise<T>
  },
  post<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    return instance.post(url, data, config) as unknown as Promise<T>
  },
  put<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    return instance.put(url, data, config) as unknown as Promise<T>
  },
  patch<T = unknown>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T> {
    return instance.patch(url, data, config) as unknown as Promise<T>
  },
  delete<T = unknown>(url: string, config?: AxiosRequestConfig): Promise<T> {
    return instance.delete(url, config) as unknown as Promise<T>
  },
}

export default request
