import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import 'cropperjs/dist/cropper.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
import App from './App.vue'
import router from './router'
import './styles/theme.css'
import './styles/animations.css'
import './styles/responsive.css'
import './styles/admin-components.css'
import './styles/teacher-ui.css'
import { permissionDirective, roleDirective } from './directives/permission'
import { startSiteConfigSync } from './composables/useSiteConfig'

// 启动站点品牌同步：登录页与各端口统一读取管理端下发的站点名称/Logo/吉祥物/公告
startSiteConfigSync()

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })

// 注册权限指令
app.directive('permission', permissionDirective)
app.directive('role', roleDirective)

app.mount('#app')
