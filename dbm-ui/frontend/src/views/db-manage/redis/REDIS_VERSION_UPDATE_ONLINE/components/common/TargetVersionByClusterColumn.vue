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
    field="target_version"
    :label="t('目标版本')"
    :loading="loading"
    required
    :width="300">
    <EditableSelect
      v-model="modelValue"
      :clearable="false">
      <BkOption
        v-for="(item, index) in versions"
        :id="item"
        :key="item"
        :name="item">
        <TextOverflowLayout>
          {{ item }}
          <template #append>
            <BkTag
              v-if="isCurrentVersion(item)"
              class="ml-4"
              size="small"
              theme="info">
              {{ t('当前版本') }}
            </BkTag>
            <BkTag
              v-if="index === 0"
              class="ml-4"
              size="small"
              theme="warning">
              {{ t('推荐') }}
            </BkTag>
          </template>
        </TextOverflowLayout>
      </BkOption>
    </EditableSelect>
  </EditableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getClusterVersions } from '@services/source/redisToolbox';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  interface Props {
    clusterId: number;
    currentVersions?: string[];
    nodeType: string;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string>();

  const { t } = useI18n();

  const {
    data: versions,
    loading,
    run: runGetClusterVersions,
  } = useRequest(getClusterVersions, {
    manual: true,
  });

  watch(
    () => props.clusterId,
    () => {
      if (props.clusterId && props.nodeType) {
        runGetClusterVersions({
          cluster_id: props.clusterId,
          node_type: props.nodeType,
          type: 'update',
        });
      }
    },
    {
      immediate: true,
    },
  );

  const isCurrentVersion = (value: string) => (props.currentVersions || []).includes(value);
</script>
