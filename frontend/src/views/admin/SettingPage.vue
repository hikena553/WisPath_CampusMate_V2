<template>
  <div class="setting-page">
    <div class="page-header">
      <h2 class="text-gradient">系统设置</h2>
      <p class="subtitle">管理系统配置参数</p>
    </div>

    <div class="setting-sections" v-loading="loading">
      <!-- 基础设置 -->
      <div class="setting-section">
        <div class="section-title">
          <el-icon><Setting /></el-icon> 基础设置
        </div>
        <div class="setting-list">
          <div class="setting-item">
            <div class="setting-info">
              <div class="setting-name">系统名称 <span class="required">*</span></div>
              <div class="setting-desc">显示在页面标题和导航栏的名称</div>
            </div>
            <el-input v-model="settingsMap['site_name']" placeholder="请输入系统名称" style="width: 300px" />
          </div>
          <div class="setting-item">
            <div class="setting-info">
              <div class="setting-name">系统公告</div>
              <div class="setting-desc">显示在首页的公告内容</div>
            </div>
            <el-input v-model="settingsMap['site_announcement']" type="textarea" :rows="3" placeholder="请输入公告内容" style="width: 300px" />
          </div>
        </div>
      </div>

      <!-- AI设置 -->
      <div class="setting-section ai-section">
        <div class="section-title">
          <el-icon><ChatDotRound /></el-icon> AI助手设置
          <el-tag v-if="aiConfigured" type="success" size="small" effect="plain" style="margin-left: 8px">已配置</el-tag>
          <el-tag v-else type="warning" size="small" effect="plain" style="margin-left: 8px">未配置</el-tag>
        </div>
        <div class="setting-list">
          <div class="setting-item">
            <div class="setting-info">
              <div class="setting-name">API Key <span class="required">*</span></div>
              <div class="setting-desc">通义千问API密钥，在阿里云控制台获取</div>
            </div>
            <el-input v-model="settingsMap['llm_api_key']" placeholder="请输入API Key" type="password" show-password style="width: 300px" />
          </div>
          <div class="setting-item">
            <div class="setting-info">
              <div class="setting-name">API 地址</div>
              <div class="setting-desc">API接口地址，默认使用阿里云通义千问</div>
            </div>
            <el-input v-model="settingsMap['llm_base_url']" placeholder="需以 /v1 结尾，如 https://dashscope.aliyuncs.com/compatible-mode/v1" style="width: 360px" />
          </div>
          <div class="setting-item">
            <div class="setting-info">
              <div class="setting-name">AI模型 <span class="required">*</span></div>
              <div class="setting-desc">填写模型名称，如 qwen-turbo、gpt-4、claude-3 等</div>
            </div>
            <el-input v-model="settingsMap['llm_model']" placeholder="例: qwen-turbo" style="width: 200px" />
          </div>
          <div class="setting-item">
            <div class="setting-info">
              <div class="setting-name">智能体模型</div>
              <div class="setting-desc">智能体使用的模型，可与主模型不同</div>
            </div>
            <el-input v-model="settingsMap['llm_agent_model']" placeholder="留空则使用主模型" style="width: 200px" />
          </div>
          <div class="setting-item">
            <div class="setting-info">
              <div class="setting-name">最大对话轮数</div>
              <div class="setting-desc">每次对话保留的最大消息数</div>
            </div>
            <el-input-number v-model="settingsMap['max_chat_history']" :min="10" :max="100" />
          </div>
          <div class="setting-item">
            <div class="setting-info">
              <div class="setting-name">Temperature</div>
              <div class="setting-desc">控制输出随机性，0=确定性，1=创造性</div>
            </div>
            <el-slider v-model="aiTemperature" :min="0" :max="1" :step="0.1" style="width: 200px" show-input />
          </div>
          <div class="setting-item">
            <div class="setting-info">
              <div class="setting-name">最大Token数</div>
              <div class="setting-desc">单次回复的最大长度</div>
            </div>
            <el-input-number v-model="aiMaxTokens" :min="1000" :max="50000" :step="1000" />
          </div>
        </div>
        <div class="ai-actions">
          <el-button type="primary" @click="handleSaveAI" :loading="savingAI">
            <el-icon><Check /></el-icon> 保存AI配置
          </el-button>
          <el-button @click="testAIConnection" :loading="testing">
            <el-icon><Connection /></el-icon> 测试连接
          </el-button>
        </div>
      </div>

      <!-- 预警设置 -->
      <div class="setting-section">
        <div class="section-title">
          <el-icon><Warning /></el-icon> 危机预警设置
        </div>
        <div class="setting-list">
          <div class="setting-item">
            <div class="setting-info">
              <div class="setting-name">预警敏感词</div>
              <div class="setting-desc">触发预警的关键词，用逗号分隔</div>
            </div>
            <el-input v-model="settingsMap['crisis_keywords']" type="textarea" :rows="2" placeholder="关键词1,关键词2,..." style="width: 300px" />
          </div>
          <div class="setting-item">
            <div class="setting-info">
              <div class="setting-name">自动通知辅导员</div>
              <div class="setting-desc">发现高危预警时自动通知辅导员</div>
            </div>
            <el-switch v-model="settingsMap['auto_notify_counselor']" active-value="true" inactive-value="false" />
          </div>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div class="setting-actions">
        <el-button type="primary" @click="handleSave" :loading="saving">
          <el-icon><Check /></el-icon> 保存所有设置
        </el-button>
        <el-button @click="loadSettings">
          <el-icon><Refresh /></el-icon> 重新加载
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { Setting, ChatDotRound, Warning, Check, Refresh, Connection } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getSettings, batchUpdateSettings, type Setting as SettingType } from '@/api/setting'

const loading = ref(false)
const saving = ref(false)
const savingAI = ref(false)
const testing = ref(false)
const settings = ref<SettingType[]>([])
const settingsMap = reactive<Record<string, string>>({})
const aiTemperature = ref(0.7)
const aiMaxTokens = ref(10000)

const aiConfigured = computed(() => {
  return !!(settingsMap['llm_api_key'] && settingsMap['llm_model'])
})

async function loadSettings() {
  loading.value = true
  try {
    const data = await getSettings()
    settings.value = data
    data.forEach(s => {
      if (s.key && s.value !== undefined) {
        settingsMap[s.key] = s.value
      }
    })
    // 加载AI相关数值设置
    if (settingsMap['llm_agent_temperature']) {
      aiTemperature.value = parseFloat(settingsMap['llm_agent_temperature']) || 0.7
    }
    if (settingsMap['llm_agent_max_tokens']) {
      aiMaxTokens.value = parseInt(settingsMap['llm_agent_max_tokens']) || 10000
    }
  } catch (error) {
    console.error('加载设置失败:', error)
  } finally {
    loading.value = false
  }
}

function validateBasicSettings(): boolean {
  if (!settingsMap['site_name']?.trim()) {
    ElMessage.warning('请填写系统名称')
    return false
  }
  return true
}

function validateAISettings(): boolean {
  if (!settingsMap['llm_api_key']?.trim()) {
    ElMessage.warning('请填写API Key')
    return false
  }
  if (!settingsMap['llm_model']) {
    ElMessage.warning('请选择AI模型')
    return false
  }
  return true
}

async function handleSave() {
  if (!validateBasicSettings()) return
  saving.value = true
  try {
    await batchUpdateSettings(settingsMap)
    ElMessage.success('设置已保存')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

async function handleSaveAI() {
  if (!validateAISettings()) return
  savingAI.value = true
  try {
    const aiSettings: Record<string, string> = {
      llm_api_key: settingsMap['llm_api_key'] || '',
      llm_base_url: settingsMap['llm_base_url'] || '',
      llm_model: settingsMap['llm_model'] || '',
      llm_agent_model: settingsMap['llm_agent_model'] || '',
      llm_agent_temperature: aiTemperature.value.toString(),
      llm_agent_max_tokens: aiMaxTokens.value.toString(),
      max_chat_history: settingsMap['max_chat_history'] || '50',
    }
    await batchUpdateSettings(aiSettings)
    ElMessage.success('AI配置已保存')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    savingAI.value = false
  }
}

async function testAIConnection() {
  if (!settingsMap['llm_api_key']?.trim()) {
    ElMessage.warning('请先填写API Key')
    return
  }
  testing.value = true
  try {
    const aiSettings: Record<string, string> = {
      llm_api_key: settingsMap['llm_api_key'] || '',
      llm_base_url: settingsMap['llm_base_url'] || '',
      llm_model: settingsMap['llm_model'] || '',
    }
    await batchUpdateSettings(aiSettings)

    const token = (await import('@/utils/token')).getToken()
    const response = await fetch('/api/agent/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        message: '你好，请回复"连接成功"',
        history: [],
      }),
    })

    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      ElMessage.error(`连接测试失败: ${data.detail || '未知错误'}`)
      return
    }

    const reader = response.body!.getReader()
    const decoder = new TextDecoder()
    const { value } = await reader.read()
    const firstChunk = decoder.decode(value)
    reader.cancel()

    const errorMsg = '抱歉，我暂时无法回答'
    if (firstChunk.includes(errorMsg)) {
      ElMessage.error('连接测试失败: AI模型返回错误。请检查：\n1. API 地址格式是否正确（需完整包含 /v1/chat/completions 路径）\n2. 模型名称在该 API 地址下是否存在\n3. API Key 是否有效')
    } else {
      ElMessage.success('AI连接测试成功！模型可正常使用')
    }
  } catch (error) {
    ElMessage.error('连接测试失败，请检查网络和配置')
  } finally {
    testing.value = false
  }
}

onMounted(() => {
  loadSettings()
})
</script>

<style scoped>
.setting-page {
  padding: 24px;
  height: 100%;
  overflow-y: auto;
}

.page-header {
  margin-bottom: 24px;
}

.page-header h2 {
  font-size: 24px;
  font-weight: 700;
  margin: 0 0 8px;
}

.subtitle {
  color: #666;
  font-size: 14px;
  margin: 0;
}

.text-gradient {
  background: linear-gradient(135deg, #409eff 0%, #67c23a 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.setting-sections {
  max-width: 800px;
}

.setting-section {
  background: #fff;
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 20px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
}

.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #1a1a2e;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f0f0;
}

.setting-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.setting-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.setting-info {
  flex: 1;
}

.setting-name {
  font-size: 14px;
  font-weight: 500;
  color: #333;
  margin-bottom: 4px;
}

.setting-desc {
  font-size: 12px;
  color: #999;
}

.setting-actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}

.required {
  color: #f56c6c;
  margin-left: 2px;
}

.ai-section {
  border: 1px solid rgba(64, 158, 255, 0.2);
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.02), rgba(103, 194, 58, 0.02));
}

.ai-actions {
  display: flex;
  gap: 12px;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid #f0f0f0;
}
</style>
