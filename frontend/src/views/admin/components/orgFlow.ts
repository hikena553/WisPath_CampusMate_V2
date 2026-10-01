import type { College, Major, ClassGroup } from '@/types'

/** 节点尺寸与间距（画布采用固定尺寸节点，保证自动布局精确） */
export const NODE_W = 240
export const NODE_H = 96
export const H_GAP = 92
export const V_GAP = 22
export const PAD = 56

export type FlowNodeType = 'root' | 'college' | 'major' | 'class'

export interface FlowStats {
  childCount: number
  majorCount: number
  classCount: number
  studentCount: number
}

export interface FlowNode {
  key: string
  type: FlowNodeType
  id: number
  name: string
  code: string | null
  description: string | null
  grade?: number
  stats: FlowStats
  hasChildren: boolean
  childCount: number
  children: FlowNode[]
  raw?: College | Major | ClassGroup
  /** 以下由布局计算得出 */
  depth: number
  x: number
  y: number
}

export interface FlowEdge {
  key: string
  from: string
  to: string
  path: string
}

export interface FlowLayout {
  nodes: FlowNode[]
  edges: FlowEdge[]
  width: number
  height: number
}

export const emptyStats = (): FlowStats => ({
  childCount: 0,
  majorCount: 0,
  classCount: 0,
  studentCount: 0,
})

/** 父节点右侧端口中心 */
export const outPort = (n: FlowNode) => ({ x: n.x + NODE_W, y: n.y + NODE_H / 2 })
/** 子节点左侧端口中心 */
export const inPort = (n: FlowNode) => ({ x: n.x, y: n.y + NODE_H / 2 })

/**
 * 自左向右的分层自动布局（工作流式）。
 * 叶子节点依次占位，父节点垂直居中对齐其子节点；
 * 连线为三次贝塞尔曲线，水平方向留出等长控制柄。
 */
export function buildFlowLayout(root: FlowNode, expanded: Set<string>): FlowLayout {
  let cursor = PAD
  let maxDepth = 0
  const nodes: FlowNode[] = []
  const edges: FlowEdge[] = []

  const visit = (src: FlowNode, depth: number): FlowNode => {
    const node: FlowNode = { ...src, depth, x: PAD + depth * (NODE_W + H_GAP), y: 0 }
    if (depth > maxDepth) maxDepth = depth

    const kids =
      src.hasChildren && expanded.has(src.key)
        ? src.children.map((child) => visit(child, depth + 1))
        : []

    if (!kids.length) {
      node.y = cursor
      cursor += NODE_H + V_GAP
    } else {
      node.y = (kids[0].y + kids[kids.length - 1].y) / 2
    }

    nodes.push(node)

    const from = outPort(node)
    kids.forEach((child) => {
      const to = inPort(child)
      const dx = Math.max(36, (to.x - from.x) / 2)
      edges.push({
        key: `${node.key}->${child.key}`,
        from: node.key,
        to: child.key,
        path: `M ${from.x} ${from.y} C ${from.x + dx} ${from.y} ${to.x - dx} ${to.y} ${to.x} ${to.y}`,
      })
    })

    return node
  }

  visit(root, 0)

  return {
    nodes,
    edges,
    width: PAD * 2 + maxDepth * (NODE_W + H_GAP) + NODE_W,
    height: cursor - V_GAP + PAD,
  }
}

/** 在树中按 key 查找节点 */
export function findFlowNode(root: FlowNode, key: string): FlowNode | null {
  if (root.key === key) return root
  for (const child of root.children) {
    const hit = findFlowNode(child, key)
    if (hit) return hit
  }
  return null
}

/** 返回从根到目标节点的完整路径（用于展示上级归属） */
export function findFlowPath(root: FlowNode, key: string, trail: FlowNode[] = []): FlowNode[] {
  const next = [...trail, root]
  if (root.key === key) return next
  for (const child of root.children) {
    const hit = findFlowPath(child, key, next)
    if (hit.length) return hit
  }
  return []
}

/** 收集整棵树的 key（展开全部用） */
export function collectKeys(root: FlowNode, keys = new Set<string>()): Set<string> {
  keys.add(root.key)
  root.children.forEach((child) => collectKeys(child, keys))
  return keys
}

export const TYPE_LABEL: Record<FlowNodeType, string> = {
  root: '总部',
  college: '学院',
  major: '专业',
  class: '班级',
}

export const CHILD_UNIT: Record<FlowNodeType, string> = {
  root: '学院',
  college: '专业',
  major: '班级',
  class: '',
}