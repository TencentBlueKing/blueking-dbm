import type { ToolboxLeafNode, ToolboxMenuNode, ToolboxTreeNode } from './types';

/**
 * 判断是否为树节点（有 children 属性）
 * @example
 * if (isTreeNode(node)) {
 *   node.children // ✅ 安全访问
 * }
 */
export function isTreeNode(node: ToolboxMenuNode): node is ToolboxTreeNode {
  return 'children' in node;
}

/**
 * 判断是否为叶子节点（无 children 属性）
 * @example
 * if (isLeafNode(node)) {
 *   node.isPrimary // ✅ 安全访问
 * }
 */
export function isLeafNode(node: ToolboxMenuNode): node is ToolboxLeafNode {
  return !('children' in node);
}
