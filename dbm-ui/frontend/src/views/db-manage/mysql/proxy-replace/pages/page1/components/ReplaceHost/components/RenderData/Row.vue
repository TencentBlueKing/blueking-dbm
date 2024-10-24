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
      <RenderOriginalProxyHost
        ref="originRef"
        :cluster-types="['TendbhaHost']"
        :model-value="data.originProxy"
        :tab-list-config="tabListConfig"
        type="ip"
        @instance-change="handleOriginProxyInputFinish" />
    </FixedColumn>
    <td style="padding: 0">
      <RenderRelatedItems
        ref="relatedInstancesRef"
        field="instance"
        :list="rowData.relatedInstances" />
    </td>
    <td style="padding: 0">
      <RenderRelatedItems
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
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      port?: number;
    };
    relatedInstances: {
      cluster_id: number;
      instance: string;
    }[];
    relatedClusters: {
      cluster_id: number;
      domain: string;
    }[];
    targetProxy: {
      bk_biz_id: number;
      bk_cloud_id: number;
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
    }>;
  }

  // 创建表格数据
  export const createRowData = (data = {} as Partial<IDataRow>) => ({
    rowKey: random(),
    originProxy:
      data.originProxy ||
      ({
        ip: '',
        bk_cloud_id: 0,
        bk_host_id: 0,
        bk_biz_id: 0,
        port: 0,
      } as IDataRow['originProxy']),
    relatedInstances: data.relatedInstances || [],
    relatedClusters: data.relatedClusters || [],
    targetProxy:
      data.targetProxy ||
      ({
        ip: '',
        bk_cloud_id: 0,
        bk_host_id: 0,
        bk_biz_id: 0,
        port: 0,
      } as IDataRow['targetProxy']),
  });
</script>
<script setup lang="ts">
  import _ from 'lodash';
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import FixedColumn from '@components/render-table/columns/fixed-column/index.vue';
  import OperateColumn from '@components/render-table/columns/operate-column/index.vue';

  import RenderOriginalProxyHost, {
    type InstanceBasicInfo,
  } from '@views/db-manage/mysql/common/edit-field/InstanceWithSelector.vue';
  import RenderRelatedItems from '@views/db-manage/mysql/proxy-replace/pages/page1/components/common/RenderRelatedItems.vue';
  import RenderTargetProxy from '@views/db-manage/mysql/proxy-replace/pages/page1/components/common/RenderTargetProxy.vue';

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const originRef = ref<InstanceType<typeof RenderOriginalProxyHost>>();
  const relatedInstancesRef = ref<InstanceType<typeof RenderRelatedItems>>();
  const targetRef = ref<InstanceType<typeof RenderTargetProxy>>();
  const rowData = ref<IDataRow>(createRowData());

  const tabListConfig = {
    TendbhaHost: [
      {
        id: 'TendbhaHost',
        name: t('目标Proxy主机'),
        tableConfig: {
          firsrColumn: {
            label: t('Proxy 主机'),
            field: 'ip',
            role: 'proxy',
          },
          multiple: false,
        },
      },
      {
        id: 'manualInput',
        name: t('手动输入'),
        tableConfig: {
          firsrColumn: {
            label: t('Proxy 主机'),
            field: 'ip',
            role: 'proxy',
          },
          multiple: false,
        },
      },
    ],
  } as any;

  watch(
    () => props.data,
    () => {
      rowData.value = props.data;
    },
    {
      immediate: true,
    },
  );

  const handleOriginProxyInputFinish = (data: InstanceBasicInfo) => {
    const originProxy = {
      ip: data.ip,
      bk_cloud_id: data.bk_cloud_id,
      bk_host_id: data.bk_host_id,
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      port: data.port,
    };
    const relatedInstances = data.related_instances!.map((item) => ({
      cluster_id: item.cluster_id,
      instance: item.instance_address,
    }));
    const relatedClusters = _.sortBy(
      data.related_clusters!.map((item) => ({
        cluster_id: item.id,
        domain: item.master_domain,
      })),
      'cluster_id',
    );
    rowData.value = Object.assign(rowData.value, {
      originProxy,
      relatedInstances,
      relatedClusters,
    });
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
        relatedInstancesRef.value!.getValue(),
        targetRef.value!.getValue(),
      ]).then(([originData, relatedInstancesData, targetData]) => ({
        origin_proxy: {
          ip: originData.ip,
          bk_cloud_id: originData.bk_cloud_id,
          bk_host_id: originData.bk_host_id,
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          port: originData.port,
        },
        ...relatedInstancesData,
        ...targetData,
        display_info: {
          type: ProxyReplaceTypes.HOST_REPLACE,
          related_instances: rowData.value.relatedInstances.map((item) => item.instance),
          related_clusters: rowData.value.relatedClusters.map((item) => item.domain),
        },
      }));
    },
  });
</script>
