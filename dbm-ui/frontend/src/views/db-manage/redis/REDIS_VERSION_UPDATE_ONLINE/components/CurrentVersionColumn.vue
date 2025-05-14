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
    :label="t('当前使用的版本')"
    :width="240">
    <EditableBlock :placeholder="t('输入集群后自动生成')">
      <BkLoading :loading="loading">
        <P
          v-for="name in modelValue"
          :key="name">
          {{ name }}
        </P>
      </BkLoading>
    </EditableBlock>
  </EditableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getClusterVersions } from '@services/source/redisToolbox';

  interface Props {
    clusterId: number;
    nodeType: string;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string[]>();

  const { t } = useI18n();

  const { loading, run: fetchCurrentClusterVersions } = useRequest(getClusterVersions, {
    manual: true,
    onSuccess(versions) {
      modelValue.value = versions;
    },
  });

  watch(
    () => [props.clusterId, props.nodeType],
    () => {
      if (props.clusterId && props.nodeType) {
        fetchCurrentClusterVersions({
          cluster_id: props.clusterId,
          node_type: props.nodeType,
          type: 'online',
        });
      }
    },
  );
</script>
