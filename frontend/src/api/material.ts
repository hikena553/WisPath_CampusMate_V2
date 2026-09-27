import request from '@/utils/request'
import type { Material } from '@/types'

export function getMyMaterials(params?: { status?: string }) {
  return request.get<Material[]>('/materials', { params })
}

export function createMaterial(data: {
  title: string
  category: string
  file_url: string
  file_name?: string
  file_type?: string
  remark?: string
}) {
  return request.post<Material>('/materials', data)
}

export function getMaterial(id: number) {
  return request.get<Material>(`/materials/${id}`)
}

export function deleteMaterial(id: number) {
  return request.delete(`/materials/${id}`)
}