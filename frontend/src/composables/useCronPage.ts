import { ref } from 'vue'

/**
 * 定时任务视图的开关状态（模块级单例）。
 *
 * 这个视图不是覆盖式子页，而是**对话区内的第二种视图**：打开时把 ChatPanel 的消息区
 * 换成任务清单，侧边栏 / 底部导航留在原位。入口有两处、分属不同组件树：
 * 侧边栏「新对话」下面的一行、移动端聊天顶栏的时钟按钮。
 * 用一份共享状态把「谁打开」与「谁渲染」解耦，免得把 open 事件一路透传到 ChatShell 再回传 prop。
 */
const visible = ref(false)

export function useCronPage() {
  return {
    cronVisible: visible,
    openCron: () => { visible.value = true },
    closeCron: () => { visible.value = false },
    /** 侧边栏入口按导航语义处理：已在定时任务视图时再点一次，回到对话 */
    toggleCron: () => { visible.value = !visible.value },
  }
}
