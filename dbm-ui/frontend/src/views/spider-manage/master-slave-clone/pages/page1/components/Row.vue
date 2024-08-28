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
      <RenderMasterHost
        ref="hostRef"
        :ip="data.clusterData.ip"
        @input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0">
      <RenderText
        :data="masterInstanceList"
        :placeholder="t('输入主机后自动生成')" />
    </td>
    <td style="padding: 0">
      <RenderSlaveHost
        ref="slavaRef"
        :cloud-id="data.clusterData.cloudId"
        :ip="data.clusterData.ip"
        :placeholder="t('输入主机后自动生成')"
        @change="handleSlaveHostChange" />
    </td>
    <td style="padding: 0">
      <RenderRelatedInstance
        :ip="slaveHost"
        :placeholder="t('输入主机后自动生成')" />
    </td>
    <td style="padding: 0">
      <RenderText
        :data="data.clusterData.domain"
        :is-loading="data.isLoading"
        :placeholder="t('输入主机后自动生成')" />
    </td>
    <td style="padding: 0">
      <RenderNewInstace
        ref="instanceRef"
        :cluster-data="data.clusterData"
        :new-host-list="data.newHostList" />
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

  import type { IValue } from '@components/instance-selector/Index.vue';
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';
  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import { random } from '@utils';

  import RenderMasterHost from './RenderMasterHost.vue';
  import RenderNewInstace from './RenderNewInstace.vue';
  import RenderRelatedInstance from './RenderRelatedInstance.vue';
  import RenderSlaveHost from './RenderSlaveHost.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    clusterData: {
      ip: string;
      clusterId: number;
      domain: string;
      cloudId: number;
      cloudName: string;
      hostId: number;
    };
    masterInstanceList: NonNullable<IValue['related_instances']>;
    newHostList: string[];
  }

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    clusterData: {
      ip: '',
      clusterId: 0,
      domain: '',
      cloudId: 0,
      cloudName: '',
      hostId: 0,
    },
    masterInstanceList: [] as IDataRow['masterInstanceList'],
    newHostList: [],
  });
</script>

<script setup lang="ts">
  interface Props {
    data: IDataRow;
    removeable: boolean;
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'clone', value: IDataRow): void;
    (e: 'hostInputFinish', value: string): void;
  }

  interface HostItem {
    ip: string;
    bk_cloud_id: number;
    bk_host_id: number;
    bk_biz_id: number;
  }

  interface Exposes {
    getValue: () => Promise<{
      newInstaceList: HostItem[];
      old_master: HostItem;
    }>;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const hostRef = ref<InstanceType<typeof RenderMasterHost>>();
  const instanceRef = ref<InstanceType<typeof RenderNewInstace>>();
  const slavaRef = ref<InstanceType<typeof RenderSlaveHost>>();
  const slaveHost = ref('');

  const masterInstanceList = computed(() =>
    props.data.masterInstanceList.map((instanceItem) => instanceItem.instance).join('\n'),
  );

  const handleSlaveHostChange = (value: string) => {
    slaveHost.value = value;
  };

  const handleInputFinish = (value: string) => {
    emits('hostInputFinish', value);
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

  const getRowData = () => [hostRef.value!.getValue(), instanceRef.value!.getValue(), slavaRef.value!.getValue()];

  const handleClone = () => {
    Promise.allSettled(getRowData()).then((rowData) => {
      const [ip, newInstaceList] = rowData.map((item) => (item.status === 'fulfilled' ? item.value : item.reason));
      emits('clone', {
        rowKey: random(),
        isLoading: false,
        clusterData: {
          ip,
          clusterId: 0,
          domain: '',
          cloudId: 0,
          cloudName: '',
          hostId: 0,
        },
        masterInstanceList: [],
        newHostList: newInstaceList.map((item: { ip: string }) => item.ip),
      });
    });
  };

  defineExpose<Exposes>({
    async getValue() {
      return Promise.all(getRowData()).then((data) => {
        const [ip, newInstaceList, oldMaster] = data;
        return {
          newInstaceList,
          old_master: oldMaster,
        };
      });
    },
  });
</script>

<style lang="less" scoped>
  :deep(.render-text-box) {
    span {
      white-space: normal;
    }
  }
</style>
