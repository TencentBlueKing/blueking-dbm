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
      <RenderSourceCluster
        :id="data.srcCluster"
        ref="sourceClusterRef"
        :data="data.srcCluster"
        @cluster-input-finish="handleClusterInputFinish" />
    </td>
    <td
      style="padding: 0;">
      <RenderInstanceId
        ref="instanceIdRef"
        :data="data.dumperId" />
    </td>
    <td
      v-if="index === 0"
      :rowspan="rowSpan"
      style="padding: 0">
      <RenderReceiverType
        :key="rowSpan"
        :data="receiverType"
        @type-change="handleReceiverTypeChange" />
    </td>
    <td
      v-if="receiverType !== 'L5_AGENT'"
      style="padding: 0;">
      <RenderReceiver
        ref="receiverRef"
        :data="data.receiver" />
    </td>
    <template v-if="receiverType === 'KAFKA'">
      <td
        style="padding: 0;">
        <RenderAccount
          ref="accountRef"
          :data="data.account" />
      </td>
      <td
        style="padding: 0;">
        <RenderPassword
          ref="passwordRef"
          :data="data.password" />
      </td>
    </template>

    <template v-if="receiverType === 'L5_AGENT'">
      <td
        style="padding: 0;">
        <RenderL5ModCmdId
          ref="modIdRef"
          :data="data.l5ModId" />
      </td>
      <td
        style="padding: 0;">
        <RenderL5ModCmdId
          ref="cmdIdRef"
          :data="data.l5ModId" />
      </td>
    </template>
    <FixedColumn>
      <BkButton
        class="delete-column"
        :disabled="rowSpan === 1"
        text
        theme="primary"
        @click="handleDelete">
        {{ $t('删除') }}
      </BkButton>
    </FixedColumn>
  </tr>
</template>
<script lang="ts">
  import FixedColumn from '@components/render-table/columns/fixed-column/index.vue';

  import { random } from '@utils';

  import RenderAccount from './RenderAccount.vue';
  import RenderInstanceId from './RenderInstanceId.vue';
  import RenderL5ModCmdId from './RenderL5Id.vue';
  import RenderPassword from './RenderPassword.vue';
  import RenderReceiver from './RenderReceiver.vue';
  import RenderReceiverType from './RenderReceiverType.vue';
  import RenderSourceCluster from './RenderSourceCluster.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    srcCluster: {
      clusterName: string,
      clusterId: number,
      moduleId: number,
    };
    dumperId: string;
    receiver: string;
    receiverType: string;
    account: string;
    password: string;
    l5ModId: number;
    l5CmdId: number;
  }

  // 创建表格数据
  export const createRowData = (): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    srcCluster: {
      clusterName: '',
      clusterId: 0,
      moduleId: 0,
    },
    dumperId: '',
    receiver: '',
    receiverType: 'KAFKA',
    account: '',
    password: '',
    l5ModId: 0,
    l5CmdId: 0,
  });

</script>
<script setup lang="ts">
  interface Props {
    data: IDataRow,
    rowSpan: number,
    index: number,
    type: string,
  }

  interface Emits {
    (e: 'remove'): void,
    (e: 'type-change', value: string): void
    (e: 'cluster-input-finish', value: IDataRow['srcCluster']): void
  }

  interface Exposes {
    getValue: () => Promise<any>
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const sourceClusterRef = ref<InstanceType<typeof RenderSourceCluster>>();
  const instanceIdRef = ref<InstanceType<typeof RenderInstanceId>>();
  const receiverRef = ref<InstanceType<typeof RenderReceiver>>();
  const accountRef = ref<InstanceType<typeof RenderAccount>>();
  const passwordRef = ref<InstanceType<typeof RenderPassword>>();
  const modIdRef = ref<InstanceType<typeof RenderL5ModCmdId>>();
  const cmdIdRef = ref<InstanceType<typeof RenderL5ModCmdId>>();
  const receiverType = ref('KAFKA');

  watch(() => props.type, (type) => {
    receiverType.value = type;
  }, {
    immediate: true,
  });

  const handleReceiverTypeChange = (type: string) => {
    receiverType.value = type;
    emits('type-change', type);
  };

  const handleDelete = () => {
    emits('remove');
  };

  const handleClusterInputFinish = (value: IDataRow['srcCluster']) => {
    emits('cluster-input-finish', value);
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all([
        sourceClusterRef.value!.getValue(),
        instanceIdRef.value?.getValue(),
        receiverRef.value?.getValue(),
        accountRef.value?.getValue(),
        passwordRef.value?.getValue(),
        modIdRef.value?.getValue(),
        cmdIdRef.value?.getValue(),
      ]).then((data) => {
        const [
          srcCluster,
          id,
          target,
          user,
          pwd,
          modid,
          cmdid,
        ] = data;
        const targetArr = target ? target.split(':') : ['', 0];
        const rowObj =  {
          ...srcCluster,
          dumper_id: id,
          protocol_type: receiverType.value,
          target_address: targetArr[0] as string | undefined, // protocol_type为L5_AGENT要去除
          target_port: Number(targetArr[1]) as number | undefined, // protocol_type为L5_AGENT要去除
          l5_modid: modid, // protocol_type为L5_AGENT填入用户值
          l5_cmdid: cmdid, // protocol_type为L5_AGENT填入用户值
          kafka_user: user, // protocol_type为KAFKA填入用户值
          kafka_pwd: pwd,  // protocol_type为KAFKA填入用户值
        };
        if (receiverType.value === 'KAFKA') {
          delete rowObj.l5_modid;
          delete rowObj.l5_cmdid;
        } else if (receiverType.value === 'L5_AGENT') {
          delete rowObj.target_address;
          delete rowObj.target_port;
          delete rowObj.kafka_user;
          delete rowObj.kafka_pwd;
        } else {
          delete rowObj.l5_modid;
          delete rowObj.l5_cmdid;
          delete rowObj.kafka_user;
          delete rowObj.kafka_pwd;
        }
        return rowObj;
      });
    },
  });

</script>
<style lang="less" scoped>
.delete-column {
  width: 100%;
}
</style>

