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
      <RenderHost
        ref="hostRef"
        :data="data.ip"
        :inputed="inputedIps"
        @input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0">
      <RenderCluster
        :data="data.clusters?.join(',')"
        :is-loading="data.isLoading" />
    </td>
    <td style="padding: 0">
      <RenderMasterInstance
        ref="instanceRef"
        :data="data.masters"
        :is-loading="data.isLoading" />
    </td>

    <td style="padding: 0">
      <RenderText
        ref="slaveRef"
        :data="data.slave"
        :is-loading="data.isLoading"
        :placeholder="$t('输入主库后自动生成')"
        :rules="rules" />
    </td>
    <td style="padding: 0">
      <RenderSwitchMode
        ref="switchModeRef"
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
  import type { ComponentExposed } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';
  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import RenderHost from '@views/db-manage/redis/common/edit-field/HostName.vue';
  import RenderCluster from '@views/db-manage/redis/common/edit-field/RenderCluster.vue';

  import { random } from '@utils';

  import RenderMasterInstance from './RenderMasterInstance.vue';
  import RenderSwitchMode, { OnlineSwitchType } from './RenderSwitchMode.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    ip: string;
    clusterIds: number[];
    slave: string;
    switchMode?: string;
    clusters?: string[];
    masters?: string[];
  }

  export interface InfoItem {
    cluster_ids: number[];
    online_switch_type: OnlineSwitchType;
    pairs: {
      redis_master: string;
      redis_slave: string;
    }[];
  }
  // 创建表格数据
  export const createRowData = (data?: IDataRow): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    ip: data?.ip ?? '',
    clusterIds: [],
    clusters: data?.clusters ?? [],
    masters: data?.masters ?? [],
    slave: data?.slave ?? '',
    switchMode: data?.switchMode ?? '',
  });
</script>
<script setup lang="ts">
  interface Props {
    data: IDataRow;
    removeable: boolean;
    inputedIps?: string[];
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'clone', value: IDataRow): void;
    (e: 'onIpInputFinish', ipInfo: string, clusterId: number): void;
  }

  interface Exposes {
    getValue: () => Promise<InfoItem>;
  }

  const props = withDefaults(defineProps<Props>(), {
    inputedIps: () => [],
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const hostRef = ref<InstanceType<typeof RenderHost>>();
  const instanceRef = ref<InstanceType<typeof RenderMasterInstance>>();
  const slaveRef = ref<ComponentExposed<typeof RenderText>>();
  const switchModeRef = ref<InstanceType<typeof RenderSwitchMode>>();

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('不能为空'),
    },
  ];

  const handleInputFinish = (ipInfo: string, clusterId: number) => {
    emits('onIpInputFinish', ipInfo, clusterId);
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

  const getRowData = () => [
    hostRef.value!.getValue(true),
    // clusterRef.value.getValue(),
    instanceRef.value!.getValue(),
    slaveRef.value!.getValue(),
    switchModeRef.value!.getValue(),
  ];

  const handleClone = () => {
    Promise.allSettled(getRowData()).then((rowData) => {
      const rowInfo = rowData.map((item) => (item.status === 'fulfilled' ? item.value : item.reason));
      emits('clone', {
        ...props.data,
        rowKey: random(),
        isLoading: false,
        switchMode: rowInfo[3],
      });
    });
  };

  defineExpose<Exposes>({
    getValue: async () => {
      const rowInfo = await Promise.all(getRowData());
      // const switchType = await switchModeRef.value!.getValue();
      return {
        cluster_ids: props.data.clusterIds,
        online_switch_type: rowInfo[3],
        pairs: [
          {
            redis_master: props.data.ip,
            redis_slave: props.data.slave,
          },
        ],
      };
    },
  });
</script>
