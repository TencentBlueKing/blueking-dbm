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
      <RenderSourceCluster
        ref="sourceClusterRef"
        :data="data.srcCluster"
        :inputed="inputedClusters"
        @on-input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0">
      <RenderTargetCluster
        ref="targetClusterRef"
        :data="data.targetClusterId"
        :is-loading="data.isLoading"
        :select-list="selectClusterList" />
    </td>
    <td style="padding: 0">
      <RenderKeyRelated
        ref="includeKeyRef"
        :data="data.includeKey"
        required />
    </td>
    <td style="padding: 0">
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

  import RenderSourceCluster from '@views/redis/common/edit-field/ClusterName.vue';
  import RenderKeyRelated from '@views/redis/common/edit-field/RegexKeys.vue';
  import RenderTargetCluster, {
    type SelectItem,
  } from '@views/redis/db-data-copy/pages/page1/components/RenderTargetCluster.vue';
  import type { InfoItem } from '@views/redis/db-data-copy/pages/page1/Index.vue';

  import { random } from '@utils';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    srcCluster: string;
    srcClusterId: number;
    targetClusterId: number;
    includeKey: string[];
    excludeKey: string[];
  }

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    srcCluster: '',
    srcClusterId: 0,
    targetClusterId: 0,
    includeKey: ['*'],
    excludeKey: [],
  });
</script>
<script setup lang="ts">
  interface Props {
    data: IDataRow;
    removeable: boolean;
    clusterList: SelectItem[];
    inputedClusters?: string[];
  }
  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'clusterInputFinish', value: string): void;
  }

  interface Exposes {
    getValue: () => Promise<InfoItem>;
  }

  const props = withDefaults(defineProps<Props>(), {
    inputedClusters: () => [],
  });

  const emits = defineEmits<Emits>();

  const sourceClusterRef = ref();
  const targetClusterRef = ref();
  const includeKeyRef = ref();
  const excludeKeyRef = ref();
  const selectClusterList = ref<SelectItem[]>([]);

  watch(
    () => props.data.srcCluster,
    (cluster) => {
      if (cluster) {
        selectClusterList.value = props.clusterList.filter((item) => item.label !== cluster);
      }
    },
    {
      immediate: true,
    },
  );

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
      await sourceClusterRef.value.getValue();
      return await Promise.all([
        props.data.srcClusterId,
        targetClusterRef.value.getValue(),
        includeKeyRef.value.getValue(),
        excludeKeyRef.value.getValue(),
      ]).then((data) => {
        const [srcClusterId, targetClusterId, includeKey, excludeKey] = data;
        return {
          src_cluster: srcClusterId,
          dst_cluster: targetClusterId,
          key_white_regex: includeKey.join('\n'), // 包含key
          key_black_regex: excludeKey.join('\n'), // 排除key
        };
      });
    },
  });
</script>
