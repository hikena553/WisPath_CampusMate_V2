<template>
  <div class="campus-vr">
    <h2 class="section-title">校园VR全景</h2>
    <div class="area-tabs">
      <el-radio-group v-model="currentArea" @change="switchArea">
        <el-radio-button value="anzhou">安州校区</el-radio-button>
        <el-radio-button value="youxian">游仙校区</el-radio-button>
      </el-radio-group>
    </div>
    <div class="toolbar">
      <el-button :type="addingMode ? 'danger' : 'primary'" size="small" @click="toggleAddMode">
        {{ addingMode ? '退出标注' : '添加标注' }}
      </el-button>
      <el-button size="small" @click="showManage = true">管理标注</el-button>
      <span v-if="addingMode" class="add-hint">点击全景图上的位置添加标注点</span>
    </div>
    <div ref="containerRef" class="panorama-container" :class="{ adding: addingMode }">
      <div
        v-for="poi in visiblePois"
        :key="poi.id"
        class="poi-marker"
        :style="{ left: poi.screenX + 'px', top: poi.screenY + 'px' }"
        @mouseenter="hoverPoi = poi.id"
        @mouseleave="hoverPoi = null"
        @click.stop="openDetail(poi)"
      >
        <div class="poi-dot" :class="{ hover: hoverPoi === poi.id }">
          <el-icon :size="18" color="#fff"><LocationFilled /></el-icon>
        </div>
        <div v-if="hoverPoi === poi.id" class="poi-label">{{ poi.name }}</div>
      </div>
    </div>
    <p class="hint">拖动旋转 · 滚轮缩放 · 悬停查看标注名称 · 点击查看详情</p>

    <el-dialog v-model="showForm" title="添加标注点" width="400px">
      <el-form :model="poiForm" label-width="70px">
        <el-form-item label="名称">
          <el-input v-model="poiForm.name" placeholder="如：图书馆" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="poiForm.description" type="textarea" :rows="3" placeholder="可选描述" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="poiForm.type">
            <el-option label="教学楼" value="building" />
            <el-option label="食堂" value="food" />
            <el-option label="图书馆" value="library" />
            <el-option label="宿舍" value="dorm" />
            <el-option label="运动场" value="sport" />
            <el-option label="其他" value="other" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showForm = false">取消</el-button>
        <el-button type="primary" @click="savePoi">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showDetail" title="标注详情" width="400px">
      <template v-if="selectedPoi">
        <div class="detail-icon">
          <el-icon :size="32" color="#409eff"><LocationFilled /></el-icon>
        </div>
        <h3>{{ selectedPoi.name }}</h3>
        <p class="detail-desc">{{ selectedPoi.description || '暂无描述' }}</p>
        <p class="detail-meta">类型：{{ typeLabel(selectedPoi.type) }}</p>
        <p class="detail-meta">经度：{{ selectedPoi.yaw?.toFixed(1) }}° 纬度：{{ selectedPoi.pitch?.toFixed(1) }}°</p>
      </template>
      <template #footer>
        <el-button type="danger" size="small" @click="deletePoi(selectedPoi!.id)">删除此标注</el-button>
        <el-button @click="showDetail = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showManage" title="管理标注" width="500px">
      <el-table :data="pois" style="width:100%">
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="type" label="类型" width="100">
          <template #default="{ row }">{{ typeLabel(row.type) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button text type="danger" size="small" @click="deletePoi(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <template v-if="pois.length === 0">
        <el-empty description="暂无标注" />
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { LocationFilled } from '@element-plus/icons-vue'
import * as THREE from 'three'

interface PoiItem {
  id: number
  name: string
  description: string
  type: string
  yaw: number
  pitch: number
  screenX?: number
  screenY?: number
}

const containerRef = ref<HTMLDivElement>()
const currentArea = ref('anzhou')
const addingMode = ref(false)
const showForm = ref(false)
const showDetail = ref(false)
const showManage = ref(false)
const hoverPoi = ref<number | null>(null)
const selectedPoi = ref<PoiItem | null>(null)
const pois = ref<PoiItem[]>([])
const nextId = ref(1)

const poiForm = reactive({ name: '', description: '', type: 'building' })

let scene: THREE.Scene
let camera: THREE.PerspectiveCamera
let renderer: THREE.WebGLRenderer
let sphere: THREE.Mesh
let isDragging = false
let dragStart = { x: 0, y: 0 }
let animationId: number
let capturedYaw = 0
let capturedPitch = 0

const panoramas: Record<string, string> = {
  anzhou: '/images/01.png',
  youxian: '/images/01.png',
}

const typeLabelMap: Record<string, string> = {
  building: '教学楼', food: '食堂', library: '图书馆', dorm: '宿舍', sport: '运动场', other: '其他',
}
function typeLabel(t: string) { return typeLabelMap[t] || t }

const visiblePois = computed(() => pois.value.filter(p => p.screenX != null && p.screenY != null))

function loadPois() {
  const key = `campus_pois_${currentArea.value}`
  try {
    const raw = localStorage.getItem(key)
    if (raw) {
      pois.value = JSON.parse(raw)
      nextId.value = pois.value.reduce((max, p) => Math.max(max, p.id), 0) + 1
    } else {
      pois.value = []
    }
  } catch { pois.value = [] }
}

function savePois() {
  const key = `campus_pois_${currentArea.value}`
  localStorage.setItem(key, JSON.stringify(pois.value))
}

function initScene() {
  scene = new THREE.Scene()
  camera = new THREE.PerspectiveCamera(75, containerRef.value!.clientWidth / containerRef.value!.clientHeight, 0.1, 1000)
  camera.position.set(0, 0, 0.1)
  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(containerRef.value!.clientWidth, containerRef.value!.clientHeight)
  containerRef.value!.appendChild(renderer.domElement)
  animate()
}

function createPanorama(imageUrl: string) {
  if (sphere) scene.remove(sphere)
  const geometry = new THREE.SphereGeometry(100, 64, 64)
  const textureLoader = new THREE.TextureLoader()
  const texture = textureLoader.load(imageUrl)
  texture.colorSpace = THREE.SRGBColorSpace
  const material = new THREE.MeshBasicMaterial({ map: texture, side: THREE.BackSide })
  sphere = new THREE.Mesh(geometry, material)
  scene.add(sphere)
}

function animate() {
  animationId = requestAnimationFrame(animate)
  projectPois()
  camera.updateProjectionMatrix()
  renderer.render(scene, camera)
}

function projectPois() {
  if (!containerRef.value || !camera) return
  const w = containerRef.value.clientWidth
  const h = containerRef.value.clientHeight
  const vec = new THREE.Vector3()
  for (const poi of pois.value) {
    const yaw = THREE.MathUtils.degToRad(poi.yaw)
    const pitch = THREE.MathUtils.degToRad(poi.pitch)
    vec.set(
      100 * Math.cos(pitch) * Math.sin(yaw),
      100 * Math.sin(pitch),
      100 * Math.cos(pitch) * Math.cos(yaw),
    )
    vec.project(camera)
    if (vec.z > 1) {
      poi.screenX = undefined
      poi.screenY = undefined
    } else {
      poi.screenX = (vec.x * 0.5 + 0.5) * w
      poi.screenY = (-vec.y * 0.5 + 0.5) * h
    }
  }
}

function sphericalFromClick(clientX: number, clientY: number) {
  const rect = containerRef.value!.getBoundingClientRect()
  const x = ((clientX - rect.left) / rect.width) * 2 - 1
  const y = -((clientY - rect.top) / rect.height) * 2 + 1
  const raycaster = new THREE.Raycaster()
  const mouse = new THREE.Vector2(x, y)
  raycaster.setFromCamera(mouse, camera)
  const intersects = raycaster.intersectObject(sphere)
  if (intersects.length > 0) {
    const point = intersects[0].point
    const yaw = Math.atan2(point.x, point.z)
    const pitch = Math.asin(point.y / 100)
    return { yaw: THREE.MathUtils.radToDeg(yaw), pitch: THREE.MathUtils.radToDeg(pitch) }
  }
  return null
}

function onMouseDown(e: MouseEvent) {
  isDragging = true
  dragStart = { x: e.clientX, y: e.clientY }
}

function onMouseUp(e: MouseEvent) {
  const dx = e.clientX - dragStart.x
  const dy = e.clientY - dragStart.y
  const dist = Math.sqrt(dx * dx + dy * dy)
  if (dist < 5) {
    if (addingMode.value) {
      const coords = sphericalFromClick(e.clientX, e.clientY)
      if (coords) {
        capturedYaw = coords.yaw
        capturedPitch = coords.pitch
        poiForm.name = ''
        poiForm.description = ''
        poiForm.type = 'building'
        showForm.value = true
      }
    }
  }
  isDragging = false
}

function onMouseMove(e: MouseEvent) {
  if (!isDragging) return
  const deltaX = e.clientX - dragStart.x
  const deltaY = e.clientY - dragStart.y
  const rotation = new THREE.Quaternion().setFromEuler(new THREE.Euler(0, deltaX * 0.005, 0))
  camera.quaternion.multiplyQuaternions(rotation, camera.quaternion)
  const rotationY = new THREE.Quaternion().setFromEuler(new THREE.Euler(deltaY * 0.005, 0, 0))
  camera.quaternion.multiplyQuaternions(rotationY, camera.quaternion)
  dragStart = { x: e.clientX, y: e.clientY }
}

function onResize() {
  if (!containerRef.value || !renderer) return
  const w = containerRef.value.clientWidth
  const h = containerRef.value.clientHeight
  camera.aspect = w / h
  renderer.setSize(w, h)
}

function switchArea(area: string) {
  currentArea.value = area
  createPanorama(panoramas[area])
  loadPois()
}

function toggleAddMode() {
  addingMode.value = !addingMode.value
}

function savePoi() {
  if (!poiForm.name) {
    ElMessage.warning('请输入名称')
    return
  }
  const poi: PoiItem = {
    id: nextId.value++,
    name: poiForm.name,
    description: poiForm.description,
    type: poiForm.type,
    yaw: capturedYaw,
    pitch: capturedPitch,
  }
  pois.value.push(poi)
  savePois()
  showForm.value = false
  ElMessage.success('标注已添加')
}

function openDetail(poi: PoiItem) {
  selectedPoi.value = poi
  showDetail.value = true
}

function deletePoi(id: number) {
  pois.value = pois.value.filter(p => p.id !== id)
  savePois()
  showDetail.value = false
  ElMessage.success('已删除')
}

watch(currentArea, () => loadPois())

onMounted(() => {
  initScene()
  createPanorama(panoramas.anzhou)
  loadPois()
  const el = containerRef.value!
  el.addEventListener('mousedown', onMouseDown)
  window.addEventListener('mousemove', onMouseMove)
  window.addEventListener('mouseup', onMouseUp)
  window.addEventListener('resize', onResize)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(animationId)
  renderer?.dispose()
  window.removeEventListener('mousemove', onMouseMove)
  window.removeEventListener('mouseup', onMouseUp)
  window.removeEventListener('resize', onResize)
})
</script>

<style scoped>
.campus-vr { padding: 40px 0; text-align: center; }
.section-title { font-size: 28px; color: #333; margin-bottom: 20px; }
.area-tabs { margin-bottom: 12px; }
.toolbar { display: flex; align-items: center; justify-content: center; gap: 8px; margin-bottom: 12px; }
.add-hint { color: #e6a23c; font-size: 13px; margin-left: 8px; }
.panorama-container { position: relative; width: 100%; height: 500px; border-radius: 12px; overflow: hidden; cursor: grab; }
.panorama-container:active { cursor: grabbing; }
.panorama-container.adding { cursor: crosshair; outline: 2px dashed #e6a23c; }
.hint { color: #999; font-size: 13px; margin-top: 8px; }
.poi-marker { position: absolute; transform: translate(-50%, -50%); pointer-events: auto; z-index: 10; }
.poi-dot { width: 32px; height: 32px; background: #409eff; border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 2px 8px rgba(64,158,255,0.5); transition: transform 0.2s; cursor: pointer; }
.poi-dot.hover { transform: scale(1.3); }
.poi-label { position: absolute; left: 50%; top: 40px; transform: translateX(-50%); white-space: nowrap; background: rgba(0,0,0,0.75); color: #fff; padding: 4px 12px; border-radius: 4px; font-size: 13px; pointer-events: none; }
.detail-icon { text-align: center; margin-bottom: 12px; }
.detail-icon h3 { font-size: 20px; color: #333; text-align: center; margin-bottom: 12px; }
.detail-desc { color: #666; font-size: 14px; line-height: 1.6; margin-bottom: 8px; }
.detail-meta { color: #999; font-size: 12px; margin-bottom: 4px; }
</style>
