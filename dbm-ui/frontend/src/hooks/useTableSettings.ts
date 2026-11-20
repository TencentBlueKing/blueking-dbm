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

import { useUserProfile } from '@stores';

interface Settings {
  /**
   * 旧方案（保存显示列）下，后续迭代新增且需要默认显示的列
   * @deprecated 新方案保存隐藏列，新增列默认显示；仅用于转换旧数据，不要再新增配置
   */
  appendColumns?: string[];
  disabled?: string[];
  fontSize?: 'large' | 'medium';
  /**
   * 默认隐藏的列，仅在用户未保存过列设置时生效
   */
  hidden?: string[];
  /**
   * 后续迭代新增的列在用户已保存列顺序中的位置：key 为新列，value 为要插到其前面的列。
   * 不配置时新列沿用表格默认行为，补在已保存顺序的最后
   */
  insertColumnsBefore?: Record<string, string>;
  order?: string[];
  rowSize?: 'large' | 'medium' | 'mini' | 'small';
  /**
   * 兼容历史用户配置，新增配置统一使用 rowSize。
   */
  size?: 'medium' | 'mini' | 'small';
}

/**
 * 用户个人配置中保存的数据，checked / appendColumns 为旧方案字段
 */
interface ProfileSettings {
  appendColumns?: string[];
  checked?: string[];
  fontSize?: Settings['fontSize'];
  hidden?: string[];
  order?: string[];
  rowSize?: Settings['rowSize'];
  size?: Settings['size'];
}

interface SettingsChangePayload {
  fontSize?: Settings['fontSize'];
  hidden?: string[];
  order?: string[];
  rowSize?: Settings['rowSize'];
  size?: Settings['size'];
}

/**
 * 已保存的列顺序里没有新列时，把新列插到配置的目标列前面；目标列不在顺序中时不处理
 */
const insertColumnsToOrder = (order: string[] | undefined, insertColumnsBefore?: Record<string, string>) => {
  if (!order || !insertColumnsBefore) {
    return order;
  }
  const result = [...order];
  Object.entries(insertColumnsBefore).forEach(([column, beforeColumn]) => {
    const beforeIndex = result.indexOf(beforeColumn);
    if (result.includes(column) || beforeIndex < 0) {
      return;
    }
    result.splice(beforeIndex, 0, column);
  });
  return result;
};

/**
 * 用户个人配置表头字段
 */
export const useTableSettings = (key: string, defaultSettings: Settings) => {
  const userProfileStore = useUserProfile();

  // 获取用户配置的表头信息
  const settings = computed(() => {
    const profileSettings = userProfileStore.profile[key] as ProfileSettings | undefined;
    const savedAppendColumnSet = new Set(profileSettings?.appendColumns);
    // 旧方案下用户保存配置之后才新增、需要强制显示的列
    const pendingAppendColumns = (defaultSettings.appendColumns ?? []).filter(
      (column) => !savedAppendColumnSet.has(column),
    );
    const pendingAppendColumnSet = new Set(pendingAppendColumns);

    let hidden = profileSettings?.hidden;
    let checked: string[] | undefined;
    if (!hidden && profileSettings?.checked) {
      if (profileSettings.order) {
        // 旧数据转换：旧方案每次保存的 order 即当时的全部列，未选中的就是隐藏列
        const checkedSet = new Set(profileSettings.checked);
        hidden = profileSettings.order.filter(
          (column) => !checkedSet.has(column) && !pendingAppendColumnSet.has(column),
        );
      } else {
        // 更早的旧数据没有 order，无法得知全部列，交给表格按列定义计算
        checked = Array.from(new Set(profileSettings.checked.concat(pendingAppendColumns)));
      }
    }
    // 用户未保存过列设置时使用默认隐藏列
    if (!hidden && !checked) {
      hidden = defaultSettings.hidden;
    }

    const rowSize =
      profileSettings?.rowSize ?? profileSettings?.size ?? defaultSettings.rowSize ?? defaultSettings.size ?? 'small';

    return {
      checked,
      disabled: defaultSettings.disabled,
      fontSize: profileSettings?.fontSize ?? defaultSettings.fontSize ?? 'medium',
      hidden,
      order: insertColumnsToOrder(profileSettings?.order ?? defaultSettings.order, defaultSettings.insertColumnsBefore),
      rowSize,
      size: rowSize === 'large' ? undefined : rowSize,
    };
  });

  /**
   * 更新表头设置，只保存新方案字段，旧方案字段随之清除
   */
  const updateTableSettings = (payload?: SettingsChangePayload) => {
    if (!payload) return;

    const rowSize = payload.rowSize ?? payload.size;
    userProfileStore.updateProfile({
      label: key,
      values: {
        fontSize: payload.fontSize,
        hidden: payload.hidden,
        order: payload.order,
        rowSize,
        size: rowSize,
      },
    });
  };

  return {
    settings,
    updateTableSettings,
  };
};
