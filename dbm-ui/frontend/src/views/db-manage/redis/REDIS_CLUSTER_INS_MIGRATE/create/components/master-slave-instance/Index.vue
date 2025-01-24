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
    class="mt16 mb16"
    :model="tableData"
    :rules="rules">
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
        :current-spec-ids="item.cluster.cluster_spec.spec_id ? [item.cluster.cluster_spec.spec_id] : []"
        field="target_spec_id"
        :label="t('规格')"
        :params="{
          clusterType: ClusterTypes.REDIS,
          bkCloudId: item.cluster.bk_cloud_id,
          machineType: specClusterMachineMap[ClusterTypes.REDIS_INSTANCE],
        }">
      </SpecSelectColumn>
      <TargetVersionSelectColumn
        v-model="item.db_version"
        :cluster-type="item.cluster.cluster_type"
        :current-versions="item.cluster.major_version ? [item.cluster.major_version] : []"
        :table-data="tableData.map((tableItem) => tableItem.cluster)"
        @batch-edit="handleVersionBatchEdit" />
      <OperationColumn
        :create-row-method="createRowData"
        :table-data="tableData" />
    </EditableRow>
  </EditableTable>
</template>
<script setup lang="ts">
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';
  import TicketModel, { type Redis } from '@services/model/ticket/ticket';
  import { getRedisList } from '@services/source/redis';

  import { ClusterTypes } from '@common/const';

  import { type TabItem } from '@components/cluster-selector/Index.vue';

  import SpecSelectColumn from '@views/db-manage/common/toolbox-field/column/spec-select-column/Index.vue';
  import { specClusterMachineMap } from '@views/db-manage/redis/common/const';
  import ClusterColumn from '@views/db-manage/redis/common/toolbox-field/cluster-column/Index.vue';
  import TargetVersionSelectColumn from '@views/db-manage/redis/common/toolbox-field/target-version-select-column/Index.vue';

  import OldMasterSlaveHostColumn from '../common/OldMasterSlaveHostColumn.vue';

  interface Exposes {
    getValue: () => Promise<
      {
        cluster_id: number;
        resource_spec: {
          backend_group: {
            spec_id: number;
            count: number;
          };
        };
        db_version: string;
        old_nodes: {
          master: {
            bk_host_id: number;
            ip: string;
            port: number;
            bk_cloud_id: number;
            bk_biz_id: number;
          }[];
          slave: {
            bk_host_id: number;
            ip: string;
            port: number;
            bk_cloud_id: number;
            bk_biz_id: number;
          }[];
        };
        display_info: {
          migrate_type: string; // domain | machine
          ip: string;
          domain: string;
        };
      }[]
    >;
    setTableByTicketClone: (infos: TicketModel<Redis.MigrateSingle>) => void;
    resetTable: () => void;
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
      id: number;
      master_domain: string;
      bk_cloud_id: number;
      cluster_type: string;
      redis_master: RedisModel['redis_master'];
      cluster_spec: RedisModel['cluster_spec'];
      major_version: string;
    };
    instance_data: {
      cluster_id: number;
      old_nodes: {
        master: IHostData[];
        slave: IHostData[];
      };
    }[];
    target_spec_id: number;
    db_version: string;
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    cluster: Object.assign(
      {
        id: 0,
        master_domain: '',
        bk_cloud_id: 0,
        cluster_type: '',
        redis_master: [] as RedisModel['redis_master'],
        cluster_spec: {} as RedisModel['cluster_spec'],
        major_version: '',
      },
      values.cluster,
    ),
    instance_data: [] as IDataRow['instance_data'],
    target_spec_id: values.target_spec_id || 0,
    db_version: values.db_version || '',
  });

  const { t } = useI18n();

  const editableTableRef = useTemplateRef('editableTable');

  const rules = {
    'cluster.master_domain': [
      {
        validator: (value: string) => {
          if (value) {
            const hostList = tableData.value.filter((row) => row.cluster.master_domain === value);
            return hostList.length === 1;
          }
          return true;
        },
        trigger: 'change',
        message: t('集群重复'),
      },
    ],
  };

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

  const selected = computed(() => {
    const selectedClusters: ComponentProps<typeof ClusterColumn>['selected'] = {
      [ClusterTypes.REDIS]: [],
    };
    tableData.value.forEach((tableRow) => {
      const { id, master_domain: masterDomain } = tableRow.cluster;
      if (id && masterDomain) {
        selectedClusters[ClusterTypes.REDIS].push({
          id,
          master_domain: masterDomain,
        });
      }
    });
    return selectedClusters;
  });

  const clusterMemo = computed(() =>
    Object.fromEntries(
      Object.values(selected.value).flatMap((clusters) =>
        clusters.filter((cluster) => cluster.master_domain).map((cluster) => [cluster.master_domain, true]),
      ),
    ),
  );

  const handleClusterBatchEdit = (clusterList: RedisModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      if (!clusterMemo.value[item.master_domain]) {
        const domain = item.master_domain;
        if (!clusterMemo.value[domain]) {
          newList.push(
            createRowData({
              cluster: {
                id: item.id,
                master_domain: item.master_domain,
                bk_cloud_id: item.bk_cloud_id,
                cluster_type: item.cluster_type,
                redis_master: item.redis_master,
                cluster_spec: item.cluster_spec,
                major_version: item.major_version,
              },
            }),
          );
        }
      }
    });
    tableData.value = [...(tableData.value[0].cluster.master_domain ? tableData.value : []), ...newList];
    window.changeConfirm = true;
  };

  const handleVersionBatchEdit = (value: string) => {
    tableData.value.forEach((tableItem) => {
      Object.assign(tableItem, {
        db_version: value,
      });
    });
  };

  defineExpose<Exposes>({
    getValue: () =>
      editableTableRef.value!.validate().then((validateResult) => {
        if (validateResult) {
          return tableData.value.flatMap((tableItem) =>
            tableItem.instance_data.map((instanceItem) => ({
              ...instanceItem,
              resource_spec: {
                backend_group: {
                  spec_id: tableItem.target_spec_id,
                  count: 1,
                },
              },
              db_version: tableItem.db_version,
              display_info: {
                migrate_type: 'domain',
                ip: '',
                domain: tableItem.cluster.master_domain,
              },
            })),
          );
        }
        return [];
      }),
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
          target_spec_id: rowItem.resource_spec.backend_group.spec_id,
          db_version: rowItem.db_version,
        });
      });
    },
    resetTable: () => {
      tableData.value = [createRowData()];
    },
  });
</script>
