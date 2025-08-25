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
    :label="t('当前版本')"
    :width="240">
    <EditableBlock :placeholder="t('输入集群后自动生成')">
      <BkLoading :loading="loading">
        <div
          v-for="name in modelValue"
          :key="name">
          {{ name }}
        </div>
      </BkLoading>
    </EditableBlock>
  </EditableColumn>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getClusterVersions } from '@services/source/redisToolbox';

  interface Props {
    clusterIds: number[];
    nodeType: string;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string[]>();

  const { t } = useI18n();

  const { loading, run: fetchCurrentClusterVersions } = useRequest(getClusterVersions, {
    manual: true,
    onSuccess(versions) {
      modelValue.value = _.uniq(
        Object.values(versions).flatMap((item) => {
          return item;
        }),
      );
    },
  });

  watch(
    () => props.clusterIds,
    (newClusterIds, oldClusterIds) => {
      if (_.isEqual(newClusterIds, oldClusterIds)) {
        return;
      }
      if (props.clusterIds.length > 0 && props.nodeType) {
        fetchCurrentClusterVersions({
          cluster_ids: props.clusterIds.join(','),
          node_type: props.nodeType,
          type: 'online',
        });
      }
    },
    {
      immediate: true,
    },
  );
</script>
