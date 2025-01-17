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
  <EditableTable
    ref="table"
    class="mb-20"
    :model="tableData">
    <EditableRow
      v-for="(item, index) in tableData"
      :key="index">
      <HostColumnGroup
        v-model="item.originProxy"
        :selected="selected"
        @batch-edit="handleBatchEdit" />
      <SingleHostColumn
        v-model="item.targetProxy"
        field="targetProxy.ip"
        :label="t('新Proxy主机')" />
      <OperationColumn
        v-model:table-data="tableData"
        :create-row-method="createTableRow" />
    </EditableRow>
  </EditableTable>
</template>
<script lang="ts" setup>
  import { useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import SingleHostColumn from '@views/db-manage/common/toolbox-field/column/single-host-column/Index.vue';

  import { ProxyReplaceTypes } from '../types';

  import HostColumnGroup, { type SelectorItem } from './HostColumnGroup.vue';

  interface RowData {
    originProxy: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
      port: number;
      cluster_ids: number[];
      related_instances: string[];
      related_clusters: string[];
    };
    targetProxy: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    };
  }

  interface Props {
    data: RowData[];
  }

  interface Exposes {
    getValue: () => Promise<
      {
        cluster_ids: number[];
        origin_proxy: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
          port?: number;
          instance_address?: string;
        };
        target_proxy: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        };
        display_info: {
          type: ProxyReplaceTypes;
          related_clusters: string[];
        };
      }[]
    >;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    originProxy: data.originProxy || {
      bk_cloud_id: 0,
      bk_host_id: 0,
      ip: '',
      port: 0,
      cluster_ids: [],
      related_instances: [],
      related_clusters: [],
    },
    targetProxy: data.targetProxy || {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      bk_cloud_id: 0,
      bk_host_id: 0,
      ip: '',
    },
  });

  const tableData = ref<RowData[]>([createTableRow()]);

  const selected = computed(() =>
    tableData.value
      .filter((item) => item.originProxy.bk_host_id)
      .map((item) => ({
        ip: item.originProxy.ip,
      })),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  watch(
    () => props.data,
    () => {
      if (props.data.length) {
        tableData.value = [...props.data];
      } else {
        tableData.value = [createTableRow()];
      }
    },
  );

  const handleBatchEdit = (list: SelectorItem[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.ip]) {
        const clusterIds: number[] = [];
        const relatedClusters: string[] = [];
        const relatedInstances: string[] = [];
        const adminPort = item.related_instances[0].admin_port;
        item.related_clusters.forEach((item) => {
          clusterIds.push(item.id);
          relatedClusters.push(item.immute_domain);
        });
        item.related_instances.forEach((item) => {
          relatedInstances.push(item.instance);
        });
        acc.push(
          createTableRow({
            originProxy: {
              bk_cloud_id: item.bk_cloud_id,
              bk_host_id: item.bk_host_id,
              ip: item.ip,
              port: adminPort,
              cluster_ids: clusterIds,
              related_instances: relatedInstances,
              related_clusters: relatedClusters,
            },
          }),
        );
      }
      return acc;
    }, []);
    tableData.value = [...(selected.value.length ? tableData.value : []), ...dataList];
  };

  defineExpose<Exposes>({
    async getValue() {
      const validateResult = await tableRef.value?.validate();
      if (!validateResult) {
        return [];
      }

      return tableData.value.map(({ originProxy, targetProxy }) => ({
        cluster_ids: originProxy.cluster_ids,
        origin_proxy: {
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          bk_cloud_id: originProxy.bk_cloud_id,
          bk_host_id: originProxy.bk_host_id,
          ip: originProxy.ip,
          port: originProxy.port,
        },
        target_proxy: {
          bk_biz_id: targetProxy.bk_biz_id,
          bk_cloud_id: targetProxy.bk_cloud_id,
          bk_host_id: targetProxy.bk_host_id,
          ip: targetProxy.ip,
        },
        display_info: {
          type: ProxyReplaceTypes.HOST_REPLACE,
          related_instances: originProxy.related_instances,
          related_clusters: originProxy.related_clusters,
        },
      }));
    },
  });
</script>
