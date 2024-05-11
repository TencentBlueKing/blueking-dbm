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
    <td style="padding: 0;">
      <RenderTargetCluster
        ref="clusterRef"
        :data="data.cluster"
        :inputed="inputedClusters"
        @input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0;">
      <RenderText
        :data="data.clusterType"
        :is-loading="data.isLoading"
        :placeholder="t('输入集群后自动生成')" />
    </td>
    <td style="padding: 0;">
      <RenderNodeType
        :data="data.nodeType"
        @change="handleNodeTypeChange" />
    </td>
    <td style="padding: 0;">
      <RenderCurrentVersion
        :is-loading="data.isLoading"
        :list="currentVersionList" />
    </td>
    <td style="padding: 0;">
      <RenderTargetVersion
        ref="targetVersionRef"
        :is-loading="data.isLoading"
        :list="targetVersionList" />
    </td>
    <OperateColumn
      :removeable="removeable"
      @add="handleAppend"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getClusterVersions } from '@services/source/redisToolbox';

  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';
  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import type { IListItem } from '@views/redis/common/edit/Select.vue';
  import RenderTargetCluster from '@views/redis/common/edit-field/ClusterName.vue';

  import { random } from '@utils';

  import RenderCurrentVersion from './RenderCurrentVersion.vue';
  import RenderNodeType from './RenderNodeType.vue';
  import RenderTargetVersion from './RenderTargetVersion.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    cluster: string;
    clusterId: number;
    nodeType: string;
    clusterType?: string;
    targetVersion?: string;
  }

  export  interface InfoItem {
    cluster_id: number,
    node_type: string,
    current_versions: string[],
    target_version: string,
  }

  // 创建表格数据
  export const createRowData = () => ({
    rowKey: random(),
    isLoading: false,
    cluster: '',
    clusterId: 0,
    nodeType: '',
  });

</script>
<script setup lang="ts">
  interface Props {
    data: IDataRow,
    removeable: boolean,
    inputedClusters?: string[],
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void,
    (e: 'remove'): void,
    (e: 'clusterInputFinish', value: string): void
  }

  interface Exposes {
    getValue: () => Promise<InfoItem>
  }

  const props = withDefaults(defineProps<Props>(), {
    inputedClusters: () => ([]),
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const clusterRef = ref<InstanceType<typeof RenderTargetCluster>>();
  const targetVersionRef = ref<InstanceType<typeof RenderTargetVersion>>();
  const currentVersionList = ref<string[]>([]);
  const nodeType = ref<string>('Proxy');
  const targetVersionList = ref<IListItem[]>([]);

  watch(() => [props.data.clusterId, nodeType.value] as [number, string], async ([clusterId, nodeType]) => {
    if (clusterId) {
      const versions = await getClusterVersions({
        node_type: nodeType,
        cluster_id: clusterId,
      });
      currentVersionList.value = versions;
    }
  }, {
    immediate: true,
  });

  watch(() => [
    props.data.clusterType,
    nodeType.value,
    currentVersionList.value,
  ] as [string, string, string[]], async ([
    clusterType,
    nodeType,
    versionList,
  ]) => {
    if (clusterType) {
      const versions = await getClusterVersions({
        node_type: nodeType,
        cluster_type: clusterType,
      });
      targetVersionList.value = versions.map(item => ({
        label: item,
        value: item,
        disabled: versionList.includes(item),
      }));
    }
  }, {
    immediate: true,
  });

  const handleNodeTypeChange = (value: string) => {
    nodeType.value = value;
  };

  const handleInputFinish = (value: string) => {
    emits('clusterInputFinish', value);
  };

  const handleAppend = () => {
    emits('add', [createRowData()]);
  };

  const handleRemove = () => {
    if (props.removeable) {
      return;
    }
    emits('remove');
  };

  defineExpose<Exposes>({
    async getValue() {
      await clusterRef.value!.getValue();
      return await targetVersionRef.value!.getValue().then(targetVersion => ({
        cluster_id: props.data.clusterId,
        node_type: nodeType.value,
        current_versions: currentVersionList.value,
        target_version: targetVersion,
      }));
    },
  });

</script>
