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

import _ from 'lodash';
import type { ComputedRef } from 'vue';

import { getLevelConfig } from '@services/source/configs';

type ParameterConfigItem = ServiceReturnType<typeof getLevelConfig>['conf_items'][number];
type DiffData = ComputedRef<ParameterConfigItem[]> | ParameterConfigItem[];

export type DiffItem = {
  name: string;
  status: string;
  before: ParameterConfigItem;
  after: ParameterConfigItem;
};

export const useDiff = (data: DiffData, origin: DiffData) => {
  const state = reactive({
    count: {
      create: 0,
      update: 0,
      delete: 0,
    },
    data: [] as any,
  });

  const diff = () => {
    state.data = [];

    const cloneData = _.cloneDeep(unref(data));
    const cloneOrigin = _.cloneDeep(unref(origin));

    // add items
    const created = _.differenceBy(cloneData, cloneOrigin, 'conf_name');
    state.count.create = created.length;
    for (const item of created) {
      state.data.push({
        name: item.conf_name,
        status: 'create',
        before: {},
        after: item,
      });
    }

    // delete items
    const deleted = _.differenceBy(cloneOrigin, cloneData, 'conf_name');
    state.count.delete = deleted.length;
    for (const item of deleted) {
      state.data.push({
        name: item.conf_name,
        status: 'delete',
        before: item,
        after: {},
      });
    }

    // updated items
    const excludesMap: { [key: string]: boolean } = {};
    for (const item of state.data) {
      excludesMap[item.name] = true;
    }
    // 剩余对比项
    const remainingData = cloneData.filter((item) => excludesMap[item.conf_name] !== true);
    // 发生变更 items
    const updated = _.differenceWith(remainingData, cloneOrigin, _.isEqual);
    state.count.update = updated.length;

    const originNames: { [key: string]: ParameterConfigItem } = {};
    for (const item of cloneOrigin) {
      originNames[item.conf_name] = item;
    }
    for (const item of updated) {
      state.data.push({
        name: item.conf_name,
        status: 'update',
        before: originNames[item.conf_name] || {},
        after: item,
      });
    }

    // 过滤掉参数项为空的项
    state.data = state.data.filter((item: DiffItem) => item.name);
  };

  watch(() => data, diff, { immediate: true, deep: true });

  return state;
};
