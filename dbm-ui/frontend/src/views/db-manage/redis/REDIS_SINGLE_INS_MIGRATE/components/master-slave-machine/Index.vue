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
    :model="tableData"
    :rules="rules">
    <EditableRow
      v-for="(item, index) in tableData"
      :key="index">
      <HostColumn
        v-model="item.host"
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
        :bk-cloud-id="item.host.bk_cloud_id"
        :cluster-type="ClusterTypes.REDIS"
        :current-spec-ids="item.host.spec_config.id ? [item.host.spec_config.id] : []"
        field="target_spec_id"
        :label="t('规格')"
        :machine-type="specClusterMachineMap[ClusterTypes.REDIS_INSTANCE]">
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
        " />
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

  import { specClusterMachineMap } from '@views/db-manage/redis/common/const';
  import HostColumn from '@views/db-manage/redis/common/toolbox-field/host-column/Index.vue';
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
    db_version: string;
    host: {
      bk_cloud_id: number;
      bk_host_id: number;
      cluster_type: string;
      ip: string;
      related_clusters: {
        major_version: string;
      }[];
      related_instances: ComponentProps<typeof OldMasterSlaveHostColumn>['data'];
      spec_config: NonNullable<IValue['spec_config']>;
    };
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
    db_version: values.db_version || '',
    host: Object.assign(
      {
        bk_cloud_id: 0,
        bk_host_id: 0,
        cluster_type: '',
        ip: '',
        related_clusters: [] as IDataRow['host']['related_clusters'],
        related_instances: [] as IDataRow['host']['related_instances'],
        spec_config: {} as IDataRow['host']['spec_config'],
      },
      values.host,
    ),
    instance_data: [] as IDataRow['instance_data'],
    target_spec_id: values.target_spec_id || 0,
  });

  const { t } = useI18n();

  const editableTableRef = useTemplateRef('editableTable');

  const rules = {
    'host.ip': [
      {
        message: t('主机重复'),
        trigger: 'change',
        validator: (value: string) => {
          if (value) {
            const hostList = tableData.value.filter((row) => row.host.ip === value);
            return hostList.length === 1;
          }
          return true;
        },
      },
    ],
  };

  const tableData = ref([createRowData()]);

  const tabListConfig = {
    RedisHost: [
      {
        tableConfig: {
          disabledRowConfig: {
            handler: (data: RedisMachineModel) =>
              data.isUnvailable || data.related_instances.some((item) => item.status === 'unavailable'),
            tip: t('集群或实例状态异常，不可选择'),
          },
          getTableList: (params: ServiceReturnType<typeof getRedisMachineList>) =>
            getRedisMachineList({
              cluster_type: ClusterTypes.REDIS_INSTANCE,
              ...params,
            }),
        },
        topoConfig: {
          totalCountFunc: (dataList: RedisModel[]) => {
            const ipSet = new Set<string>();
            dataList.forEach((dataItem) => dataItem.redis_master.forEach((masterItem) => ipSet.add(masterItem.ip)));
            return ipSet.size;
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

  const selected = computed(() => tableData.value.filter((item) => item.host.bk_host_id).map((item) => item.host));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  const handleHostBatchEdit = (list: IValue[]) => {
    const newList: IDataRow[] = [];
    list.forEach((item) => {
      if (!selectedMap.value[item.ip]) {
        newList.push(
          createRowData({
            host: {
              bk_cloud_id: item.bk_cloud_id,
              bk_host_id: item.bk_host_id,
              cluster_type: item.cluster_type,
              ip: item.ip,
              related_clusters: item.related_clusters,
              related_instances: item.related_instances,
              spec_config: item.spec_config!,
            },
          }),
        );
      }
    });
    tableData.value = [...(selected.value.length ? tableData.value : []), ...newList];
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
                domain: '',
                ip: tableItem.host.ip,
                migrate_type: 'machine',
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
          db_version: rowItem.db_version,
          host: {
            ip: rowItem.display_info.ip,
          } as IDataRow['host'],
          target_spec_id: rowItem.resource_spec.backend_group.spec_id,
        });
      });
    },
  });
</script>
