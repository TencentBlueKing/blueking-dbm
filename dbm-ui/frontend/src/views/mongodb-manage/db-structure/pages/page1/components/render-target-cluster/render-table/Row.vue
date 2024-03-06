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
  <tr>
    <td style="padding: 0">
      <RenderText
        :data="data.cluster_name"
        :placeholder="t('自动生成')" />
    </td>
    <td
      v-if="index === 0"
      :rowspan="counts"
      style="padding: 0">
      <RenderType @struct-type-change="handleStructTypeChange" />
    </td>
    <td
      v-if="isBackupRecordType"
      style="padding: 0">
      <RenderBackupFile
        ref="backupFileRef"
        :cluster-id="data.id"
        :cluster-type="clusterType" />
    </td>
    <template v-else>
      <td
        v-if="index === 0"
        :rowspan="counts"
        style="padding: 0">
        <RenderTargetTime ref="targetTimeRef" />
      </td>
    </template>
    <td style="padding: 0">
      <BkButton
        class="ml-16"
        text
        theme="primary"
        @click="handleRemove">
        {{ t('删除') }}
      </BkButton>
    </td>
  </tr>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import RenderBackupFile from './RenderBackupFile.vue';
  import RenderTargetTime from './RenderTargetTime.vue';
  import RenderType from './RenderType.vue';

  interface Props {
    index: number;
    counts: number;
    data: {
      cluster_name: string;
      id: number;
    };
    clusterType: string;
    isBackupRecordType: boolean;
  }

  interface Emits {
    (e: 'remove', value: number): void;
    (e: 'structTypeChange', value: string): void;
  }

  interface Exposes {
    getValue: () => Promise<any>;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const backupFileRef = ref<InstanceType<typeof RenderBackupFile>>();
  const targetTimeRef = ref<InstanceType<typeof RenderTargetTime>>();

  const handleRemove = () => {
    emits('remove', props.index);
  };

  const handleStructTypeChange = (value) => {
    emits('structTypeChange', value);
  };

  defineExpose<Exposes>({
    async getValue() {
      if (props.isBackupRecordType) {
        return await backupFileRef.value?.getValue();
      }
      return await targetTimeRef.value?.getValue();
    },
  });
</script>
