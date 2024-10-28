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
  <span v-show="isEdit">
    <TableEditInput
      ref="editRef"
      :model-value="relatedClusterDisplayInfo"
      @cluster-change="handleInputFinish" />
  </span>
  <ClusterRelatedInput
    v-if="!isEdit"
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

  import { findRelatedClustersByClusterIds } from '@services/source/mysqlCluster';

  import TableEditInput from '@views/db-manage/mysql/common/edit-field/ClusterNameWithSelector.vue';

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
    getValue: () => Promise<Record<'cluster_ids', Array<number>>>;
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
    id: 0,
    domain: '',
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

  // 同步外部值
  watch(
    () => props.modelValue,
    () => {
      if (props.modelValue.clusterData) {
        relatedClusterDisplayInfo.id = props.modelValue.clusterData.id;
        relatedClusterDisplayInfo.domain = props.modelValue.clusterData.domain;
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
    () => relatedClusterDisplayInfo.id,
    () => {
      const clusterId = relatedClusterDisplayInfo.id;
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

  const handleInputFinish = (info: { id: number; domain: string; cloudId: number }) => {
    console.log('info: ', info);
    if (info.domain) {
      relatedClusterDisplayInfo.domain = info.domain;
      relatedClusterDisplayInfo.id = info.id;

      emits('idChange', {
        id: info.id,
        cloudId: info.cloudId,
      });
      nextTick(() => {
        isEdit.value = false;
      });
    }
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
      return editRef.value!.getValue().then(() => ({
        cluster_ids: [
          relatedClusterDisplayInfo.id,
          ...relatedClusterDisplayInfo.checked_related.map((item) => item.id),
        ],
      }));
    },
  });
</script>
