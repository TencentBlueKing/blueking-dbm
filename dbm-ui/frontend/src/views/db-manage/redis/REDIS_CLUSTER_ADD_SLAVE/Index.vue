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
  <SmartAction>
    <div class="pb-20">
      <BkAlert
        closable
        theme="info"
        :title="
          t('重建从库：通过整机替换来实现从库实例的重建，即对应主机上的所有从库实例均会被重建，理论上不影响业务')
        " />
      <DbForm
        ref="form"
        class="toolbox-form"
        form-type="vertical"
        :model="formData"
        style="margin-top: 16px">
        <EditableTable
          ref="editableTable"
          class="mt16 mb16"
          :model="formData.tableData">
          <EditableRow
            v-for="(item, index) in formData.tableData"
            :key="index">
            <HostColumn
              v-model="item.host"
              :after-input="(data: RedisMachineModel) => afterInput(data, index)"
              :cluster-types="[ClusterTypes.REDIS]"
              :label="t('待重建从库主机')"
              :selected="selected"
              :tab-list-config="tabListConfig"
              @batch-edit="handleBatchEdit" />
            <EditableColumn
              :label="t('关联主库主机')"
              :width="200">
              <EditableBlock :placeholder="t('输入主机后自动生成')">
                {{ item.host.ip && slaveMasterMap[item.host.ip] ? slaveMasterMap[item.host.ip].ip : '' }}
              </EditableBlock>
            </EditableColumn>
            <EditableColumn
              :label="t('所属集群')"
              :min-width="200">
              <EditableBlock :placeholder="t('输入主机后自动生成')">
                <div
                  v-for="(relatedClusterItem, relatedClusterIndex) in item.host.related_clusters"
                  :key="relatedClusterIndex">
                  {{ relatedClusterItem.immute_domain }}
                </div>
              </EditableBlock>
            </EditableColumn>
            <SpecColumn v-model="item.host.spec_config" />
            <EditableColumn
              :label="t('故障从库实例数量')"
              :width="150">
              <EditableBlock :placeholder="t('输入主机后自动生成')">
                {{
                  item.host.related_instances.filter((relatedInstance) => relatedInstance.status === 'unavailable')
                    .length
                }}
              </EditableBlock>
            </EditableColumn>
            <!-- <EditableColumn
              :label="t('当前从库实例数量')"
              :width="150">
              <EditableBlock :placeholder="t('输入主机后自动生成')">
                {{ item.host.related_instances.length }}
              </EditableBlock>
            </EditableColumn> -->
            <OperationColumn
              :create-row-method="createRowData"
              :table-data="formData.tableData" />
          </EditableRow>
        </EditableTable>
        <TicketPayload v-model="formData.payload" />
      </DbForm>
    </div>
    <template #action>
      <BkButton
        class="w-88"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <DbPopconfirm
        :confirm-handler="handleReset"
        :content="t('重置将会清空当前填写的所有内容_请谨慎操作')"
        :title="t('确认重置页面')">
        <BkButton
          class="ml-8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>

<script setup lang="tsx">
  import { Message } from 'bkui-vue';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';
  import RedisMachineModel from '@services/model/redis/redis-machine';
  import { type Redis } from '@services/model/ticket/ticket';
  import { getRedisMachineList } from '@services/source/redis';
  import { listClustersCreateSlaveProxy, queryMasterSlavePairs } from '@services/source/redisToolbox';
  import type { MachineRelatedCluster, MachineSpecConfig } from '@services/types';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import { type IValue, type PanelListType } from '@components/instance-selector/Index.vue';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import HostColumn from '@views/db-manage/redis/common/toolbox-field/host-column/Index.vue';

  import SpecColumn from './components/SpecColumn.vue';

  interface IDataRow {
    host: {
      bk_host_id: number;
      ip: string;
      related_clusters: MachineRelatedCluster[];
      related_instances: {
        status: string;
      }[];
      spec_config: MachineSpecConfig;
    };
    // rowspan: number;
  }

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    host: Object.assign(
      {
        bk_host_id: 0,
        ip: '',
        related_clusters: [] as MachineRelatedCluster[],
        related_instances: [] as IDataRow['host']['related_instances'],
        spec_config: {} as MachineSpecConfig,
      },
      values.host,
    ),
    // rowspan: values?.rowspan || 1,
  });

  const createDefaultFormData = () => ({
    payload: createTickePayload(),
    tableData: [createRowData()],
  });

  const { t } = useI18n();

  useTicketDetail<Redis.ClusterAddSlave>(TicketTypes.REDIS_CLUSTER_ADD_SLAVE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { infos } = details;
      Object.assign(formData, {
        payload: createTickePayload(ticketDetail),
        tableData: infos.flatMap((infoItem) =>
          infoItem.pairs.map((pairItem) =>
            createRowData({
              host: {
                ip: pairItem.redis_slave.old_slave_ip,
              } as IDataRow['host'],
            }),
          ),
        ),
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      bk_cloud_id: number;
      cluster_ids: number[];
      pairs: {
        redis_master: {
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        };
        redis_slave: {
          count: number;
          old_slave_ip: string;
          spec_id: number;
        };
      }[];
    }[];
    ip_source: string;
  }>(TicketTypes.REDIS_CLUSTER_ADD_SLAVE);

  const editableTableRef = useTemplateRef('editableTable');

  const tabListConfig = {
    [ClusterTypes.REDIS]: [
      {
        id: 'redis',
        name: t('待重建的主机'),
        tableConfig: {
          columnsChecked: ['ip', 'role', 'cloud_area', 'status', 'host_name'],
          firsrColumn: {
            field: 'ip',
            label: 'IP',
            role: 'redis_slave',
          },
          getTableList: (params: any) =>
            getRedisMachineList({
              ...params,
              instance_status: 'unavailable',
              limit: -1,
            }),
          isRemotePagination: false,
          statusFilter: (data: RedisMachineModel) => !data.isSlaveFailover,
          // disabledRowConfig: {
          //   handler: (data: RedisMachineModel) => data.running_slave !== 0,
          //   tip: t('已存在正常运行的从库'),
          // },
        },
        topoConfig: {
          countFunc: (item: RedisModel) => item.redisSlaveFaults,
          getTopoList: listClustersCreateSlaveProxy,
          topoAlertContent: (
            <bk-alert
              style='margin-bottom: 12px;'
              theme='info'
              title={t('仅支持从库有故障的集群新建从库')}
              closable
            />
          ),
          totalCountFunc: (list: RedisModel[]) =>
            list.reduce((prevCount, listItem) => prevCount + listItem.redisSlaveFaults, 0),
        },
      },
      {
        manualConfig: {
          activePanelId: 'redis',
        },
        tableConfig: {
          columnsChecked: ['ip', 'role', 'cloud_area', 'status', 'host_name'],
          getTableList: (params: any) =>
            getRedisMachineList({
              ...params,
              instance_status: 'unavailable',
              limit: -1,
            }),
          isRemotePagination: false,
          statusFilter: (data: RedisMachineModel) => !data.isMasterFailover,
        },
      },
    ],
  } as unknown as Record<ClusterTypes, PanelListType>;

  // slave -> master
  const slaveMasterMap = shallowRef<Record<string, ServiceReturnType<typeof queryMasterSlavePairs>[number]['masters']>>(
    {},
  );

  const formData = reactive(createDefaultFormData());

  const selected = computed(() => formData.tableData.filter((item) => item.host.bk_host_id).map((item) => item.host));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  // watch(
  //   () => formData.tableData.length,
  //   () => {
  //     sortTableByCluster();
  //   },
  // );

  // 更新slave -> master 映射表
  const updateSlaveMasterMap = async (clusterIds: number[]) => {
    const retArr = await Promise.all(
      clusterIds.map((id) =>
        queryMasterSlavePairs({
          cluster_id: id,
        }),
      ),
    );
    retArr.forEach((pairs) => {
      if (pairs !== null) {
        pairs.forEach((item) => {
          slaveMasterMap.value[item.slave_ip] = item.masters;
        });
      }
    });
  };

  const afterInput = async (data: RedisMachineModel, index: number) => {
    const clusterIds = data.related_clusters.map((item) => item.id);
    await updateSlaveMasterMap(clusterIds);
    if (data.isSlaveFailover) {
      formData.tableData[index].host = data;
      // sortTableByCluster();
    } else {
      Message({
        message: t('无异常slave实例，无法重建'),
        theme: 'warning',
      });
    }
  };

  // 批量选择
  const handleBatchEdit = async (list: IValue[]) => {
    // 已选的主机信息
    const machineIpMap = list.reduce(
      (results, item) => {
        Object.assign(results, {
          [item.ip]: item,
        });
        return results;
      },
      {} as Record<string, RedisMachineModel>,
    );

    const clusterIds = [
      ...new Set(
        _.flatMap(Object.values(machineIpMap).map((item) => item.related_clusters.map((cluster) => cluster.id))),
      ),
    ];

    await updateSlaveMasterMap(clusterIds);

    const newList: IDataRow[] = [];
    list.forEach((item) => {
      const { ip } = item;
      if (!selectedMap.value[ip] && machineIpMap[ip].isSlaveFailover) {
        newList.push(
          createRowData({
            host: {
              bk_host_id: item.bk_host_id,
              ip: item.ip,
              related_clusters: machineIpMap[item.ip].related_clusters,
              related_instances: machineIpMap[item.ip].related_instances,
              spec_config: machineIpMap[item.ip].spec_config,
            },
          }),
        );
      }
    });
    if (newList.length) {
      formData.tableData = [...(selected.value.length ? formData.tableData : []), ...newList];
      window.changeConfirm = true;
    }
  };

  // 表格排序，方便合并集群显示
  // const sortTableByCluster = () => {
  //   const clusterMap: Record<string, IDataRow[]> = {};
  //   const emptyRowList: IDataRow[] = [];
  //   formData.tableData.forEach((item) => {
  //     Object.assign(item, { rowspan: 1 });
  //     const domain = item.host.related_clusters.map((clusterItem) => clusterItem.immute_domain).join(',');
  //     if (!domain) {
  //       emptyRowList.push(item);
  //       return;
  //     }
  //     if (!clusterMap[domain]) {
  //       clusterMap[domain] = [item];
  //     } else {
  //       clusterMap[domain].push(item);
  //     }
  //   });

  //   const sortedList: IDataRow[] = [];
  //   Object.values(clusterMap).forEach((list) => {
  //     Object.assign(list[0], { rowspan: list.length });
  //     sortedList.push(...list);
  //   });

  //   return [...sortedList, ...emptyRowList];
  // };

  // 根据表格数据生成提交单据请求参数
  const generateRequestParam = () => {
    const clusterMap: Record<string, IDataRow[]> = {};
    formData.tableData.forEach((tableItem) => {
      const clusterName = tableItem.host.related_clusters
        .map((relatedClusterItem) => relatedClusterItem.immute_domain)
        .join(',');
      if (!clusterMap[clusterName]) {
        clusterMap[clusterName] = [tableItem];
      } else {
        clusterMap[clusterName].push(tableItem);
      }
    });
    const keys = Object.keys(clusterMap);
    const infos = keys.map((domain) => {
      const sameArr = clusterMap[domain];
      const clusterIds = sameArr[0].host.related_clusters.map((item) => item.id);
      const { bk_cloud_id: bkCloudId, bk_host_id: bkHostId, ip: masterIp } = slaveMasterMap.value[sameArr[0].host.ip];
      const infoItem = {
        bk_cloud_id: bkCloudId,
        cluster_ids: clusterIds,
        pairs: [] as {
          redis_master: {
            bk_cloud_id: number;
            bk_host_id: number;
            ip: string;
          };
          redis_slave: {
            count: number;
            old_slave_ip: string;
            spec_id: number;
          };
        }[],
      };
      sameArr.forEach((item) => {
        const pair = {
          redis_master: {
            bk_cloud_id: bkCloudId,
            bk_host_id: bkHostId,
            ip: masterIp,
          },
          redis_slave: {
            count: 1,
            old_slave_ip: item.host.ip,
            spec_id: item.host.spec_config.id,
          },
        };
        infoItem.pairs.push(pair);
      });
      return infoItem;
    });
    return infos;
  };

  const handleSubmit = async () => {
    const validateResult = await editableTableRef.value!.validate();
    if (validateResult) {
      createTicketRun({
        details: {
          infos: generateRequestParam(),
          ip_source: 'resource_pool',
        },
        ...formData.payload,
      });
    }
  };

  // 重置
  const handleReset = () => {
    Object.assign(formData, createDefaultFormData());
    window.changeConfirm = false;
  };
</script>
