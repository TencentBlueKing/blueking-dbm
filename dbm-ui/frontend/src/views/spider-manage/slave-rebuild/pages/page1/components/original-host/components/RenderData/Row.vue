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
      <RenderSlave
        ref="slaveRef"
        :instance="instance"
        @input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0">
      <RenderText
        :data="data.slave?.domain"
        :is-loading="data.isLoading"
        :placeholder="t('输入集群后自动生成')" />
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
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';
  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import { random } from '@utils';

  import RenderSlave from './RenderSlave.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    slave: {
      bkCloudId: number;
      bkHostId: number;
      ip: string;
      port: number;
      instanceAddress: string;
      clusterId: number;
      domain: string;
    };
  }

  // 创建表格数据
  export const createRowData = () => ({
    rowKey: random(),
    isLoading: false,
    slave: {
      bkCloudId: 0,
      bkHostId: 0,
      ip: '',
      port: 0,
      instanceAddress: '',
      clusterId: 0,
      domain: '',
    },
  });
</script>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

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

  interface Exposes {
    getValue: () => Promise<string>;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const slaveRef = ref<InstanceType<typeof RenderSlave>>();
  const localSlave = ref<IDataRow['slave']>();

  const instance = computed(() => {
    const { ip, port } = props.data.slave;
    if (ip && port) {
      return `${ip}:${port}`;
    }
    return '';
  });

  watch(
    () => props.data,
    () => {
      if (props.data) {
        localSlave.value = props.data.slave;
      }
    },
    {
      immediate: true,
    },
  );

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

  const handleClone = () => {
    Promise.allSettled([slaveRef.value!.getValue()]).then((rowData) => {
      const [slaveData] = rowData.map((item) => (item.status === 'fulfilled' ? item.value : item.reason));
      const [ip, port] = slaveData.split(':');
      emits('clone', {
        rowKey: random(),
        isLoading: false,
        slave: {
          bkCloudId: 0,
          bkHostId: 0,
          ip,
          port: Number(port),
          instanceAddress: '',
          clusterId: 0,
          domain: props.data.slave.domain,
        },
      });
    });
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all([slaveRef.value!.getValue()]).then(([slaveData]) => Promise.resolve(slaveData));
    },
  });
</script>
