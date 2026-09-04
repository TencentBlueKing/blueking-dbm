<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
    10| * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <EditableColumn
    field="srcCluster.clusterName"
    :label="t('数据源集群')"
    :min-width="120"
    :rules="rules"
    :width="220">
    <EditableInput
      v-model="clusterName"
      :placeholder="t('请输入或选择集群')" />
  </EditableColumn>
</template>
<script lang="ts">
  const clusterIdMemo: { [key: string]: Record<string, boolean> } = {};
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getTendbhaList } from '@services/source/tendbha';

  import { domainRegex } from '@common/regex';

  import { Column as EditableColumn, Input as EditableInput } from '@components/editable-table/Index.vue';

  import { random } from '@utils';

  const modelValue = defineModel<{
    clusterId: number;
    clusterName: string;
    moduleId: number;
  }>({
    required: true,
  });

  const { t } = useI18n();

  const instanceKey = `render_cluster_${random()}`;
  clusterIdMemo[instanceKey] = {};

  const clusterName = computed({
    get: () => modelValue.value.clusterName,
    set: (value) => {
      modelValue.value.clusterName = value;
    },
  });

  const rules = [
    {
      message: t('不能为空'),
      trigger: 'blur',
      validator: (value: string) => Boolean(value),
    },
    {
      message: t('目标集群输入格式有误'),
      trigger: 'blur',
      validator: (value: string) => domainRegex.test(value),
    },
    {
      message: t('目标集群不存在'),
      trigger: 'blur',
      validator: async (value: string) => {
        const ret = await getTendbhaList({ domain: value });
        const { results } = ret;
        if (results.length > 0) {
          const [item] = results;
          modelValue.value.clusterId = item.id;
          modelValue.value.moduleId = item.db_module_id;
          // 直接写已选记录，避免清空后重新输入同一集群时 watch 同值不触发导致漏记
          clusterIdMemo[instanceKey][item.id] = true;
        }
        return results.length > 0;
      },
    },
    {
      message: t('集群重复'),
      trigger: 'blur',
      validator: () => {
        const currentClusterSelectMap = clusterIdMemo[instanceKey];
        const otherClusterMemoMap = { ...clusterIdMemo };
        delete otherClusterMemoMap[instanceKey];

        const otherClusterIdMap = Object.values(otherClusterMemoMap).reduce(
          (result, item) => ({
            ...result,
            ...item,
          }),
          {} as Record<string, boolean>,
        );

        const currentSelectClusterIdList = Object.keys(currentClusterSelectMap);
        // eslint-disable-next-line @typescript-eslint/prefer-for-of
        for (let i = 0; i < currentSelectClusterIdList.length; i++) {
          if (otherClusterIdMap[currentSelectClusterIdList[i]]) {
            return false;
          }
        }
        return true;
      },
    },
  ];

  // 输入清空时当前实例的已选记录一并清空
  watch(clusterName, (value) => {
    if (!value) {
      clusterIdMemo[instanceKey] = {};
    }
  });

  // 获取关联集群
  watch(
    () => modelValue.value.clusterId,
    (clusterId) => {
      if (!clusterId) {
        return;
      }
      clusterIdMemo[instanceKey][clusterId] = true;
    },
    {
      immediate: true,
    },
  );

  onBeforeUnmount(() => {
    delete clusterIdMemo[instanceKey];
  });
</script>
