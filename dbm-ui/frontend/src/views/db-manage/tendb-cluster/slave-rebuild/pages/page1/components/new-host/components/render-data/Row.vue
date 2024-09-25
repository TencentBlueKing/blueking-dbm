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
      <RenderOldSlaveHost
        ref="oldSlaveRef"
        :ip="data.oldSlave?.ip"
        @input-finish="handleInputFinish" />
    </td>
    <td style="padding: 0">
      <RenderText
        :data="slaveInstanceList"
        :is-loading="data.isLoading"
        :placeholder="t('输入主机后自动生成')" />
    </td>
    <td style="padding: 0">
      <RenderText
        :data="data.oldSlave.domian"
        :is-loading="data.isLoading"
        :placeholder="t('输入主机后自动生成')" />
    </td>
    <td style="padding: 0">
      <RenderText
        :data="data.oldSlave.specConfig.name"
        :is-loading="data.isLoading"
        :placeholder="t('输入主机后自动生成')" />
    </td>
    <td style="padding: 0">
      <RenderNewSlaveHost
        ref="newSlaveRef"
        :cluster-data="data.oldSlave" />
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
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TendbclusterMachineModel from '@services/model/tendbcluster/tendbcluster-machine';

  import type { IValue } from '@components/instance-selector/Index.vue';
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';
  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import { random } from '@utils';

  import RenderNewSlaveHost from './RenderNewSlaveHost.vue';
  import RenderOldSlaveHost from './RenderOldSlaveHost.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    oldSlave: {
      bkCloudId: number;
      bkCloudName: string;
      bkHostId: number;
      ip: string;
      domian: string;
      clusterId: number;
      specConfig: TendbclusterMachineModel['spec_config'];
      slaveInstanceList: NonNullable<IValue['related_instances']>;
    };
  }

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    oldSlave: {
      bkCloudId: 0,
      bkCloudName: '',
      bkHostId: 0,
      ip: '',
      domian: '',
      clusterId: 0,
      specConfig: {} as IDataRow['oldSlave']['specConfig'],
      slaveInstanceList: [] as IDataRow['oldSlave']['slaveInstanceList'],
    },
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

  interface Exposes {
    getValue: () => Promise<any>;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const oldSlaveRef = ref<InstanceType<typeof RenderOldSlaveHost>>();
  const newSlaveRef = ref<InstanceType<typeof RenderNewSlaveHost>>();

  const slaveInstanceList = computed(() =>
    props.data.oldSlave.slaveInstanceList.map((instanceItem) => instanceItem.instance).join('\n'),
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

  const getRowData = () => [oldSlaveRef.value!.validate(), newSlaveRef.value!.getValue()];

  const handleClone = () => {
    Promise.allSettled(getRowData()).then((rowData) => {
      emits('clone', {
        rowKey: random(),
        isLoading: false,
        oldSlave: _.cloneDeep(props.data.oldSlave),
      });
    });
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all(getRowData()).then(([oldSlaveValue, newSlaveData]) => ({
        ...newSlaveData,
      }));
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
