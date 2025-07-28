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
    ref="editableTable"
    class="mt-16 mb-16"
    :model="tableData">
    <EditableRow
      v-for="(item, index) in tableData"
      :key="index">
      <ClusterColumn
        v-model="item.cluster"
        :cluster-types="[ClusterTypes.REDIS]"
        :selected="selected"
        :tab-list-config="tabListConfig"
        @batch-edit="handleClusterBatchEdit" />
      <OldMasterSlaveHostColumn
        v-model="item.instance_data"
        :data="item.cluster.redis_master" />
      <SpecSelectColumn
        v-model="item.target_spec_id"
        :bk-cloud-id="item.cluster.bk_cloud_id"
        :cluster-type="ClusterTypes.REDIS"
        :current-spec-ids="item.cluster.cluster_spec.spec_id ? [item.cluster.cluster_spec.spec_id] : []"
        field="target_spec_id"
        :label="t('规格')"
        :machine-type="specClusterMachineMap[ClusterTypes.REDIS_INSTANCE]">
      </SpecSelectColumn>
      <TargetVersionSelectColumn
        v-model="item.db_version"
        :cluster-type="item.cluster.cluster_type"
        :current-versions="item.cluster.major_version ? [item.cluster.major_version] : []" />
      <OperationColumn
        :create-row-method="createRowData"
        :table-data="tableData" />
    </EditableRow>
  </EditableTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';
  import TicketModel, { type Redis } from '@services/model/ticket/ticket';
  import { getRedisList } from '@services/source/redis';

  import { ClusterTypes } from '@common/const';

  import { type TabItem } from '@components/cluster-selector/Index.vue';

  import { specClusterMachineMap } from '@views/db-manage/redis/common/const';
  import ClusterColumn from '@views/db-manage/redis/common/toolbox-field/cluster-column/Index.vue';
  import SpecSelectColumn from '@views/db-manage/redis/common/toolbox-field/spec-select-column/Index.vue';
  import TargetVersionSelectColumn from '@views/db-manage/redis/common/toolbox-field/target-version-select-column/Index.vue';

  import OldMasterSlaveHostColumn from '../OldMasterSlaveHostColumn.vue';

  interface Exposes {
    getValue: () => Promise<
      {
        cluster_id: number;
        db_version: string;
        display_info: {
          domain: string;
          ip: string;
          migrate_type: string; // domain | machine
        };
        old_nodes: {
          master: {
            bk_biz_id: number;
            bk_cloud_id: number;
            bk_host_id: number;
            ip: string;
            port: number;
          }[];
          slave: {
            bk_biz_id: number;
            bk_cloud_id: number;
            bk_host_id: number;
            ip: string;
            port: number;
          }[];
        };
        resource_spec: {
          backend_group: {
            count: number;
            spec_id: number;
          };
        };
      }[]
    >;
    resetTable: () => void;
    setTableByTicketClone: (infos: TicketModel<Redis.MigrateSingle>) => void;
  }

  interface IHostData {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    ip: string;
    port: number;
  }

  interface IDataRow {
    cluster: {
      bk_cloud_id: number;
      cluster_spec: RedisModel['cluster_spec'];
      cluster_type: string;
      id: number;
      major_version: string;
      master_domain: string;
      redis_master: RedisModel['redis_master'];
    };
    db_version: string;
    instance_data: {
      cluster_id: number;
      old_nodes: {
        master: IHostData[];
        slave: IHostData[];
      };
    }[];
    target_spec_id: number;
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    cluster: Object.assign(
      {
        bk_cloud_id: 0,
        cluster_spec: {} as RedisModel['cluster_spec'],
        cluster_type: '',
        id: 0,
        major_version: '',
        master_domain: '',
        redis_master: [] as RedisModel['redis_master'],
      },
      values.cluster,
    ),
    db_version: values.db_version || '',
    instance_data: [] as IDataRow['instance_data'],
    target_spec_id: values.target_spec_id || 0,
  });

  const { t } = useI18n();

  const editableTableRef = useTemplateRef('editableTable');

  const tabListConfig = {
    [ClusterTypes.REDIS]: {
      getResourceList: (params: ServiceParameters<typeof getRedisList>) =>
        getRedisList({
          cluster_type: ClusterTypes.REDIS_INSTANCE,
          ...params,
        }),
    },
  } as unknown as Record<ClusterTypes, TabItem>;

  const tableData = ref([createRowData()]);

  const selected = computed(() => tableData.value.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const handleClusterBatchEdit = (clusterList: RedisModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      if (!selectedMap.value[item.master_domain]) {
        newList.push(
          createRowData({
            cluster: {
              bk_cloud_id: item.bk_cloud_id,
              cluster_spec: item.cluster_spec,
              cluster_type: item.cluster_type,
              id: item.id,
              major_version: item.major_version,
              master_domain: item.master_domain,
              redis_master: item.redis_master,
            },
          }),
        );
      }
    });
    tableData.value = [...(tableData.value[0].cluster.master_domain ? tableData.value : []), ...newList];
    window.changeConfirm = true;
  };

  defineExpose<Exposes>({
    getValue: () =>
      editableTableRef.value!.validate().then((validateResult) => {
        if (validateResult) {
          return tableData.value.flatMap((tableItem) =>
            tableItem.instance_data.map((instanceItem) => ({
              ...instanceItem,
              db_version: tableItem.db_version,
              display_info: {
                domain: tableItem.cluster.master_domain,
                ip: '',
                migrate_type: 'domain',
              },
              resource_spec: {
                backend_group: {
                  count: 1,
                  spec_id: tableItem.target_spec_id,
                },
              },
            })),
          );
        }
        return [];
      }),
    resetTable: () => {
      tableData.value = [createRowData()];
    },
    setTableByTicketClone: (ticketDetail: TicketModel<Redis.MigrateSingle>) => {
      const { infos } = ticketDetail.details;
      const rowMap = infos.reduce<Record<string, Redis.MigrateSingle['infos']>>((prevMap, infoItem) => {
        if (prevMap[infoItem.display_info.domain]) {
          return Object.assign({}, prevMap, {
            [infoItem.display_info.domain]: prevMap[infoItem.display_info.domain].concat(infoItem),
          });
        }
        return Object.assign({}, prevMap, {
          [infoItem.display_info.domain]: [infoItem],
        });
      }, {});

      tableData.value = Object.values(rowMap).map((infoItem) => {
        const rowItem = infoItem[0];
        return createRowData({
          cluster: {
            master_domain: rowItem.display_info.domain,
          } as IDataRow['cluster'],
          db_version: rowItem.db_version,
          target_spec_id: rowItem.resource_spec.backend_group.spec_id,
        });
      });
    },
  });
</script>
