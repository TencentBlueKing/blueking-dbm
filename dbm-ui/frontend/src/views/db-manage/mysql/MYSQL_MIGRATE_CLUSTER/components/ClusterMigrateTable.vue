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
      <ClusterColumn
        v-model="item.cluster"
        :selected-ids="selectedClusterIds"
        @batch-edit="handleBatchEdit" />
      <SingleHostColumn
        v-model="item.newMaster"
        field="newMaster.ip"
        :label="t('新Master主机')" />
      <SingleHostColumn
        v-model="item.newSlave"
        field="newSlave.ip"
        :label="t('新Slave主机')" />
      <OperationColumn
        v-model:table-data="tableData"
        :create-row-method="createTableRow" />
    </EditableRow>
  </EditableTable>
</template>
<script lang="ts" setup>
  import { useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';

  import SingleHostColumn from '@views/db-manage/common/toolbox-field/column/single-host-column/Index.vue';

  import { MigrateTypes } from '../types';

  import ClusterColumn from './ClusterColumn.vue';

  interface RowData {
    cluster: {
      cluster_ids: number[];
      cluster_domains: string;
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
    data: RowData[];
  }

  interface Exposes {
    getValue: () => Promise<
      {
        cluster_ids: number[];
        resource_spec: {
          new_master: {
            spec_id: 0;
            hosts: {
              bk_biz_id: number;
              bk_cloud_id: number;
              bk_host_id: number;
              ip: string;
            }[];
          };
          new_slave: {
            spec_id: 0;
            hosts: {
              bk_biz_id: number;
              bk_cloud_id: number;
              bk_host_id: number;
              ip: string;
            }[];
          };
        };
        display_info: {
          type: MigrateTypes;
        };
      }[]
    >;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data = {} as Partial<RowData>) => ({
    cluster: data.cluster || {
      cluster_ids: [],
      cluster_domains: '',
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

  const selectedClusterIds = computed(() => tableData.value.flatMap((item) => item.cluster.cluster_ids));

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

  const handleBatchEdit = (list: TendbhaModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!selectedClusterIds.value.includes(item.id)) {
        acc.push(
          createTableRow({
            cluster: {
              cluster_ids: [item.id],
              cluster_domains: item.master_domain,
            },
          }),
        );
      }
      return acc;
    }, []);
    tableData.value = [...(selectedClusterIds.value.length ? tableData.value : []), ...dataList];
  };

  defineExpose<Exposes>({
    async getValue() {
      const validateResult = await tableRef.value?.validate();
      if (!validateResult) {
        return [];
      }

      return tableData.value.map(({ cluster, newMaster, newSlave }) => ({
        cluster_ids: cluster.cluster_ids,
        resource_spec: {
          new_master: {
            spec_id: 0,
            hosts: [newMaster],
          },
          new_slave: {
            spec_id: 0,
            hosts: [newSlave],
          },
        },
        display_info: {
          type: MigrateTypes.CLUSTER_MIGRATE,
        },
      }));
    },
  });
</script>
