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

import type { Settings } from 'bkui-vue/lib/table/props';
import _ from 'lodash';

import { useUserProfile } from '@stores';

type TableSettingKeys = keyof Settings;

/**
 * 用户个人配置表头字段
 */
export const useTableSettings = (key: string, defaultSettings: Settings) => {
  const userProfileStore = useUserProfile();
  // 获取用户配置的表头信息
  const settings = reactive(getSettings(userProfileStore.profile[key] || defaultSettings));

  // 初始化设置
  if (userProfileStore.profile[key] === undefined) {
    updateTableSettings(defaultSettings);
  }

  function getSettings(updateSettings: Settings) {
    const values: Settings = Object.assign({}, defaultSettings);
    if (defaultSettings && updateSettings) {
      // 获取后续新增字段
      const newFields = [];
      const defaultFields = defaultSettings.fields || [];
      const updateFields = (updateSettings.fields || []).map(item => item.field);
      for (const item of defaultFields) {
        // 新增字段
        if (item.field && !updateFields.includes(item.field)) {
          newFields.push(item);
        }
      }

      for (const key of Object.keys(values)) {
        const settingKey = key as TableSettingKeys;

        // 以 default settings 为准设置 fields，确保增删生效
        if (settingKey === 'fields') {
          continue;
        }

        // 设置新增字段选中
        if (settingKey === 'checked') {
          const checked = updateSettings.checked || [];
          const defaultChecked = defaultSettings.checked || [];
          // 必须勾选项
          const disabledFieldsChecked = (defaultSettings.fields || [])
            .filter(item => item.field && item.disabled)
            .map(item => item.field as string);
          // 新增字段默认勾选项
          const newFieldsChecked = newFields
            .filter(item => item.field && defaultChecked.includes(item.field))
            .map(item => item.field as string);

          Object.assign(values, {
            [settingKey]: _.uniq(checked.concat(disabledFieldsChecked, newFieldsChecked)),
          });

          continue;
        }

        // 确保以 udpate settings 为准
        const defaultValue = values[settingKey];
        const updateValue = updateSettings[settingKey];
        if (defaultValue && updateValue) {
          Object.assign(values, {
            [settingKey]: updateValue,
          });
        }
      }
    } else {
      Object.assign(values, updateSettings);
    }

    return values;
  }

  /**
   * 更新表头设置
   */
  function updateTableSettings(updateSettings: Settings) {
    userProfileStore.updateProfile({
      label: key,
      values: getSettings(updateSettings),
    });
  }

  return {
    settings,
    updateTableSettings,
  };
};
