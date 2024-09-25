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
    :model-value="modelValue?.domain"
    :placeholder="t('请输入集群')"
    :rules="rules" />
</template>
<script lang="ts">
  const clusterIdMemo: { [key: string]: Record<string, boolean> } = {};
</script>
<script setup lang="ts">
  import { onBeforeUnmount, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import { filterClusters } from '@services/source/dbbase';

  import { useGlobalBizs } from '@stores';

  import TableEditInput from '@views/db-manage/tendb-cluster/common/edit/Input.vue';

  import { random } from '@utils';

  import type { IDataRow } from './Row.vue';

  interface Exposes {
    getValue: () => Record<'cluster_id', number>;
  }

  const modelValue = defineModel<IDataRow['clusterData']>();

  const instanceKey = `render_cluster_${random()}`;
  clusterIdMemo[instanceKey] = {};

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const editRef = ref();

  const rules = [
    {
      validator: (value: string) => {
        if (value) {
          return true;
        }
        modelValue.value = undefined;
        return false;
      },
      message: t('目标集群不能为空'),
    },
    {
      validator: (value: string) =>
        filterClusters<TendbClusterModel>({
          exact_domain: value,
          bk_biz_id: currentBizId,
        }).then((data) => {
          if (data.length > 0) {
            const [clusterData] = data;
            modelValue.value = {
              id: clusterData.id,
              domain: clusterData.master_domain,
              bkCloudId: clusterData.bk_cloud_id,
              bkCloudName: clusterData.bk_cloud_name,
            };
            return true;
          }
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
      if (modelValue.value) {
        clusterIdMemo[instanceKey] = { [modelValue.value.id]: true };
      }
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
      return editRef.value.getValue().then(() => ({
        cluster_id: modelValue.value!.id,
      }));
    },
  });
</script>
