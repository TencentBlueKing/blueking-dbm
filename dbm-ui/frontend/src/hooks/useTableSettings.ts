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
  disabled?: string[];
  checked?: string[];
  size?: 'medium' | 'mini' | 'small';
}

// type TableSettingKeys = keyof Settings;

/**
 * 用户个人配置表头字段
 */
export const useTableSettings = (key: string, defaultSettings: Settings) => {
  const userProfileStore = useUserProfile();

  // 获取用户配置的表头信息
  const settings = shallowRef<{ checked?: string[]; disabled?: string[]; size?: string }>();
  settings.value = {
    checked: userProfileStore.profile[key]?.checked || defaultSettings.checked,
    disabled: defaultSettings.disabled,
    size: userProfileStore.profile[key]?.size || defaultSettings.size || 'small',
  };

  /**
   * 更新表头设置
   */
  const updateTableSettings = (updateSettings: Settings) => {
    userProfileStore.updateProfile({
      label: key,
      values: {
        checked: updateSettings.checked,
        size: updateSettings.size,
      },
    });
  };

  return {
    settings,
    updateTableSettings,
  };
};
