/**
 * SFC 样式块守卫：用 @vue/compiler-sfc 解析单文件组件，再用 postcss 解析其 <style> 块，
 * 断言「规则外的裸声明数 = 0」。
 *
 * 背景：曾因一次 edit 的 old_string 跨越 selector 行，删掉了 `/* 注释 *​/ + 若干规则 + .news-row {`
 * 这一行，样式块里出现「处于规则之外、直接挂在根上的 CSS 声明」，PostCSS 抛
 * `Unexpected }`，整个 CampusPage 白屏。此脚本用于回归防线。
 *
 * 用法: node scripts/verify-sfc-css.mjs [file ...]
 * 默认校验 src/views/student/CampusPage.vue
 */
import { readFileSync, existsSync } from 'node:fs'
import { resolve, relative } from 'node:path'
import { parse as parseSfc } from '@vue/compiler-sfc'
import postcss from 'postcss'

const DEFAULT_FILES = ['src/views/student/CampusPage.vue']
const files = process.argv.slice(2).length ? process.argv.slice(2) : DEFAULT_FILES

let failed = false

for (const f of files) {
  const abs = resolve(process.cwd(), f)
  const label = relative(process.cwd(), abs).replace(/\\/g, '/')
  if (!existsSync(abs)) {
    console.log(`FAIL ${label}: 文件不存在`)
    failed = true
    continue
  }

  const source = readFileSync(abs, 'utf8')

  // 1) SFC 解析：编译错误会出现在 errors 里，descriptor 为 null
  const { descriptor, errors } = parseSfc(source, { filename: label })
  if (errors.length || !descriptor) {
    console.log(`FAIL ${label}: @vue/compiler-sfc 解析失败`)
    for (const e of errors) console.log('  -', e.message)
    failed = true
    continue
  }

  const styleBlocks = descriptor.styles
  if (!styleBlocks.length) {
    console.log(`FAIL ${label}: 未找到 <style> 块`)
    failed = true
    continue
  }

  let bareDeclarations = 0
  let rules = 0
  let styleParseOk = true

  for (const block of styleBlocks) {
    let root
    try {
      root = postcss.parse(block.content, { from: `${label}<style#${block.lang || 'css'}>` })
    } catch (err) {
      console.log(`FAIL ${label}: postcss 解析 <style> 失败 -> ${err.message}`)
      styleParseOk = false
      failed = true
      break
    }

    // 规则外的裸声明 = 直接挂在根节点上的 decl / 注释外的原始声明节点
    root.each((node) => {
      if (node.type === 'decl') {
        bareDeclarations++
        const line = block.content.slice(0, node.source?.start?.offset ?? 0).split('\n').length
        console.log(
          `FAIL ${label}: style 内第 ${line} 行存在规则外的裸声明 \`${node.prop}: ${node.value}\` （缺少 selector）`,
        )
      }
    })
    root.walkRules(() => { rules++ })
  }

  if (!styleParseOk) continue

  if (bareDeclarations > 0) {
    failed = true
    console.log(`FAIL ${label}: 规则外裸声明数 = ${bareDeclarations}`)
  } else {
    console.log(
      `PASS ${label}: SFC 可解析 (template/script: ${descriptor.template ? 'ok' : 'none'}/${
        descriptor.script || descriptor.scriptSetup ? 'ok' : 'none'
      }), <style> 块 ${styleBlocks.length} 个, CSS 规则 ${rules} 条, 规则外裸声明数 = 0`,
    )
  }
}

process.exit(failed ? 1 : 0)