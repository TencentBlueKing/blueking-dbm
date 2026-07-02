/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DBM(BlueKing-BK-DBM) available.
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

import { useRequest } from 'vue-request';

import { getBuiltinLabels } from '@services/source/systemSettings';
import { listTag } from '@services/source/tag';

import { useGlobalBizs } from '@stores';

/**
 * 子策略按标签圈选：标签键值聚合
 *
 * 聚合 listTag(type:'cluster') + getBuiltinLabels，产出：
 * - keyValueMap：键 → 值列表（内置键为空数组）
 * - getTagId(key, value)：根据 key/value 查 ResourceTag.id（用于构造 cluster_tags 的 id）
 *
 * 失效判定由后端在 cluster_tags 每项返回 is_invalid 字段直接提供。
 */
export const useClusterTags = () => {
  const { currentBizId } = useGlobalBizs();

  const keyValueMap = ref<Record<string, string[]>>({});
  // (key, value) → ResourceTag.id 映射
  const tagIdMap = ref<Map<string, number>>(new Map());

  const { run: fetchBuiltinLabels } = useRequest(getBuiltinLabels, {
    manual: true,
    onSuccess(dataList) {
      dataList.forEach((innerKey) => {
        if (!keyValueMap.value[innerKey]) {
          keyValueMap.value = { ...keyValueMap.value, [innerKey]: [] };
        }
      });
    },
  });

  const { loading: isLoading } = useRequest(listTag, {
    defaultParams: [
      {
        bk_biz_id: currentBizId,
        limit: -1,
        offset: 0,
        type: 'cluster',
      },
    ],
    onSuccess(data) {
      const map = data.results.reduce<Record<string, string[]>>((results, item) => {
        if (results[item.key]) {
          results[item.key].push(item.value);
        } else {
          Object.assign(results, {
            [item.key]: [item.value],
          });
        }
        return results;
      }, {});
      keyValueMap.value = map;
      // 构建 (key, value) → id 映射
      tagIdMap.value = new Map(data.results.map((item) => [`${item.key}__${item.value}`, item.id]));
      fetchBuiltinLabels();
    },
  });

  /**
   * 根据 key/value 查 ResourceTag.id
   * 找不到时返回 0（新建场景，后端可按 tag_key/tag_value 自行处理）
   */
  const getTagId = (key: string, value: string): number => tagIdMap.value.get(`${key}__${value}`) ?? 0;

  return {
    getTagId,
    isLoading,
    keyValueMap,
  };
};
