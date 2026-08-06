import { ref, computed, watch, type Ref } from 'vue'

export interface PaginationOptions {
  defaultPageSize?: number
  pageSizes?: number[]
}

export interface UsePaginationReturn<T> {
  currentPage: Ref<number>
  pageSize: Ref<number>
  total: Ref<number>
  data: Ref<T[]>
  paginatedData: Ref<T[]>
  pageSizes: number[]
  handleSizeChange: () => void
  handleCurrentChange: () => void
  setData: (newData: T[]) => void
  reset: () => void
}

export function usePagination<T>(
  initialData: Ref<T[]> | T[] = [],
  options: PaginationOptions = {}
): UsePaginationReturn<T> {
  const { defaultPageSize = 50, pageSizes = [50, 100, 200] } = options

  const currentPage = ref(1)
  const pageSize = ref(defaultPageSize)
  const total = ref(0)
  const data = ref<T[]>(Array.isArray(initialData) ? initialData : []) as Ref<T[]>

  const paginatedData = computed(() => {
    const start = (currentPage.value - 1) * pageSize.value
    const end = start + pageSize.value
    return data.value.slice(start, end)
  })

  function handleSizeChange() {
    currentPage.value = 1
  }

  function handleCurrentChange() {
    // 页码变化时自动更新表格数据（通过 computed 自动响应）
  }

  function setData(newData: T[]) {
    data.value = newData
    total.value = newData.length
    // 如果当前页超出范围，重置到第一页
    const maxPage = Math.ceil(newData.length / pageSize.value) || 1
    if (currentPage.value > maxPage) {
      currentPage.value = maxPage
    }
  }

  function reset() {
    currentPage.value = 1
    pageSize.value = defaultPageSize
    data.value = []
    total.value = 0
  }

  // 监听 data 变化，自动更新 total
  watch(data, (newData) => {
    total.value = newData.length
  }, { immediate: true })

  return {
    currentPage,
    pageSize,
    total,
    data,
    paginatedData,
    pageSizes,
    handleSizeChange,
    handleCurrentChange,
    setData,
    reset,
  }
}
