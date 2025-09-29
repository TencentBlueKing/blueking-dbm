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
  <BatchInput
    :config="batchInputConfig"
    @change="handleBatchInput" />
  <EditableTable
    :key="tableKey"
    ref="table"
    class="mt-16 mb-20"
    :model="tableData">
    <EditableRow
      v-for="(item, index) in tableData"
      :key="index">
      <HostColumnGroup
        v-model="item.originProxy"
        :handle-row-merge="handleRowMerge"
        :rowspan="item.rowspan"
        :selected="selected"
        @batch-edit="handleBatchEdit" />
      <SpecColumn
        v-model="item.specId"
        :cluster-type="DBTypes.MYSQL"
        :current-spec-id-list="item.originProxy.spec_id_list"
        :machine-type="MachineTypes.MYSQL_PROXY"
        required
        :rowspan="item.rowspan"
        :show-tag="false"
        @batch-edit="handleBatchEditColumn" />
      <ResourceTagColumn
        v-model="item.labels"
        :rowspan="item.rowspan"
        @batch-edit="handleBatchEditColumn" />
      <AvailableResourceColumn
        :params="{
          city: item.originProxy.bk_idc_city_name,
          subzones: item.originProxy.bk_sub_zone,
          for_bizs: [currentBizId, 0],
          resource_types: [DBTypes.MYSQL, 'PUBLIC'],
          spec_id: item.specId,
          labels: item.labels.map((item) => item.id).join(','),
        }"
        :rowspan="item.rowspan" />
      <OperationColumn
        v-model:table-data="tableData"
        :create-row-method="createTableRow"
        :handle-row-merge="handleRowMerge" />
    </EditableRow>
  </EditableTable>
</template>
<script lang="ts" setup>
  import { useTemplateRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import type { Mysql } from '@services/model/ticket/ticket';

  import { DBTypes, MachineTypes } from '@common/const';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';

  import { random } from '@utils';

  import HostColumnGroup, { type SelectorItem } from './components/HostColumnGroup.vue';

  interface RowData {
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
    originProxy: ComponentProps<typeof HostColumnGroup>['modelValue'];
    rowspan: number;
    specId: number;
  }

  interface Props {
    ticketDetails?: Mysql.ResourcePool.ProxySwitch;
  }

  interface Exposes {
    getValue: () => Promise<
      {
        cluster_ids: number[];
        old_nodes: {
          proxy: {
            bk_biz_id: number;
            bk_cloud_id: number;
            bk_host_id: number;
            ip: string;
            port: number;
          }[];
        };
        origin_proxy_ip: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        };
        resource_spec: {
          target_proxy: {
            count: number;
            label_names: string[]; // 标签名称列表，单据详情回显用
            labels: string[]; // 标签id列表
            spec_id: number;
          };
        };
      }[]
    >;
    reset(): void;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
    labels: (data.labels || []) as RowData['labels'],
    originProxy: Object.assign(
      {
        bk_cloud_id: 0,
        bk_host_id: 0,
        bk_idc_city_name: '',
        bk_sub_zone: '',
        ip: '',
        related_clusters: [],
        related_instances: [],
        role: '',
        spec_config: {},
        spec_id_list: [],
      } as unknown as RowData['originProxy'],
      data.originProxy,
    ),
    rowspan: data.rowspan || 1,
    specId: data.specId || 0,
  });

  const tableData = ref<RowData[]>([createTableRow()]);
  const tableKey = ref(random());

  const batchInputConfig = [
    {
      case: '192.168.10.2',
      key: 'proxy_ip',
      label: t('目标Proxy主机'),
    },
    {
      case: '2核_4G_50G',
      key: 'spec_name',
      label: t('目标规格'),
    },
    {
      case: '标签1,标签2',
      key: 'labels',
      label: t('资源标签'),
    },
  ];

  const selected = computed(() =>
    tableData.value.filter((item) => item.originProxy.bk_host_id).map((item) => item.originProxy),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));
  // 具备完全相同的集群id列的行数组map
  let sameClusterIdsRowsMap: Record<string, RowData[]> = {};

  // 行合并
  const handleRowMerge = () => {
    sameClusterIdsRowsMap = {};
    tableData.value.forEach((item) => {
      Object.assign(item, { rowspan: 1 });
      const ids = (item.originProxy.related_clusters || []).map((item) => item.id).join(',');
      if (!sameClusterIdsRowsMap[ids]) {
        sameClusterIdsRowsMap[ids] = [item];
      } else {
        sameClusterIdsRowsMap[ids].push(item);
      }
    });
    Object.values(sameClusterIdsRowsMap).forEach((list) => {
      Object.assign(list[0], { rowspan: list.length });
    });
  };

  watch(
    () => props.ticketDetails,
    () => {
      if (props.ticketDetails) {
        const { infos } = props.ticketDetails;
        if (infos.length > 0) {
          tableData.value = infos.map((item) => {
            return createTableRow({
              labels: (item.resource_spec.target_proxy.labels || []).map((item) => ({ id: Number(item) })),
              originProxy: {
                ip: item.old_nodes.proxy?.[0]?.ip || '',
              },
              specId: item.resource_spec.target_proxy.spec_id,
            });
          });
        }
      }
    },
  );

  const handleBatchEdit = (list: SelectorItem[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedMap.value[item.ip]) {
        acc.push(
          createTableRow({
            originProxy: {
              ip: item.ip,
            },
          }),
        );
      }
      return acc;
    }, []);
    tableData.value = [...(selected.value.length ? tableData.value : []), ...dataList];
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const dataList = data.reduce<RowData[]>((acc, item) => {
      acc.push(
        createTableRow({
          labels: (item.labels as string)?.split(',').map((item) => ({ value: item })),
          originProxy: {
            ip: item.proxy_ip,
          },
          specId: item.spec_name,
        }),
      );
      return acc;
    }, []);
    if (isClear) {
      tableKey.value = random();
      tableData.value = [...dataList];
    } else {
      tableData.value = [...(selected.value.length ? tableData.value : []), ...dataList];
    }
    setTimeout(() => {
      tableRef.value?.validate();
    }, 200);
  };

  const handleBatchEditColumn = (value: any, field: string) => {
    tableData.value.forEach((rowData) => {
      Object.assign(rowData, {
        [field]: value,
      });
    });
  };

  defineExpose<Exposes>({
    async getValue() {
      const validateResult = await tableRef.value?.validate();
      if (!validateResult) {
        return [];
      }

      return Object.values(sameClusterIdsRowsMap).map((rows) => ({
        cluster_ids: rows[0].originProxy.related_clusters.map((item) => item.id),
        old_nodes: {
          proxy: rows[0].originProxy.related_instances.map((item) => ({
            bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
            bk_cloud_id: item.bk_cloud_id,
            bk_host_id: item.bk_host_id,
            ip: item.ip,
            port: item.port,
          })),
        },
        origin_proxy_ip: {
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          bk_cloud_id: rows[0].originProxy.bk_cloud_id,
          bk_host_id: rows[0].originProxy.bk_host_id,
          ip: rows[0].originProxy.ip,
        },
        resource_spec: {
          target_proxy: {
            count: rows.length,
            label_names: rows[0].labels.map((item) => item.value),
            labels: rows[0].labels.map((item) => String(item.id)),
            spec_id: rows[0].specId,
          },
        },
      }));
    },
    reset() {
      tableData.value = [createTableRow()];
    },
  });
</script>
