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
    <FixedColumn fixed="left">
      <RenderSource
        ref="sourceRef"
        v-model="localSource"
        :cluster-types="[ClusterTypes.TENDBHA, ClusterTypes.TENDBSINGLE]"
        :tab-list-config="tabListConfig" />
    </FixedColumn>
    <td style="padding: 0">
      <RenderText
        :data="localSource?.master_domain"
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
      show-clone
      @add="handleAppend"
      @clone="handleClone"
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
      bk_cloud_id: number;
      cluster_id: number;
      cluster_type: string;
      db_module_id: number;
      db_module_name: string;
      instance_address: string;
      master_domain: string;
      ip: string;
      port: number;
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

  import { ClusterTypes } from '@common/const';

  import FixedColumn from '@components/render-table/columns/fixed-column/index.vue';
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';
  import RenderText from '@components/render-table/columns/text-plain/index.vue';

  import RenderSource from '@views/db-manage/mysql/common/edit-field/InstanceWithSelector.vue';

  import RenderTarget from './RenderTarget.vue';

  interface Props {
    data: IDataRow;
    removeable: boolean;
  }
  interface Emits {
    (e: 'add', params: Array<IDataRow>): void;
    (e: 'remove'): void;
    (e: 'clone', value: IDataRow): void;
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

  const tabListConfig = {
    [ClusterTypes.TENDBHA]: [
      {
        tableConfig: {
          multiple: false,
        },
      },
    ],
    [ClusterTypes.TENDBSINGLE]: [
      {
        tableConfig: {
          multiple: false,
        },
      },
    ],
  } as any;

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

  const handleClone = () => {
    Promise.allSettled([sourceRef.value!.getValue(), targetRef.value!.getValue()]).then((rowData) => {
      const rowInfo = rowData.map((item) => (item.status === 'fulfilled' ? item.value : item.reason));
      emits(
        'clone',
        createRowData({
          rowKey: random(),
          source: props.data.source,
          target: {
            cluster_id: 0,
            bk_host_id: 0,
            bk_cloud_id: 0,
            port: 0,
            ip: '',
            instance_address: rowInfo[1].target,
          },
        }),
      );
    });
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all([sourceRef.value!.getValue(), targetRef.value!.getValue()]).then(
        ([sourceData, targetData]) => ({
          source: sourceData.instance_address,
          ...targetData,
          cluster_domain: localSource.value!.master_domain,
          bk_cloud_id: localSource.value!.bk_cloud_id,
        }),
      );
    },
  });
</script>
