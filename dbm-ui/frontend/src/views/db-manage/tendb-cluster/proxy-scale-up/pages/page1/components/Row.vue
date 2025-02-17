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
      <RenderTargetCluster
        :data="data.cluster"
        @on-input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0">
      <RenderNodeType
        ref="nodeTypeRef"
        :choosed="choosedNodeType"
        :counts="counts"
        :is-loading="data.isLoading"
        @change="handleChangeNodeType" />
    </td>
    <td style="padding: 0">
      <RenderSpec
        ref="specRef"
        :cloud-id="data.bkCloudId"
        :cluster-type="data.clusterType"
        :current-spec-ids="currentSpecIds"
        :data="data.specId" />
    </td>
    <td style="padding: 0">
      <RenderHostType
        ref="hostTypeRef"
        @change="handleHostTypeChange"
        @ip-list-change="handleIpListChange" />
    </td>
    <td style="padding: 0">
      <RenderTargetNumber
        ref="numRef"
        :data="data.targetNum"
        :disabled="!data.cluster || hostType === 'manual'"
        :is-loading="data.isLoading" />
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
  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';

  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import RenderTargetCluster from '@views/db-manage/tendb-cluster/common/edit-field/ClusterName.vue';
  import RenderSpec from '@views/db-manage/tendb-cluster/common/spec-panel-select/Index.vue';

  import { random } from '@utils';

  import RenderHostType from './RenderHostType.vue';
  import RenderNodeType, { NodeType } from './RenderNodeType.vue';
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
    mntCount: number; // 校验 spider_master + spider _mnt <=37
    spiderMasterList: TendbClusterModel['spider_master'];
    spiderSlaveList: TendbClusterModel['spider_slave'];
    // spec?: SpecInfo;
    specId?: number;
    targetNum?: string;
    clusterType?: string;
  }

  export interface InfoItem {
    cluster_id: number;
    add_spider_role: string;
    resource_spec: {
      spider_ip_list: {
        count: number;
        spec_id: number;
      };
    };
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
    mntCount: 0,
    spiderMasterList: [],
    spiderSlaveList: [],
  });
</script>
<script setup lang="ts">
  interface Props {
    data: IDataRow;
    removeable: boolean;
    choosedNodeType?: string[];
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'clone', value: IDataRow): void;
    (e: 'clusterInputFinish', value: string): void;
    (e: 'nodeTypeChoosed', label: string): void;
  }

  interface Exposes {
    getValue: () => Promise<InfoItem>;
  }

  const props = withDefaults(defineProps<Props>(), {
    choosedNodeType: () => [],
  });

  const emits = defineEmits<Emits>();

  const nodeTypeRef = ref<InstanceType<typeof RenderNodeType>>();
  const numRef = ref<InstanceType<typeof RenderTargetNumber>>();
  const hostTypeRef = ref<InstanceType<typeof RenderHostType>>();
  const specRef = ref<InstanceType<typeof RenderSpec>>();
  const hostType = ref('auto');
  const currentSpecIds = shallowRef<number[]>(
    props.data.spiderMasterList.map((masterItem) => masterItem.spec_config.id),
  );

  const counts = computed(() => ({ master: props.data.masterCount, slave: props.data.slaveCount }));
  // const targetMax = computed(() => 37 - props.data.mntCount);

  const handleChangeNodeType = (choosedLabel: string) => {
    emits('nodeTypeChoosed', choosedLabel);

    const { spiderMasterList, spiderSlaveList } = props.data;
    const nodeList = choosedLabel === NodeType.MASTER ? spiderMasterList : spiderMasterList;
    currentSpecIds.value = nodeList.map((nodeItem) => nodeItem.spec_config.id);
  };

  const handleIpListChange = (ipList: string[]) => {
    console.log('iplist>>>', ipList);
  };

  const handleHostTypeChange = (type: string) => {
    hostType.value = type;
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

  const getRowData = () => [nodeTypeRef.value!.getValue(), numRef.value!.getValue(), specRef.value!.getValue()];

  const handleClone = () => {
    Promise.allSettled(getRowData()).then((rowData) => {
      const [nodeType, targetNum, specInfo] = rowData.map((item) =>
        item.status === 'fulfilled' ? item.value : item.reason,
      );
      emits('clone', {
        ...createRowData(),
        cluster: props.data.cluster,
        nodeType: nodeType.reduce_spider_role,
        targetNum: targetNum.count ? targetNum.count : '',
        specId: specInfo.spec_id,
      });
    });
  };

  defineExpose<Exposes>({
    async getValue() {
      return await Promise.all(getRowData()).then((data) => {
        const [nodetype, targetNum, specInfo] = data;
        return {
          cluster_id: props.data.clusterId,
          ...nodetype,
          resource_spec: {
            spider_ip_list: {
              ...targetNum,
              ...specInfo,
            },
          },
        };
      });
    },
  });
</script>
