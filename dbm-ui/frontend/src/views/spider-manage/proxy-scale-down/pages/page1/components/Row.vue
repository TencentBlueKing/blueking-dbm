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
        :check-duplicate="false"
        :data="data.cluster"
        @on-input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0;">
      <RenderNodeType
        ref="nodeTypeRef"
        :choosed="choosedNodeType"
        :counts="counts"
        :data="data.nodeType"
        :is-loading="data.isLoading"
        @change="handleChangeNodeType" />
    </td>
    <td style="padding: 0;">
      <RenderSpec
        :data="currentSepc"
        :is-loading="data.isLoading" />
    </td>
    <td
      style="padding: 0;">
      <RenderTargetNumber
        ref="tergetNumRef"
        :data="data.targetNum"
        :disabled="!data.cluster"
        :is-loading="data.isLoading"
        :max="targetMax"
        :role="currentType" />
    </td>
    <OperateColumn
      :removeable="removeable"
      @add="handleAppend"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import SpiderModel from '@services/model/spider/spider';

  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import RenderTargetCluster from '@views/spider-manage/common/edit-field/ClusterName.vue';
  import RenderSpec from '@views/spider-manage/common/edit-field/RenderSpec.vue';
  import type { SpecInfo } from '@views/spider-manage/common/spec-panel/Index.vue';

  import { random } from '@utils';

  import RenderNodeType from './RenderNodeType.vue';
  import RenderTargetNumber from './RenderTargetNumber.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    cluster: string;
    clusterId: number;
    bkCloudId: number;
    nodeType: string;
    masterCount: number;
    slaveCount: number;
    spiderMasterList: SpiderModel['spider_master'];
    spiderSlaveList: SpiderModel['spider_slave'];
    spec?: SpecInfo;
    targetNum?: string;
  }

  export interface InfoItem {
    cluster_id: number,
    spider_reduced_to_count: number,
    reduce_spider_role: string,
  }

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    cluster: '',
    clusterId: 0,
    bkCloudId: 0,
    nodeType: '',
    masterCount: 0,
    slaveCount: 0,
    spiderMasterList: [],
    spiderSlaveList: [],
  });

</script>
<script setup lang="ts">
  interface Props {
    data: IDataRow,
    removeable: boolean,
    choosedNodeType?: string[],
  }
  interface Emits {
    (e: 'add', params: Array<IDataRow>): void,
    (e: 'remove'): void,
    (e: 'clusterInputFinish', value: string): void
    (e: 'nodeTypeChoosed', label: string): void,
  }

  interface Exposes {
    getValue: () => Promise<InfoItem>
  }

  const props = withDefaults(defineProps<Props>(), {
    choosedNodeType: () => ([]),
  });

  const emits = defineEmits<Emits>();

  const nodeTypeRef = ref();
  const tergetNumRef = ref();
  const currentSepc = ref(props.data.spec);
  const targetMax = ref(1);
  const currentType = ref('');

  const counts = computed(() => ({ master: props.data.masterCount, slave: props.data.slaveCount }));


  const handleChangeNodeType = (choosedLabel: string) => {
    currentType.value = choosedLabel;
    let count = 0;
    if (choosedLabel === 'spider_master') {
      count = props.data.masterCount;
    } else {
      count = props.data.slaveCount;
    }
    targetMax.value = count;
    if (currentSepc.value) {
      currentSepc.value.count = count;
    }
    emits('nodeTypeChoosed', choosedLabel);
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
      return await Promise.all([nodeTypeRef.value.getValue(), tergetNumRef.value.getValue()]).then((data) => {
        const [nodeType, targetNum] = data;
        return {
          cluster_id: props.data.clusterId,
          ...nodeType,
          ...targetNum,
        };
      });
    },
  });

</script>
