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
      <RenderHost
        ref="hostRef"
        :data="data.ip"
        :inputed="inputedIps"
        @on-input-finish="handleInputFinish" />
    </td>
    <td
      style="padding: 0;">
      <RenderText
        ref="clusterRef"
        :data="data.cluster"
        :is-loading="data.isLoading"
        :placeholder="$t('输入主库后自动生成')"
        :rules="rules" />
    </td>
    <td style="padding: 0;">
      <RenderMasterInstance
        ref="instanceRef"
        :data="data.masters"
        :is-loading="data.isLoading" />
    </td>

    <td style="padding: 0;">
      <RenderText
        ref="slaveRef"
        :data="data.slave"
        :is-loading="data.isLoading"
        :placeholder="$t('输入主库后自动生成')"
        :rules="rules" />
    </td>
    <td style="padding: 0;">
      <RenderSwitchMode
        ref="switchModeRef"
        :data="data.switchMode"
        :is-loading="data.isLoading" />
    </td>
    <OperateColumn
      :removeable="removeable"
      @add="handleAppend"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import { useI18n } from 'vue-i18n';

  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';
  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import RenderHost from '@views/redis/common/edit-field/HostName.vue';

  import { random } from '@utils';

  import RenderMasterInstance from './RenderMasterInstance.vue';
  import RenderSwitchMode, { OnlineSwitchType } from './RenderSwitchMode.vue';

  export interface IDataRow {
    rowKey: string;
    isLoading: boolean;
    ip: string,
    clusterId: number;
    slave: string;
    switchMode?: string;
    cluster?: string;
    masters?:string[];
  }

  export interface InfoItem {
    cluster_id: number,
    online_switch_type: OnlineSwitchType,
    pairs: {
      redis_master: string,
      redis_slave: string,
    }[]
  }
  // 创建表格数据
  export const createRowData = (data?: IDataRow): IDataRow => ({
    rowKey: random(),
    isLoading: false,
    ip: data?.ip ?? '',
    clusterId: 0,
    cluster: data?.cluster ?? '',
    masters: data?.masters ?? [],
    slave: data?.slave ?? '',
    switchMode: data?.switchMode ?? '',
  });

</script>
<script setup lang="ts">
  interface Props {
    data: IDataRow,
    removeable: boolean,
    inputedIps?: string[],
  }

  interface Emits {
    (e: 'add', params: Array<IDataRow>): void,
    (e: 'remove'): void,
    (e: 'onIpInputFinish', value: string): void
  }

  interface Exposes {
    getValue: () => Promise<InfoItem>
  }

  const props = withDefaults(defineProps<Props>(), {
    inputedIps: () => ([]),
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const hostRef = ref();
  const clusterRef = ref();
  const instanceRef = ref();
  const slaveRef = ref();
  const switchModeRef = ref();

  const rules = [
    {
      validator: (value: string) => Boolean(value),
      message: t('不能为空'),
    },
  ];

  const handleInputFinish = (value: string) => {
    emits('onIpInputFinish', value);
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
    getValue: async () => {
      await Promise.all([
        hostRef.value.getValue(),
        clusterRef.value.getValue(),
        instanceRef.value.getValue(),
        slaveRef.value.getValue(),
      ]);
      const switchType = await switchModeRef.value.getValue();
      return {
        cluster_id: props.data.clusterId,
        online_switch_type: switchType,
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
