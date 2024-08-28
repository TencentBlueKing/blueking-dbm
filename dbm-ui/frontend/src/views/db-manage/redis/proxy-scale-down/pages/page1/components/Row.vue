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
        :data="data.cluster"
        :inputed="inputedClusters"
        @input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0">
      <RenderText
        :data="data.cluster_type_name"
        :is-loading="data.isLoading"
        :placeholder="$t('选择集群后自动生成')" />
    </td>
    <td style="padding: 0">
      <RenderText
        :data="data.nodeType"
        :is-loading="data.isLoading"
        :placeholder="$t('输入集群后自动生成')" />
    </td>
    <!-- <td style="padding: 0">
      <RenderSpecList
        :data-list="proxySpecList"
        :is-loading="data.isLoading" />
    </td> -->
    <td style="padding: 0">
      <RenderRoleHostSelect
        ref="hostRef"
        :cluster-type="ClusterTypes.REDIS"
        :count="roleHostCount"
        :data="data"
        :instance-ip-list="proxyIpList"
        :is-loading="data.isLoading"
        :selected-node-list="data.selectedNodeList"
        :tab-list-config="tabListConfig"
        @num-change="handleHostNumChange"
        @type-change="handleChangeHostSelectType" />
    </td>
    <td style="padding: 0">
      <RenderTargetNumber
        ref="targetNumberRef"
        :count="roleHostCount"
        :data="localTargerNum"
        :disabled="!data.cluster || currentHostSelectType === HostSelectType.MANUAL"
        :is-loading="data.isLoading" />
    </td>
    <td style="padding: 0">
      <RenderSwitchMode
        ref="switchRef"
        :data="data.switchMode"
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
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';
  import { getRedisClusterList } from '@services/source/redis';

  import { ClusterTypes } from '@common/const';

  import type { IValue, PanelListType } from '@components/instance-selector/Index.vue';
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';
  import RenderRoleHostSelect, { HostSelectType } from '@components/render-table/columns/role-host-select/Index.vue';
  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import RenderTargetCluster from '@views/db-manage/redis/common/edit-field/ClusterName.vue';

  import { random } from '@utils';

  // import RenderSpecList from './RenderSpecList.vue';
  import RenderSwitchMode, { OnlineSwitchType } from './RenderSwitchMode.vue';
  import RenderTargetNumber from './RenderTargetNumber.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    cluster: string;
    clusterId: number;
    bkCloudId: number;
    nodeType: string;
    cluster_type_name: string;
    proxyList: RedisModel['proxy'];
    switchMode?: string;
    hostSelectType?: string;
    selectedNodeList?: IValue[];
    targetNum?: string;
  }

  export interface InfoItem {
    cluster_id: number;
    bk_cloud_id: number;
    target_proxy_count?: number | string;
    spider_reduced_hosts?: {
      ip: string;
      bk_host_id: number;
      bk_cloud_id: number;
      bk_biz_id: number;
    }[];
    online_switch_type: OnlineSwitchType;
  }

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    cluster: '',
    clusterId: 0,
    bkCloudId: 0,
    nodeType: '',
    cluster_type_name: '',
    proxyList: [],
  });
</script>
<script setup lang="ts">
  interface Props {
    data: IDataRow;
    removeable: boolean;
    inputedClusters?: string[];
  }
  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'clone', value: IDataRow): void;
    (e: 'clusterInputFinish', value: RedisModel): void;
    (e: 'targetNumChange', value: number): void;
  }

  interface Exposes {
    getValue: () => Promise<InfoItem>;
  }

  const props = withDefaults(defineProps<Props>(), {
    inputedClusters: () => [],
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const clusterRef = ref<InstanceType<typeof RenderTargetCluster>>();
  const switchRef = ref<InstanceType<typeof RenderSwitchMode>>();
  const targetNumberRef = ref<InstanceType<typeof RenderTargetNumber>>();
  const hostRef = ref<InstanceType<typeof RenderRoleHostSelect>>();
  const currentHostSelectType = ref('');
  const localTargerNum = ref('');

  const tabListConfig = computed(
    () =>
      ({
        [ClusterTypes.REDIS]: [
          {
            name: t('主机选择'),
            topoConfig: {
              filterClusterId: props.data!.clusterId,
              getTopoList: (params: ServiceParameters<typeof getRedisClusterList>) =>
                getRedisClusterList({
                  ...params,
                  domain: props.data.cluster,
                }),
            },
            tableConfig: {
              firsrColumn: {
                label: t('Proxy 主机'),
                field: 'ip',
                role: 'proxy',
              },
            },
          },
          {
            tableConfig: {
              firsrColumn: {
                label: t('Proxy 主机'),
                field: 'ip',
                role: 'proxy',
              },
            },
          },
        ],
      }) as unknown as Record<ClusterTypes, PanelListType>,
  );

  const proxyIpList = computed(() => props.data.proxyList.map((proxyItem) => proxyItem.ip));
  // const proxySpecList = computed(() => props.data.proxyList.map((proxyItem) => proxyItem.spec_config));
  const roleHostCount = computed(() => props.data.proxyList.length);

  watch(
    () => props.data.targetNum,
    () => {
      localTargerNum.value = props.data.targetNum ?? '';
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

  const handleChangeHostSelectType = (value: string) => {
    currentHostSelectType.value = value;
  };

  const handleHostNumChange = (value: number) => {
    localTargerNum.value = String(value);
  };

  const handleClone = () => {
    Promise.allSettled([
      clusterRef.value!.getValue(),
      targetNumberRef.value!.getValue(),
      hostRef.value!.getValue('proxy_reduced_hosts'),
      switchRef.value!.getValue(),
    ]).then((rowData) => {
      const rowInfo = rowData.map((item) => (item.status === 'fulfilled' ? item.value : item.reason));
      const cloneData = {
        ...props.data,
        rowKey: random(),
        isLoading: false,
        targetNum: String(roleHostCount.value - Number(rowInfo[1])),
        switchMode: rowInfo[3],
      };
      if (rowInfo[2]) {
        Object.assign(cloneData, {
          hostSelectType: HostSelectType.MANUAL,
          selectedNodeList: rowInfo[2].proxy_reduced_hosts,
        });
      }
      emits('clone', cloneData);
    });
  };

  defineExpose<Exposes>({
    async getValue() {
      await clusterRef.value!.getValue(true);
      return await Promise.all([
        targetNumberRef.value!.getValue(),
        hostRef.value!.getValue('proxy_reduced_hosts'),
        switchRef.value!.getValue(),
      ]).then((data) => {
        const [targetNum, hostData, switchMode] = data;
        const info = {
          cluster_id: props.data.clusterId,
          bk_cloud_id: props.data.bkCloudId,
          online_switch_type: switchMode as OnlineSwitchType,
        };

        if (hostData) {
          return Object.assign(info, { ...hostData });
        }
        return Object.assign(info, { target_proxy_count: targetNum });
      });
    },
  });
</script>
