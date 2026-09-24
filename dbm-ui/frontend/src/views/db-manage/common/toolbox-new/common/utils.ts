import pinyin from 'tiny-pinyin';

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

/** 判断树节点是否含子分组（二级分组结构） */
export function hasChildGroups(node: ToolboxTreeNode): boolean {
  return node.children.length > 0 && isTreeNode(node.children[0]);
}

/** 获取树节点直接挂载的叶子节点 */
export function getLeafChildren(node: ToolboxTreeNode): ToolboxLeafNode[] {
  return node.children.filter((item): item is ToolboxLeafNode => isLeafNode(item));
}

/**
 * 工具名搜索匹配：忽略大小写，支持拼音全拼与首字母
 * @example isSearchMatched('jk', '健康检查') // true
 */
export function isSearchMatched(searchKey: string, name: string): boolean {
  const keyword = searchKey.trim().toLowerCase();
  if (!keyword) {
    return true;
  }
  if (name.toLowerCase().includes(keyword)) {
    return true;
  }
  const pinyinList = pinyin.parse(name).map((item) => item.target.toLowerCase());
  const fullPinyin = pinyinList.join('');
  const initials = pinyinList.reduce((result, item) => result + item[0], '');
  return fullPinyin.includes(keyword) || initials.includes(keyword);
}
