export interface ToolboxLeafNode {
  bind?: string[];
  dbConsoleValue: string;
  desc: string;
  id: string;
  isFix?: boolean;
  isPrimary?: boolean;
  name: string;
}

export interface ToolboxTreeNode {
  children: (ToolboxTreeNode | ToolboxLeafNode)[];
  icon: string;
  id: string;
  name: string;
}

/** 菜单节点联合类型 */
export type ToolboxMenuNode = ToolboxTreeNode | ToolboxLeafNode;
