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
        @input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0">
      <RenderText
        :data="data.srcClusterTypeName"
        :is-loading="data.isLoading"
        :placeholder="t('选择集群后自动生成')" />
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
      show-clone
      @add="handleAppend"
      @clone="handleClone"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';

  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';
  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import RenderSourceCluster from '@views/db-manage/redis/common/edit-field/ClusterName.vue';
  import RenderKeyRelated from '@views/db-manage/redis/common/edit-field/RegexKeys.vue';
  import RenderTargetCluster, {
    type SelectItem,
  } from '@views/db-manage/redis/db-data-copy/pages/page1/components/RenderTargetCluster.vue';
  import type { InfoItem } from '@views/db-manage/redis/db-data-copy/pages/page1/Index.vue';

  import { random } from '@utils';

  export interface IDataRow {
    excludeKey: string[];
    includeKey: string[];
    isLoading: boolean;
    rowKey: string;
    srcCluster: string;
    srcClusterId: number;
    srcClusterTypeName: string;
    targetClusterId: number;
  }

  export type IDataRowBatchKey = keyof Pick<IDataRow, 'includeKey' | 'excludeKey'>;

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    excludeKey: [],
    includeKey: ['*'],
    isLoading: false,
    rowKey: random(),
    srcCluster: '',
    srcClusterId: 0,
    srcClusterTypeName: '',
    targetClusterId: 0,
  });
</script>
<script setup lang="ts">
  interface Props {
    clusterList: SelectItem[];
    data: IDataRow;
    inputedClusters?: string[];
    removeable: boolean;
  }
  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'clone', value: IDataRow): void;
    (e: 'clusterInputFinish', value: RedisModel): void;
  }

  interface Exposes {
    getValue: () => Promise<InfoItem>;
  }

  const props = withDefaults(defineProps<Props>(), {
    inputedClusters: () => [],
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const sourceClusterRef = ref<InstanceType<typeof RenderSourceCluster>>();
  const targetClusterRef = ref<InstanceType<typeof RenderTargetCluster>>();
  const includeKeyRef = ref<InstanceType<typeof RenderKeyRelated>>();
  const excludeKeyRef = ref<InstanceType<typeof RenderKeyRelated>>();
  const selectClusterList = ref<SelectItem[]>([]);

  watch(
    () => [props.data.srcCluster, props.clusterList],
    ([cluster]) => {
      if (cluster) {
        selectClusterList.value = props.clusterList.filter((item) => item.label !== cluster);
      }
    },
    {
      immediate: true,
    },
  );

  const handleInputFinish = (value: RedisModel) => {
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

  const getRowData = (): [number, Promise<string>, Promise<string[]>, Promise<string[]>] => [
    props.data.srcClusterId,
    targetClusterRef.value!.getValue(),
    includeKeyRef.value!.getValue(),
    excludeKeyRef.value!.getValue(),
  ];

  const handleClone = () => {
    Promise.allSettled(getRowData()).then((rowData) => {
      const [srcClusterId, targetClusterId, includeKey, excludeKey] = rowData.map((item) =>
        item.status === 'fulfilled' ? item.value : item.reason,
      );
      emits('clone', {
        ...props.data,
        excludeKey,
        includeKey,
        isLoading: false,
        rowKey: random(),
        targetClusterId,
      });
    });
  };

  defineExpose<Exposes>({
    async getValue() {
      await sourceClusterRef.value!.getValue(true);
      return await Promise.all(getRowData()).then((data) => {
        const [srcClusterId, targetClusterId, includeKey, excludeKey] = data;
        return {
          dst_cluster: targetClusterId,
          key_black_regex: excludeKey.join('\n'), // 排除key
          key_white_regex: includeKey.join('\n'), // 包含key
          src_cluster: srcClusterId,
        };
      });
    },
  });
</script>
