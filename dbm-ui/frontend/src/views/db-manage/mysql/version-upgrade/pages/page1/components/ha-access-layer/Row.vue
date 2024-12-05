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
    <FixedColumn fixed="left">
      <RenderCluster
        ref="clusterRef"
        :model-value="clusterInfo"
        @id-change="handleClusterIdChange" />
    </FixedColumn>
    <td style="padding: 0">
      <RenderText
        :data="data.clusterData?.currentVersion"
        :is-loading="data.isLoading"
        :placeholder="t('输入集群后自动生成')" />
    </td>
    <td style="padding: 0">
      <RenderTargetVersion
        ref="targetVersionRef"
        :data="data" />
    </td>
    <OperateColumn
      :removeable="removeable"
      @add="handleAppend"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import { useI18n } from 'vue-i18n';

  import FixedColumn from '@components/render-table/columns/fixed-column/index.vue';
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';
  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import { random } from '@utils';

  import RenderCluster from '../RenderClusterWithRelateCluster.vue';

  import RenderTargetVersion from './RenderTargetVersion.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    clusterData?: {
      domain: string;
      clusterId: number;
      clusterType: string;
      currentVersion: string;
    };
    targetVersion?: string;
  }

  // 创建表格数据
  export const createRowData = (data?: Omit<IDataRow, 'rowKey' | 'isLoading'>): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    ...data,
  });

  interface Props {
    data: IDataRow;
    removeable: boolean;
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'clusterInputFinish', value: number): void;
  }

  interface Exposes {
    getValue: () => Promise<any>;
  }
</script>

<script setup lang="ts">
  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const clusterRef = ref<InstanceType<typeof RenderCluster>>();
  const targetVersionRef = ref<InstanceType<typeof RenderTargetVersion>>();

  const clusterInfo = computed(() => {
    if (props.data.clusterData) {
      return {
        id: props.data.clusterData.clusterId,
        domain: props.data.clusterData.domain,
      };
    }
    return undefined;
  });

  const handleClusterIdChange = (clusterId: number) => {
    emits('clusterInputFinish', clusterId);
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
    getValue() {
      return Promise.all([clusterRef.value!.getValue(true), targetVersionRef.value!.getValue()]).then((data) => {
        const [clusterData, targetVersionData] = data;
        Object.assign(targetVersionData.display_info, {
          current_version: props.data.clusterData?.currentVersion,
        });
        return {
          ...clusterData,
          ...targetVersionData,
        };
      });
    },
  });
</script>
