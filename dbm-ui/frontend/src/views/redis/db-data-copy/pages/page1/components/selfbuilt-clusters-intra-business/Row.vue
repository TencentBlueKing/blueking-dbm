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
      <RenderSourceCluster
        ref="sourceClusterRef"
        :data="data.srcCluster"
        @input-finish="handleSrcClusterInputFinish" />
    </td>
    <td
      style="padding: 0;">
      <RenderClusterType
        ref="clusterTypeRef"
        :data="data.clusterType"
        :is-loading="data.isLoading" />
    </td>
    <td style="padding: 0;">
      <RenderAccessCode
        ref="sccessCodeRef"
        :dst-cluster="targetCluster"
        :src-cluster="data.srcCluster" />
    </td>
    <td
      style="padding: 0;">
      <RenderTargetCluster
        ref="targetClusterRef"
        :data="data.targetClusterId"
        :is-loading="data.isLoading"
        :select-list="clusterList"
        @select-change="handleInputTargetCluster" />
    </td>
    <td style="padding: 0;">
      <RenderKeyRelated
        ref="includeKeyRef"
        :data="data.includeKey"
        required />
    </td>
    <td
      style="padding: 0;">
      <RenderKeyRelated
        ref="excludeKeyRef"
        :data="data.excludeKey"
        :required="false" />
    </td>
    <OperateColumn
      :removeable="removeable"
      @add="handleAppend"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import RenderKeyRelated from '@views/redis/common/edit-field/RegexKeys.vue';
  import RenderTargetCluster, { type SelectItem } from '@views/redis/db-data-copy/pages/page1/components/RenderTargetCluster.vue';
  import type { SelfbuiltClusterToIntraInfoItem } from '@views/redis/db-data-copy/pages/page1/Index.vue';

  import { random } from '@utils';

  import RenderAccessCode from './RenderAccessCode.vue';
  import RenderClusterType, { ClusterType } from './RenderClusterType.vue';
  import RenderSourceCluster from './RenderSourceCluster.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    srcCluster: string;
    targetClusterId: number;
    clusterType: ClusterType;
    password: string;
    includeKey: string[];
    excludeKey: string[];
  }

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    srcCluster: '',
    targetClusterId: 0,
    clusterType: ClusterType.REDIS_CLUSTER,
    password: '',
    includeKey: ['*'],
    excludeKey: [],
  });

</script>
<script setup lang="ts">
  interface Props {
    data: IDataRow,
    removeable: boolean,
    clusterList: SelectItem[];
  }
  interface Emits {
    (e: 'add', params: Array<IDataRow>): void,
    (e: 'remove'): void,
    (e: 'clusterInputFinish', value: string): void
  }

  interface Exposes {
    getValue: () => Promise<SelfbuiltClusterToIntraInfoItem>
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const sourceClusterRef = ref();
  const clusterTypeRef = ref();
  const sccessCodeRef = ref();
  const targetClusterRef = ref();
  const includeKeyRef = ref();
  const excludeKeyRef = ref();
  const targetCluster = ref('');

  const handleSrcClusterInputFinish = (value: string) => {
    emits('clusterInputFinish', value);
  };

  const handleInputTargetCluster = (value: number) => {
    targetCluster.value = String(value);
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
      return await Promise.all([
        sourceClusterRef.value.getValue(),
        clusterTypeRef.value.getValue(),
        sccessCodeRef.value.getValue(),
        targetClusterRef.value.getValue(),
        includeKeyRef.value.getValue(),
        excludeKeyRef.value.getValue(),
      ]).then((data) => {
        const [
          srcCluster,
          clusterType,
          password,
          targetClusterId,
          includeKey,
          excludeKey,
        ] = data;
        return {
          src_cluster: srcCluster,
          dst_cluster: targetClusterId,
          src_cluster_type: clusterType,
          src_cluster_password: password,
          key_white_regex: includeKey.join('\n'),
          key_black_regex: excludeKey.join('\n'),
        };
      });
    },
  });

</script>
