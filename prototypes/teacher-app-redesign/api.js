/* =========================================================================
   api.js · API stub 层（签名对齐未来真实接口，内部返回 mock）
   后续接入后端时，只需把每个函数体替换为真实 fetch，调用方零改动。
   ========================================================================= */
(function () {
  const delay = (ms) => new Promise((r) => setTimeout(r, ms));

  window.API = {
    // TODO: replace with GET /api/messages/conversations
    // resp: ConversationOut[] { id, type, name, avatar, last_message, last_message_time, unread_count }
    async getConversations() {
      await delay(280);
      return window.DB.conversations;
    },

    // TODO: replace with GET /api/messages/{userId}  （群聊走 GET /api/groups/{id}/messages）
    // resp: MessageOut[] { id, sender_id, sender_name, content, created_at }
    async getMessages(convId) {
      await delay(240);
      return window.DB.messages[convId] || window.DB.messages['default'];
    },

    // TODO: replace with POST /api/messages/send  { receiver_id, content }
    async sendMessage(convId, text) {
      await delay(120);
      return { id: 'local-' + Date.now(), convId, text, time: nowTime() };
    },

    // TODO: replace with GET /api/organization/tree  （学院 → 专业 → 班级 → 学生）
    async getOrgTree() {
      await delay(320);
      return window.DB.org;
    },

    // TODO: replace with GET /api/teacher/students
    async getMyStudents() {
      await delay(260);
      return window.DB.myStudents;
    },

    // TODO: replace with GET /api/auth/teachers
    async getColleagues() {
      await delay(260);
      return window.DB.colleagues;
    },

    // TODO: replace with GET /api/notifications
    async getNotifications() {
      await delay(240);
      return window.DB.notifications;
    },

    // TODO: replace with GET /api/teacher/quick-entries  （首页常用功能 + 实时角标）
    async getQuickEntries() {
      await delay(200);
      return window.DB.quickEntries;
    },

    // TODO: replace with GET /api/teacher/{module}  （审批/预警/公告/成长档案/问卷/关怀/家校/任务/AI洞察）
    async getSubPage(id) {
      await delay(300);
      return window.DB.modules[id] || window.DB.subPages[id];
    },

    // TODO: replace with POST /api/teacher/{module}/{action}  { payload }
    // resp: { ok: true, id, message }  —— 当前返回 mock，签名与真实接口对齐
    async submitModuleAction(module, action, payload) {
      await delay(180);
      return { ok: true, module: module, action: action, payload: payload || {}, id: 'local-' + Date.now() };
    },
  };

  function nowTime() {
    const d = new Date();
    return String(d.getHours()).padStart(2, '0') + ':' + String(d.getMinutes()).padStart(2, '0');
  }
})();