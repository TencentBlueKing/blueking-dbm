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
      <InstanceColumn
        v-model="item.instance"
        :after-input="(data: RedisInstanceModel) => afterInput(data, index)"
        :selected="selected"
        :tab-list-config="tabListConfig"
        @batch-edit="handleInstanceSelectChange" />
      <EditableColumn
        :label="t('所属集群')"
        :rowspan="item.rowspan"
        :width="200">
        <EditableBlock :placeholder="t('输入主机后自动生成')">
          {{ item.instance.master_domain }}
        </EditableBlock>
      </EditableColumn>
      <EditableColumn
        :label="t('规格')"
        :width="200">
        <EditableBlock :placeholder="t('输入主机后自动生成')">
          {{ item.instance.spec_config.id ? item.instance.spec_config.name : '' }}
        </EditableBlock>
      </EditableColumn>
      <CurrentVersionColumn
        v-model="item.current_versions"
        :cluster-id="item.instance.cluster_id" />
      <OperationColumn
        :create-row-method="createRowData"
        :table-data="tableData" />
    </EditableRow>
  </EditableTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';
  import RedisInstanceModel from '@services/model/redis/redis-instance';
  import TicketModel, { type Redis } from '@services/model/ticket/ticket';
  import { getRedisClusterList, getRedisInstances } from '@services/source/redis';
  import { queryMachineInstancePair } from '@services/source/redisToolbox';

  import { ClusterTypes } from '@common/const';

  import ManualInputHostContent from '@components/instance-selector/components/common/manual-content/Index.vue';
  import { type PanelListType } from '@components/instance-selector/Index.vue';

  import InstanceColumn from '@views/db-manage/redis/common/toolbox-field/instance-column/Index.vue';

  import CurrentVersionColumn from './components/CurrentVersionColumn.vue';

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
          instance: string;
          db_version: string[];
        };
      }[]
    >;
    setTableByTicketClone: (infos: TicketModel<Redis.MigrateCluster>) => void;
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
    instance: {
      id: number;
      instance_address: string;
      cluster_id: number;
      master_domain: string;
      spec_config: RedisInstanceModel['spec_config'];
    };
    master: IHostData;
    slave: IHostData;
    current_versions: string[];
    rowspan: number;
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    instance: Object.assign(
      {
        id: 0,
        instance_address: '',
        cluster_id: 0,
        master_domain: '',
        spec_config: {} as RedisInstanceModel['spec_config'],
      },
      values.instance,
    ),
    master: Object.assign(
      {
        bk_biz_id: 0,
        bk_cloud_id: 0,
        bk_host_id: 0,
        ip: '',
        port: 0,
      },
      values.master,
    ),
    slave: Object.assign(
      {
        bk_biz_id: 0,
        bk_cloud_id: 0,
        bk_host_id: 0,
        ip: '',
        port: 0,
      },
      values.slave,
    ),
    current_versions: values?.current_versions || [],
    rowspan: values?.rowspan || 1,
  });

  const { t } = useI18n();

  const editableTableRef = useTemplateRef('editableTable');

  const rules = {
    'instance.instance_address': [
      {
        validator: (value: string) => {
          if (value) {
            const hostList = tableData.value.filter((row) => row.instance.instance_address === value);
            return hostList.length === 1;
          }
          return true;
        },
        trigger: 'change',
        message: t('实例重复'),
      },
    ],
  };

  const tableData = ref([createRowData()]);

  const tabListConfig = computed(
    () =>
      ({
        [ClusterTypes.REDIS]: [
          {
            name: t('实例选择'),
            topoConfig: {
              getTopoList: (params: ServiceParameters<typeof getRedisClusterList>) =>
                getRedisClusterList({
                  cluster_type: [
                    ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
                    ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
                    ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
                    ClusterTypes.PREDIXY_REDIS_CLUSTER,
                  ].join(','),
                  ...params,
                }),
              countFunc: (data: RedisModel) => data.redis_master.length,
              totalCountFunc: (dataList: RedisModel[]) =>
                dataList.reduce<number>((prevCount, item) => prevCount + item.redis_master.length, 0),
            },
            tableConfig: {
              getTableList: (params: ServiceParameters<typeof getRedisInstances>) =>
                getRedisInstances({
                  cluster_type: [
                    ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
                    ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
                    ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
                    ClusterTypes.PREDIXY_REDIS_CLUSTER,
                  ].join(','),
                  role: 'redis_master',
                  ...params,
                }),
              multiple: true,
              firsrColumn: {
                label: t('Master 实例'),
                field: 'instance_address',
                role: '',
              },
              columnsChecked: ['instance_address', 'cloud_area', 'status', 'host_name', 'os_name'],
            },
            previewConfig: {
              displayKey: 'instance_address',
            },
          },
          {
            manualConfig: {
              checkType: 'instance',
              checkKey: 'instance_address',
              activePanelId: 'redis',
              fieldFormat: {
                role: {
                  master: 'redis_master',
                },
              },
            },
            tableConfig: {
              getTableList: (params: ServiceParameters<typeof getRedisInstances>) =>
                getRedisInstances({
                  cluster_type: [
                    ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
                    ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
                    ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
                    ClusterTypes.PREDIXY_REDIS_CLUSTER,
                  ].join(','),
                  ...params,
                }),
              firsrColumn: {
                label: t('Master 实例'),
                field: 'instance_address',
                role: 'redis_master',
              },
              multiple: true,
            },
            previewConfig: {
              displayKey: 'instance_address',
            },
            content: ManualInputHostContent,
          },
        ],
      }) as unknown as Record<ClusterTypes, PanelListType>,
  );

  const selected = computed(() =>
    tableData.value.reduce<IDataRow['instance'][]>((prev, item) => {
      if (item.instance.id) {
        return prev.concat(item.instance);
      }
      return prev;
    }, []),
  );
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.instance_address, true])));

  watch(
    () => tableData.value.length,
    () => {
      sortTableByCluster();
    },
  );

  // 表格排序，方便合并集群显示
  const sortTableByCluster = () => {
    const clusterMap: Record<string, IDataRow[]> = {};
    tableData.value.forEach((item) => {
      Object.assign(item, { rowspan: 1 });
      const domain = item.instance.master_domain;
      if (!domain) {
        return;
      }
      if (!clusterMap[domain]) {
        clusterMap[domain] = [item];
      } else {
        clusterMap[domain].push(item);
      }
    });

    const sortedList: IDataRow[] = [];
    Object.values(clusterMap).forEach((list) => {
      Object.assign(list[0], { rowspan: list.length });
      sortedList.push(...list);
    });
  };

  const getMasterSlaveInstaceMap = async (data: RedisInstanceModel[]) => {
    const slaveInstanceMap = await queryMachineInstancePair({
      instances: data.map((item) => item.instance_address),
    });

    if (slaveInstanceMap && slaveInstanceMap.instances) {
      const masterSlaveInstaceMap = data.reduce<
        Record<
          string,
          {
            master: IHostData;
            slave: IHostData;
          }
        >
      >(
        (prevMap, instanceItem) =>
          Object.assign({}, prevMap, {
            [instanceItem.instance_address]: {
              master: {
                bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
                bk_cloud_id: instanceItem.bk_cloud_id,
                bk_host_id: instanceItem.bk_host_id,
                ip: instanceItem.ip,
                port: instanceItem.port,
              },
            },
          }),
        {},
      );
      Object.keys(masterSlaveInstaceMap).forEach((masterInstance) => {
        const slaveItem = slaveInstanceMap.instances![masterInstance];
        masterSlaveInstaceMap[masterInstance].slave = {
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          bk_cloud_id: slaveItem.bk_cloud_id,
          bk_host_id: slaveItem.bk_host_id,
          ip: slaveItem.ip,
          port: slaveItem.port,
        };
      });

      return masterSlaveInstaceMap;
    }

    return {};
  };

  // 批量选择
  const handleInstanceSelectChange = async (data: RedisInstanceModel[]) => {
    const newList: IDataRow[] = [];
    const masterSlaveInstaceMap = await getMasterSlaveInstaceMap(data);
    data.forEach((item) => {
      const { instance_address: instance } = item;
      if (!selectedMap.value[instance]) {
        const { slave } = masterSlaveInstaceMap[item.instance_address];
        newList.push(
          createRowData({
            instance: {
              id: item.id,
              instance_address: item.instance_address,
              cluster_id: item.cluster_id,
              master_domain: item.master_domain,
              spec_config: item.spec_config,
            },
            master: {
              bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
              bk_cloud_id: item.bk_cloud_id,
              bk_host_id: item.bk_host_id,
              ip: item.ip,
              port: item.port,
            },
            slave: {
              bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
              bk_cloud_id: slave.bk_cloud_id,
              bk_host_id: slave.bk_host_id,
              ip: slave.ip,
              port: slave.port,
            },
          }),
        );
      }
    });
    tableData.value = [...(tableData.value[0].instance.instance_address ? tableData.value : []), ...newList];
    window.changeConfirm = true;
  };

  const afterInput = async (data: RedisInstanceModel, index: number) => {
    const masterSlaveInstaceMap = await getMasterSlaveInstaceMap([data]);
    const { instance_address: instance } = data;
    if (!selectedMap.value[instance]) {
      const { slave } = masterSlaveInstaceMap[data.instance_address];
      tableData.value[index] = createRowData({
        instance: {
          id: data.id,
          instance_address: data.instance_address,
          cluster_id: data.cluster_id,
          master_domain: data.master_domain,
          spec_config: data.spec_config,
        },
        master: {
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          bk_cloud_id: data.bk_cloud_id,
          bk_host_id: data.bk_host_id,
          ip: data.ip,
          port: data.port,
        },
        slave: {
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          bk_cloud_id: slave.bk_cloud_id,
          bk_host_id: slave.bk_host_id,
          ip: slave.ip,
          port: slave.port,
        },
      });
      sortTableByCluster();
    }
  };

  defineExpose<Exposes>({
    getValue: () =>
      editableTableRef.value!.validate().then((validateResult) => {
        if (validateResult) {
          return tableData.value.map((tableItem) => ({
            cluster_id: tableItem.instance.cluster_id,
            resource_spec: {
              backend_group: {
                spec_id: tableItem.instance.spec_config.id,
                count: 1,
              },
            },
            old_nodes: {
              master: [tableItem.master],
              slave: [tableItem.slave],
            },
            display_info: {
              instance: tableItem.instance.instance_address,
              db_version: tableItem.current_versions,
            },
          }));
        }
        return [];
      }),
    setTableByTicketClone: (ticketDetail: TicketModel<Redis.MigrateCluster>) => {
      const { infos } = ticketDetail.details;
      tableData.value = infos.map((infoItem) =>
        createRowData({
          instance: {
            instance_address: infoItem.display_info.instance,
          } as IDataRow['instance'],
          master: infoItem.old_nodes.master[0],
          slave: infoItem.old_nodes.slave[0],
        }),
      );
    },
    resetTable: () => {
      tableData.value = [createRowData()];
    },
  });
</script>
