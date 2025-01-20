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
    field="load_modules"
    label="Module"
    required
    :width="200">
    <EditableSelect
      v-model="moduleValue"
      :clearable="false"
      collapse-tags
      :disabled="!params.clusterId"
      :list="selectList"
      multiple
      multiple-mode="tag">
      <template #option="{ item }">
        {{ item.label }}
        <BkTag
          v-if="item.disabled"
          class="ml-4"
          size="small"
          theme="success">
          {{ t('已安装') }}
        </BkTag>
      </template>
    </EditableSelect>
  </EditableColumn>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getRedisClusterModuleInfo } from '@services/source/redisToolbox';

  interface Props {
    params: {
      clusterId?: number;
      version?: string;
    };
  }

  const props = defineProps<Props>();

  const moduleValue = defineModel<string[]>({
    required: true,
  });

  const { t } = useI18n();

  const selectList = shallowRef<
    {
      disabled: boolean;
      value: string;
      label: string;
    }[]
  >([]);

  const { run: fetchClusterModule } = useRequest(getRedisClusterModuleInfo, {
    manual: true,
    onSuccess({ results }) {
      selectList.value = Object.entries(results).map(([key, value]) => ({
        disabled: value,
        value: key,
        label: key,
      }));
    },
  });

  watch(
    () => [props.params.clusterId, props.params.version],
    () => {
      if (props.params.clusterId && props.params.version) {
        fetchClusterModule({
          cluster_id: props.params.clusterId,
          version: props.params.version,
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>

<style lang="less" scoped>
  :deep(.bk-select-tag) {
    border: none !important;
    box-shadow: none !important;
  }
</style>
