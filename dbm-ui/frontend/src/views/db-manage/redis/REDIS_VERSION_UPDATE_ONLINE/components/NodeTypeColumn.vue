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
  <EditableColumn
    ref="editableTableColumn"
    field="node_type"
    :label="t('节点类型')"
    required
    :width="150">
    <template #headAppend>
      <BatchEditColumn
        :confirm-handler="handleBatchEditConfirm"
        :label="t('节点类型')">
        <BatchEditSelect
          v-model="batchEditValue"
          :list="selectList" />
      </BatchEditColumn>
    </template>
    <EditableSelect
      v-model="modelValue"
      :clearable="false"
      :disabled="!cluster.id"
      :list="selectList" />
  </EditableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes } from '@common/const';

  import BatchEditColumn, { BatchEditSelect } from '@views/db-manage/common/batch-edit-column-new/Index.vue';

  interface Props {
    cluster: {
      id: number;
    };
    clusterType?: string;
  }

  type Emits = (e: 'batch-edit', value: string, field: string) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<string>({
    default: 'Backend',
  });

  const { t } = useI18n();

  const batchEditValue = ref('');

  const selectList = computed(() => {
    const nodeTypeList = [
      {
        label: 'Backend',
        value: 'Backend',
      },
    ];

    if (props.clusterType !== ClusterTypes.REDIS_INSTANCE) {
      nodeTypeList.push({
        label: 'Proxy',
        value: 'Proxy',
      });
    }

    return nodeTypeList;
  });

  watch(
    () => props.clusterType,
    () => {
      if (props.clusterType === ClusterTypes.REDIS_INSTANCE) {
        modelValue.value = 'Backend';
      }
    },
  );

  const handleBatchEditConfirm = () => {
    emits('batch-edit', batchEditValue.value, 'node_type');
  };
</script>
