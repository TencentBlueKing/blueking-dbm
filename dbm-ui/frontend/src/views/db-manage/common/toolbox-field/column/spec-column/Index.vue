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
    :label="t('机器规格')"
    :min-width="150">
    <EditableBlock
      v-if="!selectable"
      v-model="renderSpecName"
      :placeholder="t('自动生成')" />
    <EditableSelect
      v-else
      v-model="modelValue"
      display-key="spec_name"
      id-key="spec_id"
      :list="specList">
      <template #option="{ item }">
        {{ item.spec_name }}
        <BkTag
          v-if="item.spec_id === currentSpecId"
          class="ml-4"
          size="small"
          theme="success">
          {{ t('当前规格') }}
        </BkTag>
      </template>
    </EditableSelect>
  </EditableColumn>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getResourceSpecList } from '@services/source/dbresourceSpec';

  import { ClusterTypes, DBTypes, MachineTypes } from '@common/const';

  interface Props {
    clusterType: ClusterTypes | DBTypes;
    currentSpecId?: number;
    machineType?: MachineTypes;
    selectable?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    currentSpecId: -1,
    machineType: undefined,
    selectable: false,
  });

  const modelValue = defineModel<number>({
    required: true,
  });

  const { t } = useI18n();

  const specList = ref<ServiceReturnType<typeof getResourceSpecList>['results']>([]);

  const renderSpecName = computed(
    () => specList.value.find((item) => item.spec_id === modelValue.value)?.spec_name || '',
  );

  useRequest(getResourceSpecList, {
    defaultParams: [
      {
        enable: true,
        spec_cluster_type: props.clusterType,
        spec_machine_type: props.machineType,
      },
    ],
    onSuccess: (data) => {
      specList.value = data.results;
    },
  });

  watch(
    () => props.currentSpecId,
    () => {
      modelValue.value = props.currentSpecId;
    },
  );

  watchEffect(() => {
    // 如果 modelValue 被设置为 -1 或者其他负数时，则自动选择第一个规格
    if (modelValue.value < 0) {
      setTimeout(() => {
        modelValue.value = specList.value[0]?.spec_id || 0;
      }, 200);
    }
  });
</script>
