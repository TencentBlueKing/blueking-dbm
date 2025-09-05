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
    :label="t('版本')"
    required
    :width="200">
    <EditableBlock :placeholder="t('自动生成')">
      <div
        v-for="name in modelValue"
        :key="name"
        v-overflow-title>
        {{ name }}
      </div>
    </EditableBlock>
  </EditableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getClusterVersions } from '@services/source/redisToolbox';

  interface Props {
    clusterId: number;
  }

  const props = defineProps<Props>();
  const modelValue = defineModel<string[]>();

  const { t } = useI18n();

  const { run: fetchCurrentClusterVersions } = useRequest(getClusterVersions, {
    manual: true,
    onSuccess(versions) {
      modelValue.value = versions;
    },
  });

  watch(
    () => props.clusterId,
    () => {
      if (props.clusterId) {
        fetchCurrentClusterVersions({
          cluster_id: props.clusterId,
          node_type: 'Backend',
          type: 'online',
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less" scoped>
  .render-text-box {
    position: relative;
    width: 100%;
    min-height: 42px;
    padding: 10px 16px;
    overflow: hidden;
    line-height: 20px;
    color: #63656e;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .default-display {
    cursor: not-allowed;
    background: #fafbfd;
  }
</style>
