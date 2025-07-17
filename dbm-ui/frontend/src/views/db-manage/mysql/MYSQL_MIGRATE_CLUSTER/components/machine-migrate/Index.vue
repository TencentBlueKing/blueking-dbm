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
    :model="tableData"
    :rules="rules">
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
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import type { Mysql } from '@services/model/ticket/ticket';

  import { DBTypes } from '@common/const';

  import SingleResourceHostColumn from '@views/db-manage/common/toolbox-field/column/single-resource-host-column/Index.vue';

  import HostColumnGroup, { type SelectorItem } from './components/HostColumnGroup.vue';

  interface RowData {
    master: ComponentProps<typeof HostColumnGroup>['modelValue'];
    newMaster: ComponentProps<typeof SingleResourceHostColumn>['modelValue'];
    newSlave: ComponentProps<typeof SingleResourceHostColumn>['modelValue'];
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

  const createTableRow = (data = {} as DeepPartial<RowData>) => ({
    master: Object.assign(
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        bk_cloud_id: 0,
        bk_host_id: 0,
        cluster_ids: [],
        ip: '',
        port: 0,
        related_clusters: [],
        related_instances: [],
      },
      data.master,
    ),
    newMaster: Object.assign(
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        bk_cloud_id: 0,
        bk_host_id: 0,
        ip: '',
      },
      data.newMaster,
    ),
    newSlave: Object.assign(
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        bk_cloud_id: 0,
        bk_host_id: 0,
        ip: '',
      },
      data.newSlave,
    ),
  });

  const tableData = ref<RowData[]>([createTableRow()]);

  const selected = computed(() => tableData.value.filter((item) => item.master.bk_host_id).map((item) => item.master));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  const newHostCounter = computed(() => {
    return tableData.value.reduce<Record<string, number>>((result, item) => {
      let masterCount = 1;
      if (item.master.ip === item.newMaster.ip) {
        masterCount += 1;
      }
      let slaveCount = masterCount;
      if (item.newMaster.ip === item.newSlave.ip) {
        slaveCount += 1;
      }
      Object.assign(result, {
        [item.master.ip]: (result[item.master.ip] || 0) + 1,
        [item.newMaster.ip]: (result[item.newMaster.ip] || 0) + masterCount,
        [item.newSlave.ip]: (result[item.newSlave.ip] || 0) + slaveCount,
      });
      return result;
    }, {});
  });

  const rules = {
    'master.ip': [
      {
        message: t('IP 重复'),
        trigger: 'blur',
        validator: (value: string, { rowData }: { rowData: RowData }) => {
          if (!value) {
            return true;
          }
          const row = rowData as RowData;
          return newHostCounter.value[row.master.ip] <= 1;
        },
      },
      {
        message: t('IP 重复'),
        trigger: 'change',
        validator: (value: string, { rowData }: { rowData: RowData }) => {
          if (!value) {
            return true;
          }
          const row = rowData as RowData;
          return newHostCounter.value[row.master.ip] <= 1;
        },
      },
    ],
    'newMaster.ip': [
      {
        message: t('IP 重复'),
        trigger: 'blur',
        validator: (value: string, { rowData }: { rowData: RowData }) => {
          if (!value) {
            return true;
          }
          const row = rowData as RowData;
          return newHostCounter.value[row.newMaster.ip] <= 1;
        },
      },
      {
        message: t('IP 重复'),
        trigger: 'change',
        validator: (value: string, { rowData }: { rowData: RowData }) => {
          if (!value) {
            return true;
          }
          const row = rowData as RowData;
          return newHostCounter.value[row.newMaster.ip] <= 1;
        },
      },
    ],
    'newSlave.ip': [
      {
        message: t('IP 重复'),
        trigger: 'blur',
        validator: (value: string, { rowData }: { rowData: RowData }) => {
          if (!value) {
            return true;
          }
          const row = rowData as RowData;
          return newHostCounter.value[row.newSlave.ip] <= 1;
        },
      },
      {
        message: t('IP 重复'),
        trigger: 'change',
        validator: (value: string, { rowData }: { rowData: RowData }) => {
          if (!value) {
            return true;
          }
          const row = rowData as RowData;
          return newHostCounter.value[row.newSlave.ip] <= 1;
        },
      },
    ],
  };

  watch(
    () => props.ticketDetails,
    () => {
      if (props.ticketDetails) {
        const { infos } = props.ticketDetails;
        if (infos.length > 0) {
          tableData.value = infos.map((item) => {
            return createTableRow({
              master: {
                ip: item.old_nodes.old_master?.[0]?.ip,
              },
              newMaster: {
                ip: item.resource_spec.new_master.hosts?.[0]?.ip,
              },
              newSlave: {
                ip: item.resource_spec.new_slave.hosts?.[0]?.ip,
              },
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
            master: {
              ip: item.ip,
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
