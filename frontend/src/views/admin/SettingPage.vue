<template>
  <div class="setting-page" ref="pageRef" @scroll.passive="onPageScroll">
    <!-- 页头 -->
    <div class="page-title-row">
      <div class="page-title-left">
        <div class="page-title-icon"><el-icon :size="20"><Settings /></el-icon></div>
        <div>
          <h2 class="page-title">系统设置</h2>
          <p class="page-sub">管理系统配置参数，保存后全站即时生效</p>
        </div>
      </div>
      <div class="page-title-actions">
        <el-button :loading="saving" type="primary" @click="handleSave">
          <el-icon><Check /></el-icon> 保存所有设置
        </el-button>
        <el-button :loading="loading" @click="loadAll">
          <el-icon><RefreshCw /></el-icon> 重新加载
        </el-button>
      </div>
    </div>

    <div class="setting-body">
      <!-- 左侧分组导航（参考高星开源后台设置页布局：分组锚点 + 右侧内容） -->
      <aside class="setting-nav">
        <div class="nav-title">设置分组</div>
        <div
          v-for="g in groups"
          :key="g.key"
          class="nav-item"
          :class="{ active: activeSection === g.key }"
          @click="scrollToSection(g.key)"
        >
          <span class="nav-icon"><el-icon :size="18"><component :is="g.icon" /></el-icon></span>
          <div class="nav-label">
            <div class="nav-name">{{ g.label }}</div>
            <div class="nav-desc">{{ g.desc }}</div>
          </div>
          <el-tag
            v-if="g.key === 'ai'"
            class="nav-status"
            :type="aiConfigured ? 'success' : 'warning'"
            size="small"
            effect="light"
            round
          >{{ aiConfigured ? '已配置' : '未配置' }}</el-tag>
          <el-tag
            v-else-if="g.key === 'voice'"
            class="nav-status"
            :type="voiceKeyConfigured ? 'success' : 'info'"
            size="small"
            effect="light"
            round
          >{{ voiceKeyConfigured ? '可用' : '待配置' }}</el-tag>
        </div>
      </aside>

      <!-- 右侧设置内容 -->
      <div class="setting-content">
        <div v-if="loading" class="setting-loading">正在加载设置…</div>
        <template v-else>
        <!-- ============ 通用 / 基础设置 ============ -->
        <section id="sec-basic" class="setting-section">
          <div class="section-header">
            <div class="section-header-icon blue"><el-icon><Settings /></el-icon></div>
            <div class="section-header-info">
              <div class="section-title">基础设置</div>
              <div class="section-desc">站点名称与公告信息</div>
            </div>
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
              <el-input v-model="settingsMap['site_announcement']" type="textarea" :rows="3" placeholder="请输入公告内容" style="width: 360px" />
            </div>
          </div>
        </section>

        <!-- ============ AI 助手 ============ -->
        <section id="sec-ai" class="setting-section ai-section">
          <div class="section-header">
            <div class="section-header-icon violet"><el-icon><MessageSquare /></el-icon></div>
            <div class="section-header-info">
              <div class="section-title">
                AI 助手设置
                <el-tag v-if="aiConfigured" type="success" size="small" effect="light" round>已配置</el-tag>
                <el-tag v-else type="warning" size="small" effect="light" round>未配置</el-tag>
              </div>
              <div class="section-desc">大模型 API 接入配置，支持百炼 Token Plan 等 OpenAI 兼容端点</div>
            </div>
          </div>
          <div class="setting-list">
            <div class="setting-item">
              <div class="setting-info">
                <div class="setting-name">API Key <span class="required">*</span></div>
                <div class="setting-desc">百炼 Token Plan API Key（sk-sp- 开头），在阿里云百炼控制台获取；已配置时显示脱敏值，点击输入框可直接输入新 Key 覆盖</div>
              </div>
              <el-input
                v-model="settingsMap['llm_api_key']"
                placeholder="请输入 Token Plan API Key（sk-sp- 开头）"
                type="text"
                style="width: 300px"
                @focus="onSensitiveFocus('llm_api_key')"
                @blur="restoreSensitiveOnBlur('llm_api_key')"
              />
            </div>
            <div class="setting-item">
              <div class="setting-info">
                <div class="setting-name">API 地址</div>
                <div class="setting-desc">API接口地址，Token Plan 使用 OpenAI 兼容端点</div>
              </div>
              <el-input v-model="settingsMap['llm_base_url']" placeholder="如 https://token-plan.cn-beijing.maas.aliyuncs.com/compatible-mode/v1" style="width: 360px" />
            </div>
            <div class="setting-item">
              <div class="setting-info">
                <div class="setting-name">AI模型 <span class="required">*</span></div>
                <div class="setting-desc">填写模型名称，如 qwen3.8-max、deepseek-v4-flash-0731</div>
              </div>
              <el-input v-model="settingsMap['llm_model']" placeholder="例: deepseek-v4-flash-0731" style="width: 200px" />
            </div>
            <div class="setting-item">
              <div class="setting-info">
                <div class="setting-name">智能体模型</div>
                <div class="setting-desc">智能体使用的模型，默认与主模型一致，留空则使用主模型</div>
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
              <el-slider v-model="aiTemperature" :min="0" :max="1" :step="0.1" style="width: 220px" show-input />
            </div>
            <div class="setting-item">
              <div class="setting-info">
                <div class="setting-name">最大Token数</div>
                <div class="setting-desc">单次回复的最大长度</div>
              </div>
              <el-input-number v-model="aiMaxTokens" :min="1000" :max="50000" :step="1000" />
            </div>
            <div class="setting-item">
              <div class="setting-info">
                <div class="setting-name">语音服务 API Key（可选）</div>
                <div class="setting-desc">语音识别/合成默认复用上方 LLM API Key（千问 qwen-audio-3.0 系列）；仅当使用独立百炼 Key 时才需单独填写</div>
              </div>
              <el-input
                v-model="settingsMap['dashscope_api_key']"
                placeholder="留空则复用 LLM API Key"
                style="width: 300px"
                @focus="onSensitiveFocus('dashscope_api_key')"
              />
            </div>
            <div class="setting-item">
              <div class="setting-info">
                <div class="setting-name">自我称谓</div>
                <div class="setting-desc">AI 助手在对话中的自称，如"绵小城"，用于系统提示词与欢迎语</div>
              </div>
              <el-input v-model="settingsMap['agent_name']" placeholder="例：绵小城" style="width: 200px" />
            </div>
            <div class="setting-item system-prompt-item">
              <div class="setting-info">
                <div class="setting-name">系统提示词</div>
                <div class="setting-desc">自定义 AI 助手角色设定与回复规则，覆盖内置默认提示词；支持占位符 {agent_name} {greeting} {college} {today}，留空使用内置默认</div>
              </div>
              <el-input
                v-model="settingsMap['system_prompt']"
                type="textarea"
                :rows="6"
                placeholder="例如：你是{college}的智慧校园AI助手{agent_name}，请用中文简洁回答...（留空则使用内置系统提示词）"
                style="width: 480px"
              />
            </div>
          </div>
          <div class="ai-actions">
            <el-button type="primary" @click="handleSaveAI" :loading="savingAI">
              <el-icon><Check /></el-icon> 保存AI配置
            </el-button>
            <el-button @click="testAIConnection" :loading="testing">
              <el-icon><Plug /></el-icon> 测试连接
            </el-button>
          </div>
        </section>

        <!-- ============ 危机预警 ============ -->
        <section id="sec-alert" class="setting-section">
          <div class="section-header">
            <div class="section-header-icon orange"><el-icon><TriangleAlert /></el-icon></div>
            <div class="section-header-info">
              <div class="section-title">危机预警设置</div>
              <div class="section-desc">敏感词识别与辅导员自动通知配置</div>
            </div>
          </div>
          <div class="setting-list">
            <div class="setting-item">
              <div class="setting-info">
                <div class="setting-name">预警敏感词</div>
                <div class="setting-desc">命中任一词语即进入语义分级，保存后实时生效；未配置时使用默认词库（与「危机预警」页保持一致）</div>
              </div>
              <el-input v-model="settingsMap['crisis_keywords']" type="textarea" :rows="2" placeholder="关键词1,关键词2,..." style="width: 360px" />
            </div>
            <div class="setting-item">
              <div class="setting-info">
                <div class="setting-name">自动通知辅导员</div>
                <div class="setting-desc">产生严重 / 中度预警时自动推送通知辅导员</div>
              </div>
              <el-switch v-model="settingsMap['auto_notify_counselor']" active-value="true" inactive-value="false" />
            </div>
          </div>
        </section>

        <!-- ============ 品牌设计 ============ -->
        <section id="sec-brand" class="setting-section brand-section">
          <div class="section-header">
            <div class="section-header-icon green"><el-icon><Image /></el-icon></div>
            <div class="section-header-info">
              <div class="section-title">
                Logo / 吉祥物设计
                <el-tag size="small" effect="light" round>AI 生成 / 本地上传</el-tag>
              </div>
              <div class="section-desc">输入提示词由 AI 生成候选图，或直接上传本地图片，应用后顶栏与全站即刻生效</div>
            </div>
          </div>
          <div class="brand-grid">
            <!-- Logo 卡片 -->
            <div class="brand-card">
              <div class="brand-card-head">
                <div class="brand-card-title">系统 Logo</div>
                <el-radio-group v-model="logoSection.mode" size="small">
                  <el-radio-button value="ai">AI 生成</el-radio-button>
                  <el-radio-button value="upload">本地上传</el-radio-button>
                </el-radio-group>
              </div>

              <div class="brand-preview">
                <el-image v-if="logoDisplay" :src="logoDisplay" fit="contain" class="brand-preview-img" />
                <div class="brand-preview-badge" :class="brandStatus(logoSection).kind">
                  <el-icon :size="12"><component :is="brandStatusIcon(logoSection)" /></el-icon>
                  {{ brandStatus(logoSection).text }}
                </div>
              </div>

              <template v-if="logoSection.mode === 'ai'">
                <div class="brand-composer">
                  <el-input
                    v-model="logoSection.prompt"
                    type="textarea"
                    :rows="2"
                    placeholder="描述 Logo 风格，如：圆角盾形校徽，蓝金配色，中央书本与灯塔，扁平化设计，纯白背景"
                  />
                  <el-button type="primary" class="composer-btn" :loading="logoSection.generating" @click="handleGenerate(logoSection)">
                    <el-icon><Sparkles /></el-icon> 生成候选图
                  </el-button>
                </div>
                <div v-if="logoSection.candidates.length" class="brand-candidates">
                  <div
                    v-for="(img, i) in logoSection.candidates"
                    :key="img"
                    class="candidate"
                    :class="{ active: logoSection.selected === img }"
                    @click="logoSection.selected = img"
                  >
                    <el-image :src="img" fit="cover" class="candidate-img" />
                    <span class="candidate-index">{{ i + 1 }}</span>
                    <div v-if="logoSection.selected === img" class="candidate-check"><el-icon><Check /></el-icon></div>
                  </div>
                </div>
                <div v-else class="brand-idle-tip">
                  <el-icon :size="12"><Info /></el-icon>
                  输入描述后点击「生成候选图」，或切换「本地上传」直接选择图片
                </div>
              </template>
              <template v-else>
                <div class="brand-composer upload">
                  <el-upload drag :show-file-list="false" :before-upload="(f: File) => handleUpload(logoSection, f)" accept=".png,.jpg,.jpeg,.webp,.gif">
                    <el-icon class="upload-icon"><Upload /></el-icon>
                    <div class="el-upload__text">拖拽图片到此处，或 <em>点击上传</em></div>
                    <template #tip>
                      <div class="el-upload__tip">支持 png / jpg / webp / gif，不超过 15MB</div>
                    </template>
                  </el-upload>
                </div>
              </template>

              <div class="brand-save">
                <div class="brand-save-hint"><el-icon :size="12"><Info /></el-icon> {{ brandHint(logoSection) }}</div>
                <div class="brand-save-actions">
                  <el-button type="primary" size="small" :loading="savingBrand" :disabled="!logoSection.selected" @click="handleApply(logoSection)">
                    <el-icon><Check /></el-icon> 应用此图片为 Logo
                  </el-button>
                  <el-button size="small" @click="handleReset(logoSection)">恢复默认</el-button>
                </div>
              </div>
            </div>

            <!-- 吉祥物卡片 -->
            <div class="brand-card">
              <div class="brand-card-head">
                <div class="brand-card-title">校园吉祥物</div>
                <el-radio-group v-model="mascotSection.mode" size="small">
                  <el-radio-button value="ai">AI 生成</el-radio-button>
                  <el-radio-button value="upload">本地上传</el-radio-button>
                </el-radio-group>
              </div>

              <div class="brand-preview">
                <el-image v-if="mascotDisplay" :src="mascotDisplay" fit="contain" class="brand-preview-img" />
                <div class="brand-preview-badge" :class="brandStatus(mascotSection).kind">
                  <el-icon :size="12"><component :is="brandStatusIcon(mascotSection)" /></el-icon>
                  {{ brandStatus(mascotSection).text }}
                </div>
              </div>

              <template v-if="mascotSection.mode === 'ai'">
                <div class="brand-composer">
                  <el-input
                    v-model="mascotSection.prompt"
                    type="textarea"
                    :rows="2"
                    placeholder="描述吉祥物，如：圆润可爱的科技小机器人，蓝色主色调，胸前有校徽，手比爱心，3D 渲染，纯白背景"
                  />
                  <el-button type="primary" class="composer-btn" :loading="mascotSection.generating" @click="handleGenerate(mascotSection)">
                    <el-icon><Sparkles /></el-icon> 生成候选图
                  </el-button>
                </div>
                <div v-if="mascotSection.candidates.length" class="brand-candidates">
                  <div
                    v-for="(img, i) in mascotSection.candidates"
                    :key="img"
                    class="candidate"
                    :class="{ active: mascotSection.selected === img }"
                    @click="mascotSection.selected = img"
                  >
                    <el-image :src="img" fit="cover" class="candidate-img" />
                    <span class="candidate-index">{{ i + 1 }}</span>
                    <div v-if="mascotSection.selected === img" class="candidate-check"><el-icon><Check /></el-icon></div>
                  </div>
                </div>
                <div v-else class="brand-idle-tip">
                  <el-icon :size="12"><Info /></el-icon>
                  输入描述后点击「生成候选图」，或切换「本地上传」直接选择图片
                </div>
              </template>
              <template v-else>
                <div class="brand-composer upload">
                  <el-upload drag :show-file-list="false" :before-upload="(f: File) => handleUpload(mascotSection, f)" accept=".png,.jpg,.jpeg,.webp,.gif">
                    <el-icon class="upload-icon"><Upload /></el-icon>
                    <div class="el-upload__text">拖拽图片到此处，或 <em>点击上传</em></div>
                    <template #tip>
                      <div class="el-upload__tip">支持 png / jpg / webp / gif，不超过 15MB</div>
                    </template>
                  </el-upload>
                </div>
              </template>

              <div class="brand-save">
                <div class="brand-save-hint"><el-icon :size="12"><Info /></el-icon> {{ brandHint(mascotSection) }}</div>
                <div class="brand-save-actions">
                  <el-button type="primary" size="small" :loading="savingBrand" :disabled="!mascotSection.selected" @click="handleApply(mascotSection)">
                    <el-icon><Check /></el-icon> 应用此图片为吉祥物
                  </el-button>
                  <el-button size="small" @click="handleReset(mascotSection)">恢复默认</el-button>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- ============ 语音与 TTS ============ -->
        <section id="sec-voice" class="setting-section voice-section">
          <div class="section-header">
            <div class="section-header-icon cyan"><el-icon><Mic /></el-icon></div>
            <div class="section-header-info">
              <div class="section-title">
                语音与 TTS
                <el-tag v-if="voiceKeyConfigured" type="success" size="small" effect="light" round>链路可用</el-tag>
                <el-tag v-else type="warning" size="small" effect="light" round>待配置 API Key</el-tag>
              </div>
              <div class="section-desc">语音通话全链路展示：识别 → 理解 → 合成，支持音色选择与播报风格提示词</div>
            </div>
          </div>

          <!-- ① 链路展示 -->
          <div class="pipe-wrap">
            <div class="pipe-head">
              <div class="pipe-head-title"><el-icon><Plug /></el-icon> 语音通话链路</div>
              <div class="pipe-head-tip">用户按住说话 → 识别为文本 → 大模型理解 → 边合成边播放（流式短语合成，首音 < 1s，支持随时打断）</div>
            </div>
            <div class="pipe-track">
              <div class="pipe-inner">
                <template v-for="(node, idx) in voicePipeline" :key="node.key">
                  <div class="pipe-node" :class="`c-${node.color}`">
                    <span class="pipe-zone" :class="node.zone === '客户端' ? 'zone-client' : 'zone-server'">{{ node.zone }}</span>
                    <div class="pipe-node-icon"><el-icon :size="20"><component :is="node.icon" /></el-icon></div>
                    <div class="pipe-node-title">{{ node.title }}</div>
                    <el-tooltip :content="node.desc" placement="top">
                      <div class="pipe-node-desc">{{ node.desc }}</div>
                    </el-tooltip>
                    <div class="pipe-chips">
                      <el-tooltip v-for="(c, ci) in node.chips" :key="ci" :content="c" placement="top">
                        <span class="pipe-chip">{{ c }}</span>
                      </el-tooltip>
                    </div>
                  </div>
                  <div v-if="idx < voicePipeline.length - 1" class="pipe-arrow">
                    <span class="pipe-arrow-line"></span>
                  </div>
                </template>
              </div>
            </div>
          </div>

          <!-- ② 音色设置 -->
          <div class="voice-sub">
            <div class="voice-sub-title">音色选择</div>
            <div class="setting-item">
              <div class="setting-info">
                <div class="setting-name">合成音色</div>
                <div class="setting-desc">
                  当前生效：<span class="mono-text">{{ effectiveVoice }}</span>。
                  Edge TTS 音色（{{ edgeVoicesCount }} 个）免费、无需 API Key；Token Plan 精品音色需 DashScope Key，Edge 故障时自动降级兜底
                </div>
              </div>
              <el-select
                v-model="settingsMap['llm_tts_voice']"
                filterable
                allow-create
                default-first-option
                clearable
                placeholder="选择或输入音色 ID"
                style="width: 380px"
              >
                <el-option-group v-if="edgeVoiceOptions.length" label="免费多音色 · Edge TTS（微软，无需 Key）">
                  <el-option
                    v-for="v in edgeVoiceOptions"
                    :key="v.voice"
                    :label="`${v.label}（${v.voice}）`"
                    :value="v.voice"
                  >
                    <div class="voice-option">
                      <span class="voice-option-name">{{ v.label }}</span>
                      <el-tag size="small" effect="plain" :type="v.gender === '男' ? 'primary' : 'danger'">{{ v.gender || '女' }}</el-tag>
                      <el-tag size="small" effect="plain" type="info">{{ v.tag }}</el-tag>
                    </div>
                    <div class="voice-option-value">{{ v.voice }}</div>
                  </el-option>
                </el-option-group>
                <el-option-group v-if="tokenplanVoiceOptions.length" label="精品中文 · Token Plan（qwen-plus，需 Key）">
                  <el-option
                    v-for="v in tokenplanVoiceOptions"
                    :key="v.voice"
                    :label="`${v.label}（${v.voice}）`"
                    :value="v.voice"
                  >
                    <div class="voice-option">
                      <span class="voice-option-name">{{ v.label }}</span>
                      <el-tag size="small" effect="plain" type="warning">{{ v.tag }}</el-tag>
                    </div>
                    <div class="voice-option-value">{{ v.voice }}</div>
                  </el-option>
                </el-option-group>
              </el-select>
            </div>

            <!-- 试听 -->
            <div class="setting-item voice-preview-item">
              <div class="setting-info">
                <div class="setting-name">音色试听</div>
                <div class="setting-desc">使用当前选择的音色合成一段示例语音，确认效果后再保存</div>
              </div>
              <div class="voice-preview">
                <el-input
                  v-model="previewText"
                  :rows="2"
                  type="textarea"
                  maxlength="200"
                  show-word-limit
                  placeholder="输入试听文本，如：你好，我是绵小城，很高兴为你服务。"
                  style="width: 340px"
                />
                <el-button type="primary" :loading="voiceTestLoading" @click="handleVoicePreview">
                  <el-icon><Play /></el-icon> 试听音色
                </el-button>
                <audio
                  v-if="audioSrc && !voiceTestLoading"
                  ref="voiceAudioRef"
                  :src="audioSrc"
                  controls
                  autoplay
                  class="voice-audio"
                  @error="handleVoiceAudioError"
                />
                <div v-if="voiceTestResult" class="voice-test-result"><el-icon><CircleCheck /></el-icon> {{ voiceTestResult }}</div>
              </div>
            </div>
          </div>

          <!-- ③ 播报风格提示词 -->
          <div class="voice-sub">
            <div class="voice-sub-title">播报风格提示词</div>
            <div class="setting-item system-prompt-item">
              <div class="setting-info">
                <div class="setting-name">语音播报风格</div>
                <div class="setting-desc">作用于语音通话链路中的大模型回复风格——让回答更口语化、简短、适合语音合成朗读。留空则使用默认问候式播报风格</div>
              </div>
              <div class="voice-prompt-wrap">
                <el-input
                  v-model="settingsMap['llm_tts_prompt']"
                  type="textarea"
                  :rows="4"
                  placeholder="例如：用温柔亲切的语气回复，句子简短，多用口语化表达，避免长句与生僻词，像朋友一样自然地聊天。"
                  style="width: 480px"
                />
                <div class="voice-prompt-examples">
                  <span class="example-label">快捷示例：</span>
                  <el-tag
                    v-for="ex in VOICE_PROMPT_EXAMPLES"
                    :key="ex.label"
                    class="example-tag"
                    size="small"
                    effect="plain"
                    round
                    @click="applyPromptExample(ex.text)"
                  >{{ ex.label }}</el-tag>
                  <el-button link type="primary" size="small" @click="settingsMap['llm_tts_prompt'] = ''">清空</el-button>
                </div>
              </div>
            </div>
          </div>

          <div class="ai-actions">
            <el-button type="primary" :loading="savingVoice" @click="handleSaveVoice">
              <el-icon><Check /></el-icon> 保存语音设置
            </el-button>
            <el-button :loading="voiceInfoLoading" @click="loadVoiceInfo">
              <el-icon><RefreshCw /></el-icon> 刷新链路状态
            </el-button>
          </div>
        </section>
        </template>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import {
  Settings, MessageSquare, TriangleAlert, Check, RefreshCw, Plug, Image,
  Sparkles, Upload, Mic, Monitor, Headphones, Play, CircleCheck,
  Clock, Info,
} from 'lucide-vue-next'
import { ElMessage } from 'element-plus'
import {
  getSettings, batchUpdateSettings, generateBrandingImages, uploadBrandingImage,
  getVoicePipelineInfo, testTtsPreview, type Setting as SettingType, type VoicePipelineInfo,
} from '@/api/setting'
import { getCrisisConfig } from '@/api/crisis'

const loading = ref(true)
const saving = ref(false)
const savingAI = ref(false)
const testing = ref(false)
const settings = ref<SettingType[]>([])
const settingsMap = reactive<Record<string, string>>({})
const aiTemperature = ref(0.7)
const aiMaxTokens = ref(10000)

// ===== 分组导航 =====
const activeSection = ref('basic')
const pageRef = ref<HTMLElement | null>(null)
const groups = [
  { key: 'basic', icon: Settings, label: '基础设置', desc: '站点名称与公告' },
  { key: 'ai', icon: MessageSquare, label: 'AI 助手', desc: '大模型与智能体' },
  { key: 'alert', icon: TriangleAlert, label: '危机预警', desc: '敏感词与通知' },
  { key: 'brand', icon: Image, label: '品牌设计', desc: 'Logo 与吉祥物' },
  { key: 'voice', icon: Mic, label: '语音与 TTS', desc: '通话链路与音色' },
]
const sectionKeys = groups.map(g => g.key)

function scrollToSection(key: string) {
  if (!pageRef.value) return
  const el = pageRef.value.querySelector(`#sec-${key}`) as HTMLElement | null
  if (!el) return
  const contRect = pageRef.value.getBoundingClientRect()
  const rect = el.getBoundingClientRect()
  pageRef.value.scrollTo({
    top: pageRef.value.scrollTop + rect.top - contRect.top - 12,
    behavior: 'smooth',
  })
}

function onPageScroll() {
  if (!pageRef.value) return
  const contRect = pageRef.value.getBoundingClientRect()
  let current = sectionKeys[0]
  for (const key of sectionKeys) {
    const el = pageRef.value.querySelector(`#sec-${key}`) as HTMLElement | null
    if (!el) continue
    const rect = el.getBoundingClientRect()
    if (rect.top - contRect.top <= 120 && rect.bottom - contRect.top > 60) {
      current = key
    }
  }
  activeSection.value = current
}

// ===== 品牌设计（Logo / 吉祥物）状态 =====
interface BrandSection {
  key: 'logo' | 'mascot'
  settingKey: string
  mode: 'ai' | 'upload'
  prompt: string
  generating: boolean
  candidates: string[]
  selected: string
}

function createBrandSection(key: 'logo' | 'mascot'): BrandSection {
  return {
    key,
    settingKey: key === 'logo' ? 'site_logo' : 'site_mascot',
    mode: 'ai',
    prompt: '',
    generating: false,
    candidates: [],
    selected: '',
  }
}

const logoSection = reactive<BrandSection>(createBrandSection('logo'))
const mascotSection = reactive<BrandSection>(createBrandSection('mascot'))
const savingBrand = ref(false)

const DEFAULT_LOGO = '/images/校徽_圆形.png'
const DEFAULT_MASCOT = '/images/mascot.png'
const logoDisplay = computed(() => {
  const stored = settingsMap['site_logo'] || ''
  if (!stored && logoSection.selected) return logoSection.selected
  return stored || DEFAULT_LOGO
})
const mascotDisplay = computed(() => {
  const stored = settingsMap['site_mascot'] || ''
  if (!stored && mascotSection.selected) return mascotSection.selected
  return stored || DEFAULT_MASCOT
})

// 品牌状态：当前生效 / 待应用 / 使用默认，用于预览图左上角徽章回显
function brandStatus(section: BrandSection): { text: string; kind: 'live' | 'pending' | 'default' } {
  const stored = settingsMap[section.settingKey] || ''
  if (section.selected && section.selected === stored) return { text: '当前生效', kind: 'live' }
  if (section.selected) return { text: '待应用', kind: 'pending' }
  return { text: '使用默认', kind: 'default' }
}
function brandStatusIcon(section: BrandSection) {
  return brandStatus(section).kind === 'live' ? Check : brandStatus(section).kind === 'pending' ? Clock : Image
}

// 底部操作栏提示语：根据「已应用 / 已选新图 / 未选择」区分
function brandHint(section: BrandSection): string {
  const stored = settingsMap[section.settingKey] || ''
  if (section.selected && section.selected === stored) return '已应用，顶栏与全站即刻生效'
  if (section.selected) return '已选择新图片，点击「应用」立即生效'
  if (section.mode === 'ai') return '输入提示词生成候选图，或切换「本地上传」'
  return '上传图片后可点击「应用」'
}

// AI 生成候选图
async function handleGenerate(section: BrandSection) {
  if (!section.prompt.trim()) {
    ElMessage.warning('请先输入设计提示词')
    return
  }
  section.generating = true
  try {
    const res = await generateBrandingImages(section.prompt, 4)
    section.candidates = res.images
    section.selected = res.images[0] || ''
    ElMessage.success(`已生成 ${res.images.length} 张候选图（模型 ${res.model}），点击选择后应用`)
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '图片生成失败，请检查 API Key 与网络')
  } finally {
    section.generating = false
  }
}

// 本地上传
async function handleUpload(section: BrandSection, file: File) {
  if (!/\.(png|jpe?g|webp|gif)$/i.test(file.name)) {
    ElMessage.warning('仅支持 png / jpg / webp / gif 图片')
    return false
  }
  try {
    const res = await uploadBrandingImage(file)
    section.selected = res.url
    section.candidates = []
    ElMessage.success('上传成功，点击「应用」即可更新')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '上传失败')
  }
  return false
}

// 应用图片到系统设置
async function handleApply(section: BrandSection) {
  if (!section.selected) {
    ElMessage.warning('请先生成或上传一张图片')
    return
  }
  savingBrand.value = true
  try {
    await batchUpdateSettings({ [section.settingKey]: section.selected })
    settingsMap[section.settingKey] = section.selected
    ElMessage.success(`${section.key === 'logo' ? 'Logo' : '吉祥物'}已更新，顶栏与全站即刻生效`)
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    savingBrand.value = false
  }
}

// 恢复默认 / 清除
async function handleReset(section: BrandSection) {
  savingBrand.value = true
  try {
    await batchUpdateSettings({ [section.settingKey]: '' })
    settingsMap[section.settingKey] = ''
    section.selected = ''
    section.candidates = []
    ElMessage.success(section.key === 'logo' ? '已恢复默认 Logo' : '已恢复默认吉祥物')
  } catch (error) {
    ElMessage.error('操作失败')
  } finally {
    savingBrand.value = false
  }
}

const aiConfigured = computed(() => {
  return !!(settingsMap['llm_api_key'] && settingsMap['llm_model'])
})

// ===== 敏感字段（掩码值）处理 =====
// 接口对敏感 Key 仅返回掩码（sk-s****MRig），页面直接明文显示以便确认"已回显"；
// 点击输入框时自动清空，可直接输入新 Key 覆盖；未输入则失焦恢复原掩码。
const _MASKED_KEYS = new Set(['llm_api_key', 'dashscope_api_key', 'embedding_api_key', 'xqe_password'])

function isMaskedValue(v?: string): boolean {
  return !!v && v.includes('****')
}

// 记录聚焦前的掩码值，用于失焦空值恢复
const keyMaskBackup: Record<string, string> = {}

function onSensitiveFocus(key: string) {
  if (isMaskedValue(settingsMap[key])) {
    keyMaskBackup[key] = settingsMap[key]
    settingsMap[key] = ''
  }
}

function restoreSensitiveOnBlur(key: string) {
  // 仅恢复 LLM API Key：未输入时还原掩码，避免误以为已清空
  if (key === 'llm_api_key' && keyMaskBackup[key] && !settingsMap[key]?.trim()) {
    settingsMap[key] = keyMaskBackup[key]
  }
  delete keyMaskBackup[key]
}

// 保存时剥离掩码/空值：未修改的敏感字段不提交，保留数据库原值
function stripMaskedKeys(settings: Record<string, string>): Record<string, string> {
  const out: Record<string, string> = {}
  Object.entries(settings).forEach(([k, v]) => {
    if (_MASKED_KEYS.has(k)) {
      if (isMaskedValue(v) || !v?.trim()) return // 掩码或空 → 不提交
    }
    out[k] = v
  })
  return out
}

// ===== 语音与 TTS =====
const voiceInfo = ref<VoicePipelineInfo | null>(null)
const voiceInfoLoading = ref(false)
const savingVoice = ref(false)
const voiceTestLoading = ref(false)
const previewText = ref('你好，我是绵小城，很高兴为你服务。今天天气不错，记得保持好心情哦！')
const audioSrc = ref('')
const voiceAudioRef = ref<HTMLAudioElement | null>(null)
const voiceTestResult = ref('')

// 音色静态兜底列表（与后端 voice/info 一致；页面加载后优先使用接口动态列表）
// Edge TTS：14 个中文音色，免费无需 Key；Token Plan：qwen-plus 精品音色
const STATIC_VOICE_PRESETS = [
  { voice: 'zh-CN-XiaoxiaoNeural', label: '晓晓', gender: '女', tag: '普通话·温暖亲切', provider: 'edge' },
  { voice: 'zh-CN-XiaoyiNeural', label: '晓伊', gender: '女', tag: '普通话·活泼友善', provider: 'edge' },
  { voice: 'zh-CN-YunjianNeural', label: '云健', gender: '男', tag: '普通话·沉稳有力', provider: 'edge' },
  { voice: 'zh-CN-YunxiNeural', label: '云希', gender: '男', tag: '普通话·阳光少年', provider: 'edge' },
  { voice: 'zh-CN-YunxiaNeural', label: '云夏', gender: '男', tag: '普通话·明朗大方', provider: 'edge' },
  { voice: 'zh-CN-YunyangNeural', label: '云扬', gender: '男', tag: '普通话·专业新闻', provider: 'edge' },
  { voice: 'zh-CN-liaoning-XiaobeiNeural', label: '晓贝', gender: '女', tag: '东北话·爽朗有趣', provider: 'edge' },
  { voice: 'zh-CN-shaanxi-XiaoniNeural', label: '晓妮', gender: '女', tag: '陕西话·质朴幽默', provider: 'edge' },
  { voice: 'zh-HK-HiuGaaiNeural', label: '曉佳', gender: '女', tag: '粤语·亲切', provider: 'edge' },
  { voice: 'zh-HK-HiuMaanNeural', label: '曉曼', gender: '女', tag: '粤语·温柔', provider: 'edge' },
  { voice: 'zh-HK-WanLungNeural', label: '雲龍', gender: '男', tag: '粤语·沉稳', provider: 'edge' },
  { voice: 'zh-TW-HsiaoChenNeural', label: '曉臻', gender: '女', tag: '台湾国语·自然', provider: 'edge' },
  { voice: 'zh-TW-HsiaoYuNeural', label: '曉雨', gender: '女', tag: '台湾国语·活泼', provider: 'edge' },
  { voice: 'zh-TW-YunJheNeural', label: '雲哲', gender: '男', tag: '台湾国语·沉稳', provider: 'edge' },
  { voice: 'longanhuan_v3.6', label: '龙安欢（默认）', gender: '女', tag: '精品中文·默认', provider: 'tokenplan' },
  { voice: 'longanlingxi', label: '龙安灵希', gender: '女', tag: '精品中文·可爱甜美', provider: 'tokenplan' },
]

// 音色选项：优先接口动态列表，接口未返回时用静态兜底
const voiceOptions = computed<typeof STATIC_VOICE_PRESETS>(() => {
  const dyn = voiceInfo.value?.voices
  return (dyn && dyn.length ? dyn : STATIC_VOICE_PRESETS) as typeof STATIC_VOICE_PRESETS
})
const edgeVoiceOptions = computed(() => voiceOptions.value.filter(v => v.provider === 'edge'))
const tokenplanVoiceOptions = computed(() => voiceOptions.value.filter(v => v.provider === 'tokenplan'))
const edgeVoicesCount = computed(() => edgeVoiceOptions.value.length)

const VOICE_PROMPT_EXAMPLES = [
  { label: '温柔亲切', text: '语气温柔亲切、自然有耐心，多用安抚性表达，像知心姐姐一样陪伴学生；句子简短，口语化。' },
  { label: '活泼热情', text: '语气活泼热情、富有感染力，适当使用感叹语气，让学生感到轻松愉快；句子简短，口语化。' },
  { label: '沉稳专业', text: '语气沉稳专业、条理清晰，表达简洁准确，适合正式场景的资讯播报；避免网络用语。' },
]

const effectiveVoice = computed(() => {
  return settingsMap['llm_tts_voice']?.trim() || voiceInfo.value?.voice || 'longanhuan_v3.6'
})

const voiceKeyConfigured = computed(
  () => !!(settingsMap['llm_api_key'] || settingsMap['dashscope_api_key']) || edgeVoiceOptions.value.length > 0,
)

const voicePipeline = computed(() => {
  const llm = voiceInfo.value?.llm_model || settingsMap['llm_agent_model'] || settingsMap['llm_model'] || '未配置'
  const voice = effectiveVoice.value
  const sttModel = voiceInfo.value?.stt?.model || 'qwen-audio-3.0-asr-flash'
  const isEdge = /neural$/i.test(voice)
  const ttsModel = isEdge ? 'edge-tts（微软免费）' : (voiceInfo.value?.tts?.model || 'qwen-audio-3.0-tts-plus')
  return [
    { key: 'mic', icon: Mic, title: '麦克风采集', zone: '客户端', color: 'green', desc: '采集 16kHz PCM 音频流', chips: ['噪音抵消', '端点检测'] },
    { key: 'stt', icon: Monitor, title: 'ASR 语音识别', zone: '服务端', color: 'blue', desc: '语音 → 文本转写', chips: [sttModel] },
    { key: 'emotion', icon: TriangleAlert, title: '情绪 / 危机检测', zone: '服务端', color: 'orange', desc: '视觉情绪 + 敏感词联动', chips: ['心理关注上报'] },
    { key: 'llm', icon: MessageSquare, title: '大模型理解', zone: '服务端', color: 'violet', desc: '上下文 → 流式回复文本', chips: [llm] },
    { key: 'tts', icon: Sparkles, title: 'TTS 语音合成', zone: '服务端', color: 'cyan', desc: isEdge ? 'Edge TTS 免费合成 · 故障自动降级 Token Plan' : '短语级流式合成（边说边出）', chips: [ttsModel, voice] },
    { key: 'play', icon: Headphones, title: '扬声器播放', zone: '客户端', color: 'green', desc: '播放即达，开口即打断', chips: ['低延迟', '可打断'] },
  ]
})

function applyPromptExample(text: string) {
  settingsMap['llm_tts_prompt'] = text
}

async function loadVoiceInfo() {
  voiceInfoLoading.value = true
  try {
    voiceInfo.value = await getVoicePipelineInfo()
  } catch (error) {
    console.error('加载语音链路信息失败:', error)
  } finally {
    voiceInfoLoading.value = false
  }
}

async function handleVoicePreview() {
  if (!previewText.value.trim()) {
    ElMessage.warning('请输入试听文本')
    return
  }
  voiceTestLoading.value = true
  voiceTestResult.value = ''
  audioSrc.value = ''
  try {
    const res = await testTtsPreview({
      text: previewText.value.trim(),
      voice: settingsMap['llm_tts_voice']?.trim() || undefined,
    })
    // 先解除 loading：audio 的 v-if 依赖「audioSrc && !voiceTestLoading」，
    // 若在 nextTick 后才解开 loading，元素会晚于手势链路渲染，el.play() 取不到元素且自动播放被策略拦截 → 无声
    voiceTestLoading.value = false
    audioSrc.value = `data:audio/wav;base64,${res.audio_base64}`
    voiceTestResult.value = `已合成 ${res.chars} 字 · 音色 ${res.voice} · 模型 ${res.model}`
    console.info('[voice-test] 合成成功 audio=', res.audio_base64 ? res.audio_base64.length + 'B(base64)' : 'EMPTY', 'model=', res.model)
    // 合成成功后立即自动播放（仍在用户点击手势链路上，autoplay 策略允许）
    await nextTick()
    const el = voiceAudioRef.value
    if (el) {
      console.info('[voice-test] audio 元素 readyState=', el.readyState, 'duration=', el.duration ?? -1, 'paused=', el.paused)
      el.play()
        .then(() => {
          console.info('[voice-test] play() 已接受（浏览器开始播放）')
          setTimeout(async () => {
            if (el) {
              console.info('[voice-test] 播放1s后 currentTime=', el.currentTime.toFixed(2), 'paused=', el.paused, 'ended=', el.ended,
                'volume=', el.volume, 'muted=', el.muted)
              // 输出链路诊断：设备列表 + AudioContext 状态（排查系统静音/无输出设备）
              try {
                const devs = await navigator.mediaDevices.enumerateDevices()
                const outs = devs.filter((d) => d.kind === 'audiooutput')
                console.info('[voice-test] 音频输出设备=', outs.length ? outs.map((d) => d.label || '(未授权名称)').join(' | ') : '无（系统无可用输出设备，请检查音量合成器/默认设备）')
              } catch (e: unknown) {
                console.info('[voice-test] enumerateDevices 不可用:', e)
              }
              try {
                const ctx = new AudioContext()
                console.info('[voice-test] AudioContext.state=', ctx.state, '（running=正常，suspended=被自动播放策略挂起）')
                void ctx.close()
              } catch { /* ignore */ }
            }
          }, 1000)
        })
        .catch((e: unknown) => {
          console.error('[voice-test] play() 被拒绝:', e)
          // 个别浏览器拦截自动播放：提示用户手动点击播放条
          ElMessage.info('已合成，若未自动播放请点击播放条试听')
        })
    } else {
      console.error('[voice-test] audio 元素未渲染，无法播放')
    }
    ElMessage.success('试听合成成功')
  } catch (error: any) {
    ElMessage.error(error?.response?.data?.detail || '合成失败，请检查语音 API Key 与网络')
  } finally {
    voiceTestLoading.value = false
  }
}

// 浏览器无法解析返回的音频（如 WAV 头异常）时给出明确提示，避免"无声失败"
function handleVoiceAudioError() {
  audioSrc.value = ''
  voiceTestResult.value = ''
  ElMessage.error('音频解码失败：浏览器无法播放返回的语音，请稍后重试')
}

async function handleSaveVoice() {
  savingVoice.value = true
  try {
    await batchUpdateSettings({
      llm_tts_voice: settingsMap['llm_tts_voice'] || '',
      llm_tts_prompt: settingsMap['llm_tts_prompt'] || '',
    })
    await loadVoiceInfo()
    ElMessage.success('语音设置已保存，语音通话即时生效')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    savingVoice.value = false
  }
}

// ===== 通用设置加载 / 保存 =====
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
    // 试听文本：若已有音色则不覆盖用户输入
    if (!previewText.value.includes(settingsMap['agent_name'] || '绵小城')) {
      previewText.value = previewText.value.replace('绵小城', settingsMap['agent_name'] || '绵小城')
    }
    // 品牌设计回显：已保存的 Logo / 吉祥物同步为当前选中
    if (settingsMap['site_logo']) logoSection.selected = settingsMap['site_logo']
    if (settingsMap['site_mascot']) mascotSection.selected = settingsMap['site_mascot']
    // 危机预警配置回显：数据库未配置时回退默认词库，与「危机预警」页展示保持一致
    if (!settingsMap['crisis_keywords'] || !String(settingsMap['crisis_keywords']).trim()) {
      try {
        const cfg = await getCrisisConfig()
        settingsMap['crisis_keywords'] = (cfg.keywords || []).join('，')
        if (settingsMap['auto_notify_counselor'] === undefined) {
          settingsMap['auto_notify_counselor'] = String(cfg.notify_counselor)
        }
      } catch (error) {
        console.error('加载危机预警配置失败:', error)
      }
    }
  } catch (error) {
    console.error('加载设置失败:', error)
  } finally {
    loading.value = false
  }
}

async function loadAll() {
  await Promise.all([loadSettings(), loadVoiceInfo()])
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
  // 与「危机预警」页规则一致：预警敏感词不能为空，避免保存空值导致两处展示不一致
  if (!settingsMap['crisis_keywords'] || !String(settingsMap['crisis_keywords']).trim()) {
    ElMessage.warning('预警敏感词不能为空')
    return
  }
  saving.value = true
  try {
    // 敏感词规范化：兼容中英文逗号 / 顿号 / 空白分隔，与「危机预警」页标签规则保持一致
    const keywords = Array.from(new Set(
      String(settingsMap['crisis_keywords'] || '')
        .split(/[,，、;；\s]+/)
        .map(k => k.trim())
        .filter(Boolean)
    ))
    const payload = stripMaskedKeys({ ...settingsMap })
    payload['crisis_keywords'] = keywords.join(',')
    // 仅提交通用基础字段：敏感 Key 由"保存AI配置"管理，避免脱敏/空值覆盖数据库
    await batchUpdateSettings(payload)
    settingsMap['crisis_keywords'] = keywords.join('，')
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
      dashscope_api_key: settingsMap['dashscope_api_key'] || '',
      agent_name: settingsMap['agent_name'] || '',
      system_prompt: settingsMap['system_prompt'] || '',
    }
    // 未修改的敏感 Key（掩码）不提交，保留原值；dashscope 显式清空仍提交（清空 = 复用默认）
    const payload = stripMaskedKeys(aiSettings)
    if (settingsMap['dashscope_api_key']?.trim() === '') {
      payload['dashscope_api_key'] = ''
    }
    await batchUpdateSettings(payload)
    ElMessage.success('AI配置已保存')
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    savingAI.value = false
  }
}

// 测试 AI 连接：先保存配置，再流式请求一条测试消息
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
      llm_agent_model: settingsMap['llm_agent_model'] || '',
      max_chat_history: settingsMap['max_chat_history'] || '50',
      dashscope_api_key: settingsMap['dashscope_api_key'] || '',
      agent_name: settingsMap['agent_name'] || '',
    }
    await batchUpdateSettings(stripMaskedKeys(aiSettings))

    const token = (await import('@/utils/token')).getToken()
    const response = await fetch('/api/agent/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-Requested-With': 'XMLHttpRequest',
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
  loadAll()
})
</script>

<style scoped>
.setting-page {
  height: 100%;
  overflow-y: auto;
  padding: 16px;
  background: #f5f7fa;
}

/* ===== 页头 ===== */
.page-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}
.page-title-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.page-title-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: #409eff;
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.page-title {
  font-size: 18px;
  font-weight: 700;
  margin: 0;
  color: #1a1a2e;
}
.page-sub {
  font-size: 12px;
  color: #8a93a6;
  margin: 2px 0 0;
}
.page-title-actions {
  display: flex;
  gap: 10px;
}

/* ===== 主体：左侧分组导航 + 右侧内容（参考高星开源后台设置页布局） ===== */
.setting-body {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}
.setting-nav {
  width: 240px;
  flex-shrink: 0;
  position: sticky;
  top: 0;
  background: #fff;
  border-radius: 12px;
  padding: 12px 8px;
  box-shadow: 0 1px 8px rgba(30, 41, 59, 0.06);
}
.nav-title {
  font-size: 11px;
  font-weight: 600;
  color: #a0a8b8;
  letter-spacing: 0.08em;
  padding: 4px 12px 10px;
}
.nav-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s, box-shadow 0.2s;
}
.nav-item:hover {
  background: #f3f6fc;
}
.nav-item.active {
  background: rgba(64, 158, 255, 0.12);
  box-shadow: inset 0 0 0 1px rgba(64, 158, 255, 0.35);
}
.nav-item.active::before {
  content: '';
  position: absolute;
  left: -8px;
  top: 50%;
  transform: translateY(-50%);
  width: 3px;
  height: 20px;
  border-radius: 2px;
  background: #3b82f6;
}
.nav-icon {
  width: 30px;
  height: 30px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #8a93a6;
  background: #f3f5f8;
  flex-shrink: 0;
  transition: all 0.2s;
}
.nav-item.active .nav-icon {
  color: #409eff;
  background: #fff;
  box-shadow: 0 2px 6px rgba(64, 158, 255, 0.25);
}
.nav-label {
  flex: 1;
  min-width: 0;
}
.nav-name {
  font-size: 13px;
  font-weight: 600;
  color: #2b3445;
}
.nav-desc {
  font-size: 11px;
  color: #a0a8b8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.nav-status {
  flex-shrink: 0;
}
.setting-content {
  flex: 1;
  min-width: 0;
  max-width: 980px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.setting-loading {
  padding: 24px;
  text-align: center;
  color: #8a93a6;
  font-size: 13px;
}

/* ===== 设置区块 ===== */
.setting-section {
  background: #fff;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 8px rgba(30, 41, 59, 0.06);
  scroll-margin-top: 12px;
}
.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 18px;
  padding-bottom: 12px;
  border-bottom: 1px solid #f0f2f5;
}
.section-header-icon {
  width: 38px;
  height: 38px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}
.section-header-icon.blue { background: #409eff; }
.section-header-icon.violet { background: #7c4dff; }
.section-header-icon.orange { background: #ff9800; }
.section-header-icon.green { background: #67c23a; }
.section-header-icon.cyan { background: #00bcd4; }
.section-header-info {
  flex: 1;
  min-width: 0;
}
.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 700;
  color: #1a1a2e;
}
.section-desc {
  font-size: 12px;
  color: #8a93a6;
  margin-top: 2px;
}
.setting-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.setting-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.setting-info {
  flex: 1;
  min-width: 0;
}
.setting-name {
  font-size: 13px;
  font-weight: 600;
  color: #333;
  margin-bottom: 3px;
}
.setting-desc {
  font-size: 11px;
  color: #99a1b3;
  line-height: 1.5;
}
.required {
  color: #f56c6c;
  margin-left: 2px;
}
.ai-section {
  border: 1px solid rgba(64, 158, 255, 0.18);
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.02), rgba(103, 194, 58, 0.02));
}
.ai-actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid #f0f2f5;
}
.system-prompt-item {
  align-items: flex-start;
}
.mono-text {
  font-family: Consolas, 'Courier New', monospace;
  color: #409eff;
  background: rgba(64, 158, 255, 0.08);
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 12px;
}

/* ===== 品牌设计 ===== */
.brand-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}
.brand-card {
  border: 1px solid #eef0f4;
  border-radius: 12px;
  padding: 16px;
  background: #fafbfd;
  display: flex;
  flex-direction: column;
}
.brand-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}
.brand-card-title {
  font-size: 13px;
  font-weight: 700;
  color: #2b3445;
  margin: 0;
}
.brand-preview {
  position: relative;
  height: 150px;
  border-radius: 10px;
  background: #fff;
  border: 1px dashed #dfe3ec;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  margin-bottom: 12px;
}
.brand-preview-img {
  width: 100%;
  height: 100%;
}
.brand-preview-badge {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 2;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  line-height: 1;
  padding: 5px 9px;
  border-radius: 999px;
  color: #fff;
  box-shadow: 0 1px 4px rgba(30, 41, 59, 0.16);
  pointer-events: none;
}
.brand-preview-badge.live { background: rgba(103, 194, 58, 0.92); }
.brand-preview-badge.pending { background: rgba(230, 162, 60, 0.92); }
.brand-preview-badge.default { background: rgba(144, 147, 153, 0.85); }
.brand-composer {
  display: flex;
  align-items: flex-end;
  gap: 10px;
}
.brand-composer .el-textarea {
  flex: 1;
  min-width: 0;
}
.composer-btn {
  flex-shrink: 0;
}
.brand-composer.upload {
  align-items: stretch;
}
.brand-composer.upload .el-upload,
.brand-composer.upload .el-upload-dragger {
  width: 100%;
}
.brand-idle-tip {
  margin-top: 10px;
  padding: 9px 12px;
  border-radius: 8px;
  background: #f6f8fb;
  border: 1px dashed #e0e5ee;
  font-size: 11px;
  color: #8a93a6;
  display: flex;
  align-items: center;
  gap: 6px;
  line-height: 1.5;
}
.brand-candidates {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 12px;
}
.candidate {
  position: relative;
  width: 92px;
  height: 92px;
  border-radius: 8px;
  overflow: hidden;
  border: 2px solid transparent;
  cursor: pointer;
  transition: border-color 0.2s, transform 0.2s, box-shadow 0.2s;
}
.candidate:hover {
  transform: translateY(-1px);
  box-shadow: 0 3px 10px rgba(30, 41, 59, 0.12);
}
.candidate.active {
  border-color: #409eff;
}
.candidate-img {
  width: 100%;
  height: 100%;
}
.candidate-index {
  position: absolute;
  left: 4px;
  top: 4px;
  background: rgba(0, 0, 0, 0.5);
  color: #fff;
  font-size: 10px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.candidate-check {
  position: absolute;
  right: 4px;
  bottom: 4px;
  background: #409eff;
  color: #fff;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}
.upload-icon {
  font-size: 40px;
  color: #c0c4cc;
}
.brand-save {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f0f2f5;
}
.brand-save-hint {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #99a1b3;
  min-width: 0;
  line-height: 1.4;
}
.brand-save-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

/* ===== 语音与 TTS 区块 ===== */
.voice-sub {
  margin-top: 18px;
}
.voice-sub-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 700;
  color: #2b3445;
  margin-bottom: 12px;
}
.voice-sub-title::before {
  content: '';
  width: 3px;
  height: 14px;
  border-radius: 2px;
  background: #00bcd4;
}
.pipe-wrap {
  border: 1px solid #eef0f4;
  border-radius: 12px;
  padding: 16px;
  background: linear-gradient(180deg, #fafbfd, #fff);
}
.pipe-head {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.pipe-head-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 700;
  color: #2b3445;
}
.pipe-head-tip {
  font-size: 11px;
  color: #99a1b3;
}
.pipe-track {
  overflow-x: auto;
  padding-bottom: 6px;
}
.pipe-inner {
  display: flex;
  align-items: stretch;
  min-width: min-content;
  padding-top: 10px;
}
.pipe-node {
  position: relative;
  width: 150px;
  flex-shrink: 0;
  border-radius: 10px;
  padding: 12px 10px 10px;
  background: #fff;
  border: 1px solid #e8ebf1;
  text-align: center;
  transition: transform 0.2s, box-shadow 0.2s;
}
.pipe-node:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(30, 41, 59, 0.1);
}
.pipe-zone {
  position: absolute;
  top: -9px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 10px;
  padding: 1px 8px;
  border-radius: 8px;
  white-space: nowrap;
}
.zone-client { background: #e8f5e9; color: #388e3c; }
.zone-server { background: #e3f2fd; color: #1976d2; }
.pipe-node-icon {
  width: 40px;
  height: 40px;
  margin: 8px auto;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.pipe-node-title {
  font-size: 12px;
  font-weight: 700;
  color: #2b3445;
  margin-bottom: 4px;
}
.pipe-node-desc {
  font-size: 10px;
  color: #8a93a6;
  line-height: 1.4;
  min-height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.pipe-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  justify-content: center;
  margin-top: 8px;
}
.pipe-chip {
  font-size: 10px;
  background: #f3f5f8;
  color: #6b7280;
  border-radius: 4px;
  padding: 1px 6px;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.c-green { border-top: 3px solid #67c23a; }
.c-blue { border-top: 3px solid #409eff; }
.c-orange { border-top: 3px solid #e6a23c; }
.c-violet { border-top: 3px solid #7c4dff; }
.c-cyan { border-top: 3px solid #00bcd4; }
.c-green .pipe-node-icon { background: rgba(103, 194, 58, 0.12); color: #67c23a; }
.c-blue .pipe-node-icon { background: rgba(64, 158, 255, 0.12); color: #409eff; }
.c-orange .pipe-node-icon { background: rgba(230, 162, 60, 0.12); color: #e6a23c; }
.c-violet .pipe-node-icon { background: rgba(124, 77, 255, 0.12); color: #7c4dff; }
.c-cyan .pipe-node-icon { background: rgba(0, 188, 212, 0.14); color: #00bcd4; }
.pipe-arrow {
  display: flex;
  align-items: center;
  padding: 0 4px;
  flex-shrink: 0;
}
.pipe-arrow-line {
  position: relative;
  width: 30px;
  height: 2px;
  background: repeating-linear-gradient(90deg, #c9d2e0 0 6px, transparent 6px 10px);
}
.pipe-arrow-line::after {
  content: '';
  position: absolute;
  right: -2px;
  top: -3px;
  border-left: 6px solid #c9d2e0;
  border-top: 4px solid transparent;
  border-bottom: 4px solid transparent;
}

/* 试听 */
.voice-preview-item {
  align-items: flex-start;
}
.voice-preview {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 10px;
  width: 340px;
  flex-shrink: 0;
}
.voice-audio {
  width: 340px;
  height: 36px;
}
.voice-test-result {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #67c23a;
}
.voice-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.voice-option-name {
  font-size: 12px;
}
.voice-option-value {
  font-size: 11px;
  color: #99a1b3;
  font-family: Consolas, 'Courier New', monospace;
}
.voice-prompt-wrap {
  width: 480px;
  flex-shrink: 0;
}
.voice-prompt-examples {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  flex-wrap: wrap;
}
.example-label {
  font-size: 12px;
  color: #8a93a6;
}
.example-tag {
  cursor: pointer;
}

/* ===== 响应式 ===== */
@media (max-width: 900px) {
  .setting-body {
    flex-direction: column;
  }
  .setting-nav {
    position: static;
    width: 100%;
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    padding: 8px;
  }
  .nav-title {
    display: none;
  }
  .nav-item {
    flex: 1;
    min-width: 130px;
  }
  .nav-desc {
    display: none;
  }
  .setting-content {
    max-width: none;
  }
}
@media (max-width: 768px) {
  .brand-grid {
    grid-template-columns: 1fr;
  }
  .brand-composer {
    flex-direction: column;
    align-items: stretch;
  }
  .brand-composer .composer-btn {
    width: 100%;
  }
  .brand-save {
    flex-direction: column;
    align-items: stretch;
    gap: 10px;
  }
  .brand-save-actions {
    justify-content: flex-end;
  }
  .setting-item {
    flex-direction: column;
    align-items: stretch;
  }
  .voice-preview,
  .voice-audio,
  .voice-prompt-wrap {
    width: 100%;
  }
  .pipe-node {
    width: 132px;
  }
  .setting-nav {
    display: none;
  }
}

/* ===== 暗色模式 ===== */
html.dark .setting-page { background: #14161f; }
html.dark .setting-nav,
html.dark .setting-section {
  background: #1c1f2b;
  box-shadow: 0 1px 8px rgba(0, 0, 0, 0.3);
}
html.dark .nav-item:hover { background: rgba(255, 255, 255, 0.05); }
html.dark .nav-item.active {
  background: rgba(64, 158, 255, 0.15);
  box-shadow: inset 0 0 0 1px rgba(64, 158, 255, 0.4);
}
html.dark .nav-item.active .nav-icon {
  background: rgba(64, 158, 255, 0.16);
  color: #79bbff;
}
html.dark .page-title,
html.dark .nav-name,
html.dark .section-title,
html.dark .setting-name,
html.dark .brand-card-title,
html.dark .voice-sub-title,
html.dark .pipe-node-title,
html.dark .pipe-head-title { color: #e8eaf0; }
html.dark .page-sub,
html.dark .nav-desc,
html.dark .section-desc,
html.dark .setting-desc,
html.dark .voice-option-value,
html.dark .pipe-head-tip { color: #7a8296; }
html.dark .nav-icon,
html.dark .pipe-chip { background: #262a38; color: #a0a8b8; }
html.dark .section-header,
html.dark .ai-actions { border-color: #2a2e3d; }
html.dark .ai-section {
  border-color: rgba(64, 158, 255, 0.25);
  background: linear-gradient(135deg, rgba(64, 158, 255, 0.06), rgba(103, 194, 58, 0.04));
}
html.dark .brand-card {
  background: #191c26;
  border-color: #2a2e3d;
}
html.dark .brand-preview {
  background: #14161f;
  border-color: #33384a;
}
html.dark .brand-preview-badge {
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.5);
}
html.dark .brand-idle-tip {
  background: #1a1d28;
  border-color: #33384a;
  color: #7a8296;
}
html.dark .brand-save {
  border-top-color: #2a2e3d;
}
html.dark .brand-save-hint {
  color: #6d7588;
}
html.dark .pipe-wrap {
  background: linear-gradient(180deg, #191c26, #1c1f2b);
  border-color: #2a2e3d;
}
html.dark .pipe-node {
  background: #20232f;
  border-color: #33384a;
}
html.dark .pipe-node:hover {
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.45);
}
html.dark .pipe-node-desc { color: #7a8296; }
html.dark .pipe-arrow-line {
  background: repeating-linear-gradient(90deg, #3a4052 0 6px, transparent 6px 10px);
}
html.dark .pipe-arrow-line::after { border-left-color: #3a4052; }
html.dark .zone-client { background: rgba(76, 175, 80, 0.18); color: #81c784; }
html.dark .zone-server { background: rgba(66, 165, 245, 0.18); color: #64b5f6; }
html.dark .voice-test-result { color: #81c784; }
html.dark .mono-text {
  color: #79bbff;
  background: rgba(64, 158, 255, 0.14);
}
</style>