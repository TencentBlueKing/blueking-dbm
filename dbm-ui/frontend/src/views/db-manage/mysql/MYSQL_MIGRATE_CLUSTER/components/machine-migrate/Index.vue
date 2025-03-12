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
        v-model="item.master"
        :selected="selected"
        @batch-edit="handleBatchEdit" />
      <SingleResourceHostColumn
        v-model="item.newMaster"
        field="newMaster.ip"
        :label="t('新Master主机')"
        :min-width="150"
        :params="{
          for_bizs: [currentBizId, 0],
          resource_types: [DBTypes.MYSQL, 'PUBLIC'],
        }" />
      <SingleResourceHostColumn
        v-model="item.newSlave"
        field="newSlave.ip"
        :label="t('新Slave主机')"
        :min-width="150"
        :params="{
          for_bizs: [currentBizId, 0],
          resource_types: [DBTypes.MYSQL, 'PUBLIC'],
        }" />
      <OperationColumn
        v-model:table-data="tableData"
        :create-row-method="createTableRow" />
    </EditableRow>
  </EditableTable>
</template>
<script lang="ts" setup>
  import { useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { Mysql } from '@services/model/ticket/ticket';

  import { DBTypes } from '@common/const';

  import SingleResourceHostColumn from '@views/db-manage/common/toolbox-field/column/single-resource-host-column/Index.vue';

  import HostColumnGroup, { type SelectorItem } from './components/HostColumnGroup.vue';

  interface RowData {
    master: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      cluster_ids: number[];
      ip: string;
      port: number;
      related_clusters: string[];
      related_instances: string[];
    };
    newMaster: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    };
    newSlave: {
      bk_biz_id: number;
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    };
  }

  interface Props {
    ticketDetails?: Mysql.ResourcePool.MigrateCluster;
  }

  interface Exposes {
    getValue(): Promise<
      {
        cluster_ids: number[];
        resource_spec: {
          new_master: {
            hosts: {
              bk_biz_id: number;
              bk_cloud_id: number;
              bk_host_id: number;
              ip: string;
            }[];
            spec_id: 0;
          };
          new_slave: {
            hosts: {
              bk_biz_id: number;
              bk_cloud_id: number;
              bk_host_id: number;
              ip: string;
            }[];
            spec_id: 0;
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

  const createTableRow = (data = {} as Partial<RowData>) => ({
    master: data.master || {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      bk_cloud_id: 0,
      bk_host_id: 0,
      cluster_ids: [],
      ip: '',
      port: 0,
      related_clusters: [],
      related_instances: [],
    },
    newMaster: data.newMaster || {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      bk_cloud_id: 0,
      bk_host_id: 0,
      ip: '',
    },
    newSlave: data.newSlave || {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      bk_cloud_id: 0,
      bk_host_id: 0,
      ip: '',
    },
  });

  const tableData = ref<RowData[]>([createTableRow()]);

  const selected = computed(() => tableData.value.filter((item) => item.master.bk_host_id).map((item) => item.master));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  watch(
    () => props.ticketDetails,
    () => {
      if (props.ticketDetails) {
        const { infos } = props.ticketDetails;
        if (infos.length > 0) {
          tableData.value = infos.map((item) => {
            const oldMaster = item.old_nodes.old_master[0];
            return createTableRow({
              master: {
                ...oldMaster,
                cluster_ids: [],
                port: 0,
                related_clusters: [],
                related_instances: [],
              },
              newMaster: item.resource_spec.new_master.hosts[0],
              newSlave: item.resource_spec.new_slave.hosts[0],
            });
          });
        }
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
            master: {
              bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
              bk_cloud_id: item.bk_cloud_id,
              bk_host_id: item.bk_host_id,
              cluster_ids: clusterIds,
              ip: item.ip,
              port: adminPort,
              related_clusters: relatedClusters,
              related_instances: relatedInstances,
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

      return tableData.value.map(({ master, newMaster, newSlave }) => ({
        cluster_ids: master.cluster_ids,
        resource_spec: {
          new_master: {
            hosts: [newMaster],
            spec_id: 0,
          },
          new_slave: {
            hosts: [newSlave],
            spec_id: 0,
          },
        },
      }));
    },
    reset() {
      tableData.value = [createTableRow()];
    },
  });
</script>
