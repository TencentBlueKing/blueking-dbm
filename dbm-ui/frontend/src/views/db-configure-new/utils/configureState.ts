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

const STORAGE_KEY = 'dbConfigureState';

interface ConfigureState {
  /** 当前激活的 tab（conf_type 或 conf_file） */
  activeTab?: string;
  /** 选中的树节点 parentId */
  selectedParentId?: string;
  /** 选中的树节点 treeId */
  selectedTreeId?: string;
}

/**
 * 获取保存的状态
 */
export const getConfigureState = (): ConfigureState => {
  try {
    const savedState = sessionStorage.getItem(STORAGE_KEY);
    if (savedState) {
      return JSON.parse(savedState);
    }
  } catch {
    // 忽略解析错误
  }
  return {};
};

/**
 * 保存状态到 sessionStorage
 * @param partialState 部分状态，会与现有状态合并
 */
export const saveConfigureState = (partialState: Partial<ConfigureState>) => {
  try {
    const savedState = sessionStorage.getItem(STORAGE_KEY);
    const state: ConfigureState = savedState ? JSON.parse(savedState) : {};
    Object.assign(state, partialState);
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {
    // 忽略存储错误
  }
};

/**
 * 重置 tab 状态（切换 treeNode 或 clusterTab 时调用）
 */
export const resetConfigureTab = () => {
  try {
    const savedState = sessionStorage.getItem(STORAGE_KEY);
    if (savedState) {
      const state: ConfigureState = JSON.parse(savedState);
      delete state.activeTab;
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    }
  } catch {
    // 忽略存储错误
  }
};

/**
 * 清除所有状态
 */
export const clearConfigureState = () => {
  try {
    sessionStorage.removeItem(STORAGE_KEY);
  } catch {
    // 忽略存储错误
  }
};
