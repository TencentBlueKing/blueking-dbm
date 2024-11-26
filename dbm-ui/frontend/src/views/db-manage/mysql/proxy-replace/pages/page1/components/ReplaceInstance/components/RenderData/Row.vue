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
      <RenderOriginalProxyInst
        ref="originRef"
        v-model="rowData.originProxy.instance_address"
        @input-finish="handleOriginProxyInputFinish" />
    </FixedColumn>
    <td style="padding: 0">
      <RenderRelatedItems
        ref="relatedClustersRef"
        field="domain"
        :list="rowData.relatedClusters" />
    </td>
    <td style="padding: 0">
      <RenderTargetProxy
        ref="targetRef"
        v-model="rowData.targetProxy"
        :origin-proxy="rowData.originProxy" />
    </td>
    <OperateColumn
      :removeable="removeable"
      @add="handleAppend"
      @remove="handleRemove" />
  </tr>
</template>
<script lang="ts">
  import { ProxyReplaceTypes } from '@views/db-manage/mysql/proxy-replace/pages/page1/components/common/const';

  import { random } from '@utils';

  export interface IDataRow {
    rowKey: string;
    originProxy: {
      bk_biz_id: number;
      bk_cloud_id: number | null;
      bk_host_id: number;
      ip: string;
      port?: number;
      instance_address: string;
    };
    relatedClusters: {
      cluster_id: number;
      domain: string;
    }[];
    targetProxy: {
      bk_biz_id: number;
      bk_cloud_id: number | null;
      bk_host_id: number;
      ip: string;
      port?: number;
    };
  }

  interface Props {
    data: IDataRow;
    removeable: boolean;
  }

  interface Emits {
    (e: 'add', params: IDataRow[]): void;
    (e: 'remove'): void;
  }

  interface Exposes {
    getValue: () => Promise<{
      cluster_ids: number[];
      origin_proxy: IDataRow['originProxy'];
      target_proxy: IDataRow['targetProxy'];
      display_info: {
        type: string;
        related_clusters: string[];
      };
    }>;
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    originProxy:
      data.originProxy ||
      ({
        ip: '',
        bk_cloud_id: null,
        bk_host_id: 0,
        bk_biz_id: 0,
        port: 0,
        instance_address: '',
      } as IDataRow['originProxy']),
    relatedClusters: data.relatedClusters || [],
    targetProxy:
      data.targetProxy ||
      ({
        ip: '',
        bk_cloud_id: null,
        bk_host_id: 0,
        bk_biz_id: 0,
        port: 0,
      } as IDataRow['targetProxy']),
  });
</script>
<script setup lang="ts">
  import { ref } from 'vue';

  import FixedColumn from '@components/render-table/columns/fixed-column/index.vue';
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import RenderRelatedItems from '@views/db-manage/mysql/proxy-replace/pages/page1/components/common/RenderRelatedItems.vue';
  import RenderTargetProxy from '@views/db-manage/mysql/proxy-replace/pages/page1/components/common/RenderTargetProxy.vue';

  import RenderOriginalProxyInst from '../RenderOriginalProxyInst.vue';

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const originRef = ref<InstanceType<typeof RenderOriginalProxyInst>>();
  const relatedClustersRef = ref<InstanceType<typeof RenderRelatedItems>>();
  const targetRef = ref<InstanceType<typeof RenderTargetProxy>>();
  const rowData = ref<IDataRow>(createRowData());

  watch(
    () => props.data,
    () => {
      rowData.value = props.data;
    },
    {
      immediate: true,
    },
  );

  const handleOriginProxyInputFinish = (data: Omit<IDataRow, 'rowKey' | 'targetProxy'>) => {
    rowData.value = Object.assign(rowData.value, data);
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
    getValue() {
      return Promise.all([
        originRef.value!.getValue(),
        relatedClustersRef.value!.getValue(),
        targetRef.value!.getValue(),
      ]).then(([originData, relatedClustersData, targetData]) => ({
        ...originData,
        ...relatedClustersData,
        ...targetData,
        display_info: {
          type: ProxyReplaceTypes.INSTANCE_REPLACE,
          related_clusters: rowData.value.relatedClusters.map((item) => item.domain),
        },
      }));
    },
  });
</script>
