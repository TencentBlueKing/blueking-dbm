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
        ref="clusterRef"
        :check-duplicate="false"
        :data="data.cluster"
        @on-input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0">
      <RenderNodeType
        ref="nodeTypeRef"
        :choosed="choosedNodeType"
        :counts="counts"
        :data="data.nodeType"
        :is-loading="data.isLoading"
        @change="handleChangeNodeType" />
    </td>
    <!-- <td style="padding: 0">
      <RenderSpec
        :data="currentSepc"
        :is-loading="data.isLoading" />
    </td> -->
    <td style="padding: 0">
      <RenderRoleHostSelect
        ref="hostRef"
        cluster-type="TendbClusterHost"
        :count="nodeCount"
        :data="data"
        :instance-ip-list="instaceIpList"
        :is-loading="data.isLoading"
        :selected-node-list="data.selectedNodeList"
        :tab-list-config="tabListConfig"
        @num-change="handleHostNumChange"
        @type-change="handleChangeHostSelectType" />
    </td>
    <td style="padding: 0">
      <RenderTargetNumber
        ref="tergetNumRef"
        :count="nodeCount"
        :data="localTargerNum"
        :disabled="!data.cluster || currentHostSelectType === HostSelectType.MANUAL"
        :is-loading="data.isLoading"
        :role="currentType" />
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

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import { getTendbclusterMachineList } from '@services/source/tendbcluster';

  import { ClusterTypes } from '@common/const';

  import type { IValue, PanelListType } from '@components/instance-selector/Index.vue';
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';
  import RenderRoleHostSelect, { HostSelectType } from '@components/render-table/columns/role-host-select/Index.vue';

  import RenderTargetCluster from '@views/db-manage/tendb-cluster/common/edit-field/ClusterName.vue';
  // import RenderSpec from '@views/db-manage/tendb-cluster/common/edit-field/RenderSpec.vue';
  import type { SpecInfo } from '@views/db-manage/tendb-cluster/common/spec-panel/Index.vue';

  import { random } from '@utils';

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
    spiderMasterList: TendbClusterModel['spider_master'];
    spiderSlaveList: TendbClusterModel['spider_slave'];
    spec?: SpecInfo;
    hostSelectType?: string;
    selectedNodeList?: IValue[];
    targetNum?: string;
  }

  export interface InfoItem {
    cluster_id: number;
    spider_reduced_to_count?: number | string;
    spider_reduced_hosts?: {
      ip: string;
      bk_host_id: number;
      bk_cloud_id: number;
      bk_biz_id: number;
    }[];
    reduce_spider_role: string;
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

  const { t } = useI18n();

  const clusterRef = ref<InstanceType<typeof RenderTargetCluster>>();
  const nodeTypeRef = ref<InstanceType<typeof RenderNodeType>>();
  const hostRef = ref<InstanceType<typeof RenderRoleHostSelect>>();
  const tergetNumRef = ref<InstanceType<typeof RenderTargetNumber>>();
  const currentSepc = ref(props.data.spec);
  const nodeCount = ref(1);
  const currentType = ref('');
  const currentHostSelectType = ref('');
  const localTargerNum = ref('');
  const instaceIpList = shallowRef<string[]>([]);

  const counts = computed(() => ({ master: props.data.masterCount, slave: props.data.slaveCount }));

  const tabListConfig = computed(() => {
    const isMater = props.data?.nodeType === NodeType.MASTER;
    return {
      TendbClusterHost: [
        {
          name: t('主机选择'),
          topoConfig: {
            filterClusterId: props.data!.clusterId,
            countFunc: (clusterItem: TendbClusterModel) => {
              const hostList = isMater ? clusterItem.spider_master : clusterItem.spider_slave;
              const ipList = hostList.map((hostItem) => hostItem.ip);
              return new Set(ipList).size;
            },
          },
          tableConfig: {
            getTableList: (params: ServiceReturnType<typeof getTendbclusterMachineList>) =>
              getTendbclusterMachineList({
                ...params,
                spider_role: isMater ? 'spider_master' : 'spider_slave',
              }),
            firsrColumn: {
              label: isMater ? t('Master 主机') : t('Slave 主机'),
              field: 'ip',
              role: '',
            },
          },
        },
        {
          tableConfig: {
            getTableList: (params: ServiceReturnType<typeof getTendbclusterMachineList>) =>
              getTendbclusterMachineList({
                ...params,
                spider_role: isMater ? 'spider_master' : 'spider_slave',
              }),
            firsrColumn: {
              label: isMater ? t('Master 主机') : t('Slave 主机'),
              field: 'ip',
              role: '',
            },
          },
        },
      ],
    } as unknown as Record<ClusterTypes, PanelListType>;
  });

  watch(
    () => props.data.targetNum,
    () => {
      localTargerNum.value = props.data.targetNum ?? '';
    },
    {
      immediate: true,
    },
  );

  const handleChangeNodeType = (choosedLabel: string) => {
    currentType.value = choosedLabel;
    let count = 0;
    let ipList: string[] = [];
    if (choosedLabel === 'spider_master') {
      count = props.data.masterCount;
      ipList = props.data.spiderMasterList.map((masterItem) => masterItem.ip);
    } else {
      count = props.data.slaveCount;
      ipList = props.data.spiderSlaveList.map((slaveItem) => slaveItem.ip);
    }
    nodeCount.value = count;
    instaceIpList.value = ipList;
    if (currentSepc.value) {
      currentSepc.value.count = count;
    }
    emits('nodeTypeChoosed', choosedLabel);

    // localTargerNum.value = '';
    hostRef.value?.resetValue();
  };

  const handleChangeHostSelectType = (value: string) => {
    currentHostSelectType.value = value;
  };

  const handleHostNumChange = (value: number) => {
    localTargerNum.value = String(value);
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

  const handleClone = () => {
    Promise.allSettled([
      clusterRef.value!.getValue(),
      nodeTypeRef.value!.getValue(),
      hostRef.value!.getValue('spider_reduced_hosts'),
      tergetNumRef.value!.getValue(),
    ]).then((rowData) => {
      const rowInfo = rowData.map((item) => (item.status === 'fulfilled' ? item.value : item.reason));
      const cloneData = {
        rowKey: random(),
        isLoading: false,
        cluster: '',
        clusterId: 0,
        bkCloudId: 0,
        nodeType: rowInfo[1].reduce_spider_role,
        masterCount: 0,
        slaveCount: 0,
        spiderMasterList: [],
        spiderSlaveList: [],
        targetNum: String(nodeCount.value - Number(rowInfo[3].spider_reduced_to_count)),
      };
      if (rowInfo[2]) {
        Object.assign(cloneData, {
          hostSelectType: HostSelectType.MANUAL,
          selectedNodeList: rowInfo[2].spider_reduced_hosts,
        });
      }
      emits('clone', cloneData);
    });
  };

  defineExpose<Exposes>({
    async getValue() {
      await clusterRef.value!.getValue();
      return Promise.all([
        nodeTypeRef.value!.getValue(),
        hostRef.value!.getValue('spider_reduced_hosts'),
        tergetNumRef.value!.getValue(),
      ]).then((data) => {
        const [nodeType, hostData, targetNum] = data;
        const info = {
          cluster_id: props.data.clusterId,
          ...nodeType,
        };

        if (hostData) {
          return Object.assign(info, { ...hostData });
        }
        return Object.assign(info, { ...targetNum });
      });
    },
  });
</script>
