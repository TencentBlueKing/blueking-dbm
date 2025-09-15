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
    class="current-version-column"
    :label="t('当前版本')"
    readonly
    :width="240">
    <EditableBlock :placeholder="t('输入集群后自动生成')">
      <BkLoading :loading="versionLoading || pairVersionLoading">
        <div class="version-item">
          {{ modelValue.join(',') }}
        </div>
        <div
          v-if="slaveVersions.length > 0"
          class="version-item">
          {{ slaveVersions.join(',') }}
        </div>
      </BkLoading>
    </EditableBlock>
  </EditableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getClusterVersionsByIp } from '@services/source/redisToolbox';

  interface Props {
    clusterId: number;
    host: {
      ip: string;
      pair_machine: {
        ip: string;
      };
    };
    nodeType: string;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string[]>({
    required: true,
  });
  const slaveVersions = defineModel<string[]>('slave-versions', {
    required: true,
  });

  const { t } = useI18n();

  const { loading: versionLoading, run: fetchCurrentClusterVersions } = useRequest(getClusterVersionsByIp, {
    manual: true,
    onSuccess(version) {
      modelValue.value = version;
    },
  });

  const { loading: pairVersionLoading, run: fetchPairCurrentClusterVersions } = useRequest(getClusterVersionsByIp, {
    manual: true,
    onSuccess(version) {
      modelValue.value = version;
    },
  });

  watch(
    () => [props.host.ip, props.clusterId],
    () => {
      if (props.host.ip && props.clusterId) {
        fetchCurrentClusterVersions({
          cluster_id: props.clusterId,
          ip: props.host.ip,
          node_type: props.nodeType,
          type: 'online',
        });
      } else {
      }
    },
  );

  watch(
    () => [props.host.pair_machine.ip, props.clusterId],
    () => {
      if (props.host.pair_machine.ip && props.clusterId) {
        fetchPairCurrentClusterVersions({
          cluster_id: props.clusterId,
          ip: props.host.pair_machine.ip,
          node_type: props.nodeType,
          type: 'online',
        });
      } else {
      }
    },
  );
</script>

<style lang="less" scoped>
  .current-version-column {
    :deep(.bk-editable-block-content-wrapper) {
      padding: 0;
      margin: 0;

      .bk-editable-block-content-placeholder {
        padding: 0 10px;
      }
    }

    .version-item {
      height: 40px;
      padding: 0 10px;
      line-height: 40px;

      &:not(:first-child) {
        border-top: 1px solid #dcdee5;
      }
    }
  }
</style>
