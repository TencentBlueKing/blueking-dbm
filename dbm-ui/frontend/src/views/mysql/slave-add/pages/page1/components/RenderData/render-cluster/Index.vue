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
    v-if="isEdit"
    ref="editRef"
    v-model="relatedClusterDisplayInfo.cluster_domain"
    :placeholder="t('请输入或选择集群')"
    :rules="rules"
    @submit="handleInputFinish" />
  <ClusterRelatedInput
    v-else
    v-model="isEdit"
    :data="relatedClusterDisplayInfo"
    :placeholder="t('请输入集群域名')"
    @change-related="(value: number[]) => handleChangeRelated(value)" />
</template>
<script lang="ts">
  const clusterIdMemo: { [key: string]: Record<string, boolean> } = {};
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { filterClusters } from '@services/source/dbbase';
  import { findRelatedClustersByClusterIds } from '@services/source/mysqlCluster';

  import TableEditInput from '@components/render-table/columns/input/index.vue';

  import { random } from '@utils';

  import type { IDataRow } from '../Row.vue';

  import ClusterRelatedInput, { type Props as ClusterRelatedInputProps } from './ClusterRelatedInput.vue';

  interface Props {
    modelValue: IDataRow;
  }

  interface Emits {
    (e: 'idChange', value: { id: number; cloudId: number | null }): void;
  }

  interface Exposes {
    getValue: () => Record<'cluster_ids', Array<number>>;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const instanceKey = `render_cluster_${random()}`;
  clusterIdMemo[instanceKey] = {};

  const editRef = ref<InstanceType<typeof TableEditInput>>();
  const isEdit = ref(true);
  const isShowEdit = ref(true);

  const relatedClusterDisplayInfo = reactive<ClusterRelatedInputProps['data']>({
    cluster_id: 0,
    cluster_domain: '',
    cluster_related: [],
    checked_related: [],
  });

  const { run: fetchRelatedClustersByClusterIds } = useRequest(findRelatedClustersByClusterIds, {
    manual: true,
    onSuccess(results) {
      isEdit.value = false;
      const currentItem = results[0];
      relatedClusterDisplayInfo.cluster_related = currentItem.related_clusters;
      relatedClusterDisplayInfo.checked_related = currentItem.related_clusters;
    },
  });

  const rules = [
    {
      validator: (value: string) => {
        if (value) {
          return true;
        }
        return false;
      },
      message: t('目标集群不能为空'),
    },
    {
      validator: (value: string) =>
        filterClusters({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          exact_domain: value,
        }).then((data) => {
          if (data.length > 0) {
            relatedClusterDisplayInfo.cluster_domain = data[0].master_domain;
            relatedClusterDisplayInfo.cluster_id = data[0].id;
            emits('idChange', {
              id: data[0].id,
              cloudId: data[0].bk_cloud_id,
            });
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
    () => props.modelValue,
    () => {
      if (props.modelValue.clusterData) {
        relatedClusterDisplayInfo.cluster_id = props.modelValue.clusterData.id;
        relatedClusterDisplayInfo.cluster_domain = props.modelValue.clusterData.domain;
        isShowEdit.value = false;
      } else {
        isShowEdit.value = true;
      }
    },
    {
      immediate: true,
    },
  );

  // 获取关联集群
  watch(
    () => relatedClusterDisplayInfo.cluster_id,
    () => {
      const clusterId = relatedClusterDisplayInfo.cluster_id;
      if (!clusterId) {
        return;
      }

      clusterIdMemo[instanceKey][clusterId] = true;
      fetchRelatedClustersByClusterIds({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        cluster_ids: [clusterId],
      });
    },
    {
      immediate: true,
    },
  );

  watch(isEdit, () => {
    if (isEdit.value) {
      nextTick(() => {
        editRef.value?.focus();
      });
    }
  });

  const handleInputFinish = () => {
    nextTick(() => {
      if (relatedClusterDisplayInfo.cluster_domain) {
        isEdit.value = false;
      }
    });
  };

  /**
   * 切换关联集群选中
   */
  const handleChangeRelated = (values: number[]) => {
    relatedClusterDisplayInfo.checked_related = relatedClusterDisplayInfo.cluster_related.filter((item) =>
      values.includes(item.id),
    );
  };

  onBeforeUnmount(() => {
    delete clusterIdMemo[instanceKey];
  });

  defineExpose<Exposes>({
    getValue() {
      return {
        cluster_ids: [
          relatedClusterDisplayInfo.cluster_id,
          ...relatedClusterDisplayInfo.checked_related.map((item) => item.id),
        ],
      };
    },
  });
</script>
