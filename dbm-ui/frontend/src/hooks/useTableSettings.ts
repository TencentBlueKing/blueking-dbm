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
  checked?: string[];
  disabled?: string[];
  fontSize?: 'large' | 'medium';
  order?: string[];
  rowSize?: 'large' | 'medium' | 'mini' | 'small';
  /**
   * 兼容历史用户配置，新增配置统一使用 rowSize。
   */
  size?: 'medium' | 'mini' | 'small';
}

interface SettingsChangePayload {
  columns?: string[];
  fontSize?: Settings['fontSize'];
  order?: string[];
  rowSize?: Settings['rowSize'];
  size?: Settings['size'];
}

/**
 * 用户个人配置表头字段
 */
export const useTableSettings = (key: string, defaultSettings: Settings) => {
  const userProfileStore = useUserProfile();

  // 获取用户配置的表头信息
  const settings = computed<Settings>(() => {
    const profileSettings = userProfileStore.profile[key];
    const rowSize =
      profileSettings?.rowSize ?? profileSettings?.size ?? defaultSettings.rowSize ?? defaultSettings.size ?? 'small';

    return {
      checked: profileSettings?.checked ?? defaultSettings.checked,
      disabled: defaultSettings.disabled,
      fontSize: profileSettings?.fontSize ?? defaultSettings.fontSize ?? 'medium',
      order: profileSettings?.order ?? defaultSettings.order,
      rowSize,
      size: rowSize === 'large' ? undefined : rowSize,
    };
  });

  /**
   * 更新表头设置
   */
  const updateTableSettings = (payload?: SettingsChangePayload) => {
    if (!payload) return;

    const rowSize = payload.rowSize ?? payload.size;
    userProfileStore.updateProfile({
      label: key,
      values: {
        checked: payload.columns,
        fontSize: payload.fontSize,
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
