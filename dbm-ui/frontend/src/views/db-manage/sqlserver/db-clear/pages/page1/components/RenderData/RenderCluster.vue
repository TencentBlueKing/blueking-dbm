<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <TableEditInput
    ref="editRef"
    v-model="localDomain"
    multi-input
    :placeholder="t('请输入集群')"
    :rules="rules" />
</template>
<script lang="ts">
  const clusterIdMemo: { [key: string]: Record<string, boolean> } = {};
</script>
<script setup lang="ts">
  import { onBeforeUnmount, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import SqlServerHaClusterDetailModel from '@services/model/sqlserver/sqlserver-ha-detail';
  import { filterClusters } from '@services/source/dbbase';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  import { random } from '@utils';

  interface Exposes {
    getValue: () => Promise<Record<string, number>>;
  }

  const modelValue = defineModel<{
    id: number;
    domain: string;
    cloudId: null | number;
  }>();

  const instanceKey = `render_cluster_${random()}`;
  clusterIdMemo[instanceKey] = {};

  const { t } = useI18n();

  const editRef = ref<InstanceType<typeof TableEditInput>>();

  const localClusterId = ref(0);
  const localDomain = ref('');

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('目标集群不能为空'),
    },
    {
      validator: (value: string) =>
        filterClusters<SqlServerHaClusterDetailModel>({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          exact_domain: value,
        }).then((data) => {
          if (data.length > 0) {
            localClusterId.value = data[0].id;
            modelValue.value = {
              id: data[0].id,
              cloudId: data[0].bk_cloud_id,
              domain: data[0].master_domain,
            };
            return true;
          }
          modelValue.value = undefined;
          return false;
        }),
      message: t('目标集群不存在'),
    },
    {
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
        for (let i = 0; i < currentSelectClusterIdList.length; i++) {
          if (otherClusterIdMap[currentSelectClusterIdList[i]]) {
            return false;
          }
        }
        return true;
      },
      message: t('目标集群重复'),
    },
  ];

  // 同步外部值
  watch(
    modelValue,
    () => {
      const { id = 0, domain = '' } = modelValue.value || {};
      localClusterId.value = id;
      localDomain.value = domain;
    },
    {
      immediate: true,
    },
  );

  // 获取关联集群
  watch(
    localClusterId,
    () => {
      if (!localClusterId.value) {
        return;
      }
      clusterIdMemo[instanceKey][localClusterId.value] = true;
    },
    {
      immediate: true,
    },
  );

  onBeforeUnmount(() => {
    delete clusterIdMemo[instanceKey];
  });

  defineExpose<Exposes>({
    getValue() {
      // 用户输入未完成验证
      return editRef.value!.getValue().then(() => ({
        cluster_id: localClusterId.value,
      }));
    },
  });
</script>
