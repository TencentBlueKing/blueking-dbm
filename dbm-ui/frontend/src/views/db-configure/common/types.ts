/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */

import BizConfTopoTreeModel from '@services/model/config/biz-conf-topo-tree';

import type { ConfLevels } from '@common/const';

/**
 * 树节点数据
 */
export type TreeData = {
  children: TreeData[];
  /** 模块下挂载的集群列表（不进入树渲染，仅用于展示"关联集群"等业务信息） */
  clusters?: TreeData[];
  data?: BizConfTopoTreeModel;
  id: number;
  isOpen?: boolean;
  levelType: ConfLevels;
  name: string;
  parentId: string;
  tag: string;
  treeId: string;
  version?: string;
};

/**
 * 树 state
 */
export type TreeState = {
  activeNode?: TreeData;
  data: TreeData[];
  isAnomalies: boolean;
  loading: boolean;
  search: string;
  selected?: TreeData;
};

/** 模块信息类型定义 */
export interface ModuleInfo {
  bufferPercent?: string; // 内存分片比率 (SqlServer)
  charset: string; // 字符集
  maxRemainMemGb?: string; // 最大OS保留内存 (SqlServer)
  moduleId: number;
  moduleName: string;
  relatedClusterCount: number;
  relatedClusters: string;
  spiderVersion?: string; // 接入层版本 (TenDBCluster)
  syncType?: string; // 主从方式 (SqlServer)
  systemVersion?: string; // 操作系统版本 (SqlServer)
  updatedAt: string;
  updatedBy: string;
  version: string; // 数据库版本
}
