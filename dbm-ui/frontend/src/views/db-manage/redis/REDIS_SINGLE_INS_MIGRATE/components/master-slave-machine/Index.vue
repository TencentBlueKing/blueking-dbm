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
        hide-manual-input
        :label="t('主库主机')"
        :placeholder="t('请输入IP（单个）')"
        :selected="selected"
        :tab-list-config="tabListConfig"
        @batch-edit="handleHostBatchEdit" />
      <OldMasterSlaveHostColumn
        v-model="item.instance_data"
        :data="item.host.related_instances" />
      <SpecColumn
        v-model="item.target_spec_id"
        :cluster-type="DBTypes.REDIS"
        :current-spec-id-list="item.host.spec_config.id ? [item.host.spec_config.id] : []"
        field="target_spec_id"
        :label="t('规格')"
        :machine-type="specClusterMachineMap[ClusterTypes.REDIS_INSTANCE]"
        required
        selectable
        @batch-edit="handleBatchEdit" />
      <ResourceTagColumn
        v-model="item.labels"
        @batch-edit="handleBatchEdit" />
      <AvailableResourceColumn
        :params="{
          city: item.host.related_clusters?.[0]?.region,
          for_bizs: [currentBizId, 0],
          resource_types: [DBTypes.REDIS, 'PUBLIC'],
          spec_id: item.target_spec_id,
          labels: item.labels.map((item) => item.id).join(','),
        }" />
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
  import { type Redis } from '@services/model/ticket/ticket';
  import { getRedisMachineList } from '@services/source/redis';

  import { useTicketDetail } from '@hooks';

  import { ClusterTypes, DBTypes, TicketTypes } from '@common/const';

  import { type IValue, type PanelListType } from '@components/instance-selector/Index.vue';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import AvailableResourceColumn from '@views/db-manage/common/toolbox-field/column/available-resource-column/Index.vue';
  import ResourceTagColumn from '@views/db-manage/common/toolbox-field/column/resource-tag-column/Index.vue';
  import SpecColumn from '@views/db-manage/common/toolbox-field/column/spec-column/Index.vue';
  import { specClusterMachineMap } from '@views/db-manage/redis/common/const';
  import HostColumn from '@views/db-manage/redis/common/toolbox-field/host-column/Index.vue';
  import TargetVersionSelectColumn from '@views/db-manage/redis/common/toolbox-field/target-version-select-column/Index.vue';

  import { random } from '@utils';

  import OldMasterSlaveHostColumn from '../OldMasterSlaveHostColumn.vue';

  interface Exposes {
    getValue: () => Promise<Redis.ResourcePool.MigrateSingle['infos']>;
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
    db_version: string;
    host: {
      bk_cloud_id: number;
      bk_host_id: number;
      cluster_type: string;
      ip: string;
      related_clusters: {
        major_version: string;
        region: string;
      }[];
      related_instances: ComponentProps<typeof OldMasterSlaveHostColumn>['data'];
      spec_config: NonNullable<IValue['spec_config']>;
    };
    instance_data: {
      origin_old_nodes: {
        master: IHostData[];
        slave: IHostData[];
      };
      src_cluster: {
        cluster_id: number;
        master_ins: string;
        slave_ins: string;
      }[];
    };
    labels: ComponentProps<typeof ResourceTagColumn>['modelValue'];
    target_spec_id: number;
  }

  const createRowData = (values: DeepPartial<IDataRow> = {}) => ({
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
    instance_data: {} as IDataRow['instance_data'],
    labels: (values.labels || []) as IDataRow['labels'],
    target_spec_id: values.target_spec_id || 0,
  });

  const { t } = useI18n();

  const editableTableRef = useTemplateRef('editableTable');

  useTicketDetail<Redis.ResourcePool.MigrateSingle>(TicketTypes.REDIS_SINGLE_INS_MIGRATE, {
    onSuccess(ticketDetail) {
      const { infos } = ticketDetail.details;
      const rowMap = infos.reduce<Record<string, Redis.ResourcePool.MigrateSingle['infos']>>((prevMap, infoItem) => {
        const migrateIp = infoItem.migrate_ip!;
        if (prevMap[migrateIp]) {
          return Object.assign({}, prevMap, {
            [migrateIp]: prevMap[migrateIp].concat(infoItem),
          });
        }
        return Object.assign({}, prevMap, {
          [migrateIp]: [infoItem],
        });
      }, {});

      tableData.value = Object.values(rowMap).map((infoItem) => {
        const rowItem = infoItem[0];
        return createRowData({
          db_version: rowItem.db_version,
          host: {
            ip: rowItem.migrate_ip,
          } as IDataRow['host'],
          labels: (rowItem.resource_spec.backend_group.labels || []).map((item) => ({ id: Number(item) })),
          target_spec_id: rowItem.resource_spec.backend_group.spec_id,
        });
      });
    },
  });

  const batchInputConfig = [
    {
      case: '192.168.10.2',
      key: 'ip',
      label: t('主库主机'),
    },
    {
      case: t('无限制'),
      key: 'spec_name',
      label: t('目标规格'),
    },
    {
      case: 'Redis-6',
      key: 'version',
      label: t('目标版本'),
    },
  ];

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

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const tableKey = ref(random());
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
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const newList = data.reduce<IDataRow[]>((acc, item) => {
      acc.push(
        createRowData({
          db_version: item.version,
          host: {
            ip: item.ip,
          } as IDataRow['host'],
          target_spec_id: item.spec_name,
        }),
      );
      return acc;
    }, []);
    if (isClear) {
      tableKey.value = random();
      tableData.value = [...newList];
    } else {
      tableData.value = [...(selected.value.length ? tableData.value : []), ...newList];
    }
    setTimeout(() => {
      editableTableRef.value!.validate();
    }, 200);
  };

  const handleBatchEdit = (value: number, field: string) => {
    tableData.value.forEach((item) => {
      Object.assign(item, { [field]: value });
    });
  };

  defineExpose<Exposes>({
    getValue: () =>
      editableTableRef.value!.validate().then((validateResult) => {
        if (validateResult) {
          return tableData.value.map((tableItem) => ({
            ...tableItem.instance_data,
            db_version: tableItem.db_version,
            // migrate_domain: '',
            migrate_ip: tableItem.host.ip,
            migrate_type: 'machine',
            resource_spec: {
              backend_group: {
                count: 1,
                label_names: tableItem.labels.map((item) => item.value),
                labels: tableItem.labels.map((item) => String(item.id)),
                spec_id: tableItem.target_spec_id,
              },
            },
          }));
        }
        return [];
      }),
    resetTable: () => {
      tableData.value = [createRowData()];
    },
  });
</script>
