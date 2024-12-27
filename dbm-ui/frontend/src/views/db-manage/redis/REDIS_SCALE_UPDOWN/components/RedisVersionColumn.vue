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
  <Column
    field="version"
    :label="t('Redis版本')"
    :min-width="150"
    required>
    <Select
      v-model="modelValue"
      :disabled="!clusterId"
      :input-search="false"
      :list="versionList"
      :placeholder="t('自动生成')">
      <template #option="{ item, index }">
        <div>
          {{ item.label }}
          <BkTag
            v-if="modelValue === item.value"
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
        </div>
      </template>
    </Select>
  </Column>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getClusterVersions } from '@services/source/redisToolbox';

  import { Column, Select } from '@components/editable-table/Index.vue';

  interface Props {
    clusterId: number;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string>({
    default: '',
  });

  const { t } = useI18n();

  const versionList = ref<
    {
      value: string;
      label: string;
    }[]
  >([]);

  const { run: fetchVersions } = useRequest(getClusterVersions, {
    manual: true,
    onSuccess(versions) {
      versionList.value = versions.map((item) => ({
        label: item,
        value: item,
      }));
    },
  });

  watch(
    () => props.clusterId,
    () => {
      if (props.clusterId) {
        fetchVersions({
          node_type: 'Backend',
          type: 'update',
          cluster_id: props.clusterId,
        });
      }
    },
  );
</script>
