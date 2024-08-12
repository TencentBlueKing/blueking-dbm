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
      <RenderSource
        ref="sourceRef"
        v-model="localSource" />
    </td>
    <td style="padding: 0">
      <RenderText
        :data="localSource?.masterDomain"
        :placeholder="t('输入源实例后自动生成')" />
    </td>
    <td style="padding: 0">
      <RenderTarget
        ref="targetRef"
        :model-value="data.target"
        :source="localSource" />
    </td>
    <OperateColumn
      :removeable="removeable"
      @add="handleAppend"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import { random } from '@utils';

  export interface IProxyData {
    cluster_id: number;
    bk_host_id: number;
    bk_cloud_id: number;
    port: number;
    ip: string;
    instance_address: string;
  }

  export interface IDataRow {
    rowKey: string;
    source?: {
      bkCloudId: number;
      clusterId: number;
      clusterType: string;
      dbModuleId: number;
      dbModuleName: string;
      instanceAddress: string;
      masterDomain: string;
    };
    target?: IProxyData;
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    source: data.source,
    target: data.target,
  });
</script>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';
  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import RenderSource from './RenderSource.vue';
  import RenderTarget from './RenderTarget.vue';

  interface Props {
    data: IDataRow;
    removeable: boolean;
  }
  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
  }

  interface Exposes {
    getValue: () => Promise<any>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const sourceRef = ref<InstanceType<typeof RenderSource>>();
  const targetRef = ref<InstanceType<typeof RenderTarget>>();

  const localSource = ref<IDataRow['source']>();

  watch(
    () => props.data,
    () => {
      if (props.data.source) {
        localSource.value = props.data.source;
      }
    },
    {
      immediate: true,
    },
  );

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
    getValue() {
      return Promise.all([sourceRef.value!.getValue(), targetRef.value!.getValue()]).then(
        ([sourceData, targetData]) => ({
          ...sourceData,
          ...targetData,
          cluster_domain: localSource.value!.masterDomain,
          bk_cloud_id: localSource.value!.bkCloudId,
        }),
      );
    },
  });
</script>
