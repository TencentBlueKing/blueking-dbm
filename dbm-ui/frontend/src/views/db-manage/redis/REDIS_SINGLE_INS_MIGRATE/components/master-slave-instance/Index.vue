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
    ref="editableTable"
    class="mt-16 mb-16"
    :model="tableData">
    <EditableRow
      v-for="(item, index) in tableData"
      :key="index">
      <ClusterBatchColumn
        v-model="item.batchCluster"
        :selected="selected"
        :selected-map="selectedMap"
        :tab-list-config="tabListConfig"
        @batch-edit="handleClusterBatchEdit" />
      <OldMasterSlaveHostColumn
        v-model="item.instance_data"
        :data="Object.values(item.batchCluster.clusters).flatMap((item) => item.redis_master)" />
      <SpecSelectColumn
        v-model="item.target_spec_id"
        :bk-cloud-id="Object.values(item.batchCluster.clusters)?.[0]?.bk_cloud_id"
        :cluster-type="ClusterTypes.REDIS"
        :current-spec-ids="Object.values(item.batchCluster.clusters).flatMap((item) => item.cluster_spec.spec_id)"
        field="target_spec_id"
        :label="t('规格')"
        :machine-type="specClusterMachineMap[ClusterTypes.REDIS_INSTANCE]">
      </SpecSelectColumn>
      <TargetVersionSelectColumn
        v-model="item.db_version"
        :cluster-type="Object.values(item.batchCluster.clusters)?.[0]?.cluster_type"
        :current-versions="Object.values(item.batchCluster.clusters).flatMap((item) => item.major_version)" />
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
  import { type Redis } from '@services/model/ticket/ticket';
  import { getRedisList } from '@services/source/redis';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import { type TabItem } from '@components/cluster-selector/Index.vue';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import { specClusterMachineMap } from '@views/db-manage/redis/common/const';
  import SpecSelectColumn from '@views/db-manage/redis/common/toolbox-field/spec-select-column/Index.vue';
  import TargetVersionSelectColumn from '@views/db-manage/redis/common/toolbox-field/target-version-select-column/Index.vue';

  import { useTicketDetail } from '@/hooks';

  import OldMasterSlaveHostColumn from '../OldMasterSlaveHostColumn.vue';

  import ClusterBatchColumn from './components/ClusterBatchColumn.vue';

  interface Exposes {
    getValue: () => Promise<Redis.MigrateSingle['infos']>;
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
    batchCluster: ComponentProps<typeof ClusterBatchColumn>['modelValue'];
    db_version: string;
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
    target_spec_id: number;
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    batchCluster: Object.assign(
      {
        clusters: {} as IDataRow['batchCluster']['clusters'],
        renderText: '',
      },
      values.batchCluster,
    ),
    db_version: values.db_version || '',
    instance_data: {} as IDataRow['instance_data'],
    target_spec_id: values.target_spec_id || 0,
  });

  const { t } = useI18n();

  const editableTableRef = useTemplateRef('editableTable');

  useTicketDetail<Redis.MigrateSingle>(TicketTypes.REDIS_SINGLE_INS_MIGRATE, {
    onSuccess(ticketDetail) {
      const { infos } = ticketDetail.details;
      const rowMap = infos.reduce<Record<string, Redis.MigrateSingle['infos']>>((prevMap, infoItem) => {
        const migrateDomain = infoItem.migrate_domain!;
        if (prevMap[migrateDomain]) {
          return Object.assign({}, prevMap, {
            [migrateDomain]: prevMap[migrateDomain].concat(infoItem),
          });
        }
        return Object.assign({}, prevMap, {
          [migrateDomain]: [infoItem],
        });
      }, {});

      tableData.value = Object.values(rowMap).map((infoItem) => {
        const rowItem = infoItem[0];
        return createRowData({
          batchCluster: {
            renderText: rowItem.migrate_domain,
          } as IDataRow['batchCluster'],
          db_version: rowItem.db_version,
          target_spec_id: rowItem.resource_spec.backend_group.spec_id,
        });
      });
    },
  });

  const batchInputConfig = [
    {
      case: 'redis.test.1.db\\nredis.test.2.db',
      key: 'master_domain',
      label: t('目标集群'),
    },
    {
      case: t('无限制'),
      key: 'spec_name',
      label: t('规格'),
    },
    {
      case: 'Redis-6',
      key: 'version',
      label: t('目标版本'),
    },
  ];

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

  const selected = computed(() =>
    tableData.value
      .filter((item) => item.batchCluster.renderText)
      .flatMap((item) => Object.values(item.batchCluster.clusters)),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const handleClusterBatchEdit = (clusterList: RedisModel[]) => {
    const newList: IDataRow[] = [];
    clusterList.forEach((item) => {
      if (!selectedMap.value[item.master_domain]) {
        newList.push(
          createRowData({
            batchCluster: {
              renderText: item.master_domain,
            } as IDataRow['batchCluster'],
          }),
        );
      }
    });

    tableData.value = [...tableData.value.filter((item) => item.batchCluster.renderText), ...newList];
    window.changeConfirm = true;
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const newList = data.reduce<IDataRow[]>((acc, item) => {
      acc.push(
        createRowData({
          batchCluster: {
            renderText: item.master_domain?.replaceAll('\\n', '\n') || '',
          } as IDataRow['batchCluster'],
          db_version: item.version,
          target_spec_id: item.spec_name,
        }),
      );
      return acc;
    }, []);
    if (isClear) {
      tableData.value = [...newList];
    } else {
      tableData.value = [...tableData.value.filter((item) => item.batchCluster.renderText), ...newList];
    }
    setTimeout(() => {
      editableTableRef.value!.validate();
    }, 200);
  };

  defineExpose<Exposes>({
    getValue: () =>
      editableTableRef.value!.validate().then((validateResult) => {
        if (validateResult) {
          return tableData.value.map((tableItem) => {
            return {
              ...tableItem.instance_data,
              db_version: tableItem.db_version,
              migrate_domain: Object.values(tableItem.batchCluster.clusters)
                .map((item) => item.master_domain)
                .join(','),
              // migrate_ip: '',
              migrate_type: 'domain',
              resource_spec: {
                backend_group: {
                  count: 1,
                  spec_id: tableItem.target_spec_id,
                },
              },
            };
          });
        }
        return [];
      }),
    resetTable: () => {
      tableData.value = [createRowData()];
    },
  });
</script>
