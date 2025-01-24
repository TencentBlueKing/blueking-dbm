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
      <HostColumn
        v-model="item.host"
        :after-input="(data: RedisMachineModel) => afterInput(data, index)"
        :cluster-types="['RedisHost']"
        :label="t('主库主机')"
        :placeholder="t('请输入IP（单个）')"
        :selected="selected"
        :tab-list-config="tabListConfig"
        @batch-edit="handleHostBatchEdit" />
      <OldMasterSlaveHostColumn
        v-model="item.instance_data"
        :data="item.host.related_instances" />
      <SpecSelectColumn
        v-model="item.target_spec_id"
        :current-spec-ids="item.host.spec_config.id ? [item.host.spec_config.id] : []"
        field="target_spec_id"
        :label="t('规格')"
        :params="{
          clusterType: ClusterTypes.REDIS,
          bkCloudId: item.host.bk_cloud_id,
          machineType: specClusterMachineMap[ClusterTypes.REDIS_INSTANCE],
        }">
      </SpecSelectColumn>
      <TargetVersionSelectColumn
        v-model="item.db_version"
        :cluster-type="item.host.cluster_type"
        :current-versions="item.host.related_clusters.length ? [item.host.related_clusters[0].major_version] : []"
        :table-data="
          tableData.map((tableItem) => ({
            id: tableItem.host.bk_host_id,
            cluster_type: tableItem.host.cluster_type,
          }))
        "
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
  import RedisMachineModel from '@services/model/redis/redis-machine';
  import TicketModel, { type Redis } from '@services/model/ticket/ticket';
  import { getRedisMachineList } from '@services/source/redis';

  import { ClusterTypes } from '@common/const';

  import { type IValue, type PanelListType } from '@components/instance-selector/Index.vue';

  import SpecSelectColumn from '@views/db-manage/common/toolbox-field/column/spec-select-column/Index.vue';
  import { specClusterMachineMap } from '@views/db-manage/redis/common/const';
  import HostColumn from '@views/db-manage/redis/common/toolbox-field/host-column/Index.vue';
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
    host: {
      bk_host_id: number;
      ip: string;
      bk_cloud_id: number;
      cluster_type: string;
      related_instances: ComponentProps<typeof OldMasterSlaveHostColumn>['data'];
      spec_config: NonNullable<IValue['spec_config']>;
      related_clusters: {
        major_version: string;
      }[];
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
    host: Object.assign(
      {
        bk_host_id: 0,
        ip: '',
        bk_cloud_id: 0,
        cluster_type: '',
        related_instances: [] as IDataRow['host']['related_instances'],
        spec_config: {} as IDataRow['host']['spec_config'],
        related_clusters: [] as IDataRow['host']['related_clusters'],
      },
      values.host,
    ),
    instance_data: [] as IDataRow['instance_data'],
    target_spec_id: values.target_spec_id || 0,
    db_version: values.db_version || '',
  });

  const { t } = useI18n();

  const editableTableRef = useTemplateRef('editableTable');

  const rules = {
    'host.ip': [
      {
        validator: (value: string) => {
          if (value) {
            const hostList = tableData.value.filter((row) => row.host.ip === value);
            return hostList.length === 1;
          }
          return true;
        },
        trigger: 'change',
        message: t('主机重复'),
      },
    ],
  };

  const tableData = ref([createRowData()]);

  const tabListConfig = {
    RedisHost: [
      {
        topoConfig: {
          totalCountFunc: (dataList: RedisModel[]) => {
            const ipSet = new Set<string>();
            dataList.forEach((dataItem) => dataItem.redis_master.forEach((masterItem) => ipSet.add(masterItem.ip)));
            return ipSet.size;
          },
        },
        tableConfig: {
          getTableList: (params: ServiceReturnType<typeof getRedisMachineList>) =>
            getRedisMachineList({
              cluster_type: ClusterTypes.REDIS_INSTANCE,
              ...params,
            }),
          disabledRowConfig: {
            handler: (data: RedisMachineModel) =>
              data.isUnvailable || data.related_instances.some((item) => item.status === 'unavailable'),
            tip: t('集群或实例状态异常，不可选择'),
          },
        },
      },
      {
        manualConfig: {
          checkInstances: (params: ServiceReturnType<typeof getRedisMachineList>) =>
            getRedisMachineList({
              cluster_type: ClusterTypes.REDIS_INSTANCE,
              ...params,
            }),
        },
        tableConfig: {
          disabledRowConfig: {
            handler: (data: RedisMachineModel) =>
              data.isUnvailable || data.related_instances.some((item) => item.status === 'unavailable'),
            tip: t('集群或实例状态异常，不可选择'),
          },
        },
      },
    ],
  } as unknown as Record<ClusterTypes, PanelListType>;

  const selected = computed(() => {
    const selectedClusters: ComponentProps<typeof HostColumn>['selected'] = {
      RedisHost: [],
    };
    tableData.value.forEach((tableRow) => {
      const { ip } = tableRow.host;
      if (ip) {
        selectedClusters.RedisHost.push(tableRow.host as unknown as IValue);
      }
    });
    return selectedClusters;
  });

  const ipMemo = computed(() =>
    Object.fromEntries(
      Object.values(selected.value).flatMap((machineList) =>
        machineList.filter((machineItem) => machineItem.ip).map((machineItem) => [machineItem.ip, true]),
      ),
    ),
  );

  const handleHostBatchEdit = (list: IValue[]) => {
    const newList: IDataRow[] = [];
    list.forEach((item) => {
      if (!ipMemo.value[item.ip]) {
        newList.push(
          createRowData({
            host: {
              bk_host_id: item.bk_host_id,
              ip: item.ip,
              bk_cloud_id: item.bk_cloud_id,
              cluster_type: item.cluster_type,
              related_instances: item.related_instances,
              spec_config: item.spec_config!,
              related_clusters: item.related_clusters,
            },
          }),
        );
      }
    });
    tableData.value = [...(tableData.value[0].host.ip ? tableData.value : []), ...newList];
    window.changeConfirm = true;
  };

  const afterInput = async (host: RedisMachineModel, index: number) => {
    tableData.value[index].host = {
      bk_host_id: host.bk_host_id,
      ip: host.ip,
      bk_cloud_id: host.bk_cloud_id,
      cluster_type: host.cluster_type,
      related_instances: host.related_instances,
      spec_config: host.spec_config!,
      related_clusters: host.related_clusters,
    };
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
                migrate_type: 'machine',
                ip: tableItem.host.ip,
                domain: '',
              },
            })),
          );
        }
        return [];
      }),
    setTableByTicketClone: (ticketDetail: TicketModel<Redis.MigrateSingle>) => {
      const { infos } = ticketDetail.details;
      const rowMap = infos.reduce<Record<string, Redis.MigrateSingle['infos']>>((prevMap, infoItem) => {
        if (prevMap[infoItem.display_info.ip]) {
          return Object.assign({}, prevMap, {
            [infoItem.display_info.ip]: prevMap[infoItem.display_info.ip].concat(infoItem),
          });
        }
        return Object.assign({}, prevMap, {
          [infoItem.display_info.ip]: [infoItem],
        });
      }, {});

      tableData.value = Object.values(rowMap).map((infoItem) => {
        const rowItem = infoItem[0];
        return createRowData({
          host: {
            ip: rowItem.display_info.ip,
          } as IDataRow['host'],
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
