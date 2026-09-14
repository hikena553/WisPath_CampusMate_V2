export function renderMarkdown(text: string): string {
  if (!text) return ''

  let html = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')

  // 代码块（```...```）
  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_match, _lang, code) => {
    return `<pre class="md-code-block"><code>${code.trim()}</code></pre>`
  })

  // 行内代码（`...`）
  html = html.replace(/`([^`]+)`/g, '<code class="md-inline-code">$1</code>')

  // 表格
  html = html.replace(/^(\|.+\|)\n(\|[\s\-:]+\|)\n((?:\|.+\|\n?)+)/gm, (_match, header, _separator, body) => {
    const headers = header.split('|').filter((c: string) => c.trim()).map((c: string) => `<th>${c.trim()}</th>`)
    const rows = body.trim().split('\n').map((row: string) => {
      const cells = row.split('|').filter((c: string) => c.trim()).map((c: string) => `<td>${c.trim()}</td>`)
      return `<tr>${cells.join('')}</tr>`
    })
    return `<table class="md-table"><thead><tr>${headers.join('')}</tr></thead><tbody>${rows.join('')}</tbody></table>`
  })

  // 标题（### ## #）
  html = html.replace(/^### (.+)$/gm, '<h4 class="md-h4">$1</h4>')
  html = html.replace(/^## (.+)$/gm, '<h3 class="md-h3">$1</h3>')
  html = html.replace(/^# (.+)$/gm, '<h2 class="md-h2">$1</h2>')

  // 粗体 + 斜体（***...***）
  html = html.replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')

  // 粗体（**...**）
  html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')

  // 斜体（*...*）
  html = html.replace(/\*(.+?)\*/g, '<em>$1</em>')

  // 删除线（~~...~~）
  html = html.replace(/~~(.+?)~~/g, '<del>$1</del>')

  // 引用（> ...）
  html = html.replace(/^&gt; (.+)$/gm, '<blockquote class="md-quote">$1</blockquote>')

  // 无序列表（- 或 *）
  html = html.replace(/^[\-\*] (.+)$/gm, '<li class="md-li">$1</li>')

  // 有序列表（1. 2. 3.）
  html = html.replace(/^\d+\. (.+)$/gm, '<li class="md-li">$1</li>')

  html = html.replace(/(<li class="md-li">.*<\/li>\n?)+/g, '<ul class="md-ul">$&</ul>')

  // 链接（[文本](URL)）
  html = html.replace(/\[(.+?)\]\((.+?)\)/g, (_match, label, url) => {
    const safeUrl = url.replace(/"/g, '&quot;')
    if (/^javascript:/i.test(safeUrl.trim())) {
      return label
    }
    return `<a href="${safeUrl}" target="_blank" rel="noopener noreferrer">${label}</a>`
  })

  // 换行
  html = html.replace(/\n/g, '<br>')

  return html
}
