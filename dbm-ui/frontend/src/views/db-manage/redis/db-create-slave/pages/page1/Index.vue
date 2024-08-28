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
    <div class="master-slave-cutoff-page">
      <BkAlert
        closable
        theme="info"
        :title="
          t('重建从库：通过整机替换来实现从库实例的重建，即对应主机上的所有从库实例均会被重建，理论上不影响业务')
        " />
      <RenderData
        class="mt16"
        @show-master-batch-selector="handleShowMasterBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :data="item"
          :inputed-ips="inputedIps"
          :removeable="tableData.length < 2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @clone="(payload: IDataRow) => handleClone(index, payload)"
          @on-ip-input-finish="(ip: string) => handleChangeHostIp(index, ip)"
          @remove="handleRemove(index)" />
      </RenderData>
      <TicketRemark v-model="remark" />
      <InstanceSelector
        v-model:is-show="isShowMasterInstanceSelector"
        :cluster-types="[ClusterTypes.REDIS]"
        :selected="selected"
        :tab-list-config="tabListConfig"
        @change="handelMasterProxyChange" />
    </div>
    <template #action>
      <BkButton
        class="w-88"
        :disabled="totalNum === 0"
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
  import {  Message } from 'bkui-vue';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { getRedisMachineList } from '@services/source/redis';
  import {
    listClustersCreateSlaveProxy,
    queryMasterSlavePairs,
  } from '@services/source/redisToolbox';
  import { createTicket } from '@services/source/ticket';

  import { useTicketCloneInfo } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';
  import TicketRemark from '@components/ticket-remark/Index.vue';

  import RenderData from './components/Index.vue';
  import RenderDataRow, {
    createRowData,
    type IDataRow,
  } from './components/Row.vue';

  interface InfoItem {
    cluster_ids: number[],
    bk_cloud_id: number,
    pairs: {
      redis_master: {
        ip: string,
        bk_cloud_id: number,
        bk_host_id: number,
      },
      redis_slave: {
        spec_id: number,
        count: number,
        old_slave_ip: string;
      }
    }[]
  }

  type RedisModel = ServiceReturnType<typeof listClustersCreateSlaveProxy>[number]
  type RedisHostModel = ServiceReturnType<typeof getRedisMachineList>['results'][number]
  type MachineInstancePairItem = ServiceReturnType<typeof queryMasterSlavePairs>[number]['masters']

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const router = useRouter();

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.REDIS_CLUSTER_ADD_SLAVE,
    onSuccess(cloneData) {
      tableData.value = cloneData.tableDataList;
      remark.value = cloneData.remark
      window.changeConfirm = true;
    }
  });

  const rowRefs = ref();
  const isShowMasterInstanceSelector = ref(false);
  const isSubmitting  = ref(false);
  const tableData = ref([createRowData()]);
  const remark = ref('')

  const selected = shallowRef({ redis: [] } as InstanceSelectorValues<IValue>);

  const totalNum = computed(() => tableData.value.filter(item => Boolean(item.slaveIp)).length);
  const inputedIps = computed(() => tableData.value.map(item => item.slaveIp));

  // slave -> master
  const slaveMasterMap: Record<string, MachineInstancePairItem> = {};

  const tabListConfig = {
    [ClusterTypes.REDIS]: [
      {
        id: 'redis',
        name: t('待重建的主机'),
        topoConfig: {
          getTopoList: listClustersCreateSlaveProxy,
          countFunc: (item: RedisModel) => item.redisSlaveFaults,
          topoAlertContent: <bk-alert closable style="margin-bottom: 12px;" theme="info" title={t('仅支持从库有故障的集群新建从库')} />,
        },
        tableConfig: {
          getTableList: (params: any) => getRedisMachineList({
            ...params,
            instance_status: 'unavailable',
            limit: -1,
          }),
          firsrColumn: {
            label: 'IP',
            role: 'redis_slave',
            field: 'ip',
          },
          isRemotePagination: false,
          columnsChecked: ['ip', 'role', 'cloud_area', 'status', 'host_name'],
          statusFilter: (data: RedisHostModel) => !data.isSlaveFailover,
          // disabledRowConfig: {
          //   handler: (data: RedisHostModel) => data.running_slave !== 0,
          //   tip: t('已存在正常运行的从库'),
          // },
        },
      },
      {
        tableConfig: {
          getTableList: (params: any) => getRedisMachineList({
            ...params,
            instance_status: 'unavailable',
            limit: -1,
          }),
          isRemotePagination: false,
          columnsChecked: ['ip', 'role', 'cloud_area', 'status', 'host_name'],
          statusFilter: (data: RedisHostModel) => !data.isMasterFailover,
        },
        manualConfig: {
          activePanelId: 'redis',
        },
      },
    ],
  } as unknown as Record<ClusterTypes, PanelListType>;

  // 检测列表是否为空
  const checkListEmpty = (list: IDataRow[]) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.slaveIp;
  };

  // 更新slave -> master 映射表
  const updateSlaveMasterMap = async (ids?: number[]) => {
    const clusterIds = ids ? ids : [...new Set(_.flatMap(tableData.value.map(item => item.clusterIds)))];
    const retArr = await Promise.all(clusterIds.map(id => queryMasterSlavePairs({
      cluster_id: id,
    })));
    retArr.forEach((pairs) => {
      if (pairs !== null) {
        pairs.forEach((item) => {
          slaveMasterMap[item.slave_ip] = item.masters;
        });
      }
    });
  };

  // Master 批量选择
  const handleShowMasterBatchSelector = () => {
    isShowMasterInstanceSelector.value = true;
  };

  // ip 是否已存在表格的映射表
  let ipMemo: Record<string, boolean> = {};

  // 批量选择
  const handelMasterProxyChange = async (data: InstanceSelectorValues<IValue>) => {
    selected.value = data;
    const newList: IDataRow[] = [];
    const ips = data.redis.map(item => item.ip);
    const listResult = await getRedisMachineList({
      ip: ips.join(','),
      add_role_count: true,
    });

    const machineIpMap = listResult.results.reduce((results, item) => {
      Object.assign(results, {
        [item.ip]: item
      });
      return results;
    }, {} as Record<string, ServiceReturnType<typeof getRedisMachineList>['results'][number]>);

    const clusterIds = [...new Set(_.flatMap(Object.values(machineIpMap).map(item => item.related_clusters.map(cluster => cluster.id))))];

    await updateSlaveMasterMap(clusterIds);

    data.redis.forEach((item) => {
      const { ip } = item;
      if (!ipMemo[ip] && machineIpMap[ip].isSlaveFailover) {
        newList.push({
          rowKey: ip,
          isLoading: false,
          slaveIp: ip,
          masterIp: slaveMasterMap[item.ip].ip,
          clusterIds: machineIpMap[item.ip].related_clusters.map(item => item.id),
          bkCloudId: slaveMasterMap[item.ip].bk_cloud_id,
          bkHostId: slaveMasterMap[item.ip].bk_host_id,
          cluster: {
            domain: machineIpMap[item.ip].related_clusters.map(item => item.immute_domain).join(','),
            isStart: false,
            isGeneral: true,
            rowSpan: 1,
          },
          spec: machineIpMap[item.ip].spec_config,
          targetNum: 1,
          slaveHost: {
            faults: machineIpMap[item.ip].related_instances.filter(item => item.status === 'unavailable').length,
            total: machineIpMap[item.ip].related_instances.length,
          },
        });
        ipMemo[ip] = true;
      }
    });
    if (checkListEmpty(tableData.value)) {
      if (newList.length > 0) {
        tableData.value = newList;
      };
    } else {
      tableData.value = [...tableData.value, ...newList];
    }
    sortTableByCluster();
    // updateSlaveMasterMap();
    window.changeConfirm = true;
  };

  // 输入IP后查询详细信息
  const handleChangeHostIp = async (index: number, ip: string) => {
    if (!ip) {
      const { slaveIp } = tableData.value[index];
      ipMemo[slaveIp] = false;
      tableData.value[index].slaveIp = '';
      return;
    }
    tableData.value[index].isLoading = true;
    tableData.value[index].slaveIp = ip;
    const listResult = await getRedisMachineList({
      ip,
      add_role_count: true,
    }).finally(() => {
      tableData.value[index].isLoading = false;
    });

    if (listResult.results.length === 0) {
      return;
    }

    const data = listResult.results[0];

    const clusterIds = data.related_clusters.map(item => item.id);

    await updateSlaveMasterMap(clusterIds);
    if (data.isSlaveFailover) {
      const obj = {
        rowKey: tableData.value[index].rowKey,
        isLoading: false,
        slaveIp: ip,
        masterIp: slaveMasterMap[ip].ip,
        clusterIds,
        bkCloudId: slaveMasterMap[ip].bk_cloud_id,
        bkHostId: slaveMasterMap[ip].bk_host_id,
        cluster: {
          domain: data.related_clusters.map(item => item.immute_domain).join(','),
          isStart: false,
          isGeneral: true,
          rowSpan: 1,
        },
        spec: data.spec_config,
        targetNum: 1,
        slaveHost: {
          faults: data.related_instances.filter(item => item.status === 'unavailable').length,
          total: data.related_instances.length,
        },
      };
      tableData.value[index] = obj;
      ipMemo[ip]  = true;
      sortTableByCluster();
    } else {
      tableData.value[index].slaveIp = '';
      Message({
        theme: 'warning',
        message: t('无异常slave实例，无法重建'),
      });
    }
  };

  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    tableData.value.splice(index + 1, 0, ...appendList);
    sortTableByCluster();
  };

  // 删除一个集群
  const handleRemove = (index: number) => {
    const removeItem = tableData.value[index];
    const removeIp = removeItem.slaveIp;
    tableData.value.splice(index, 1);
    delete ipMemo[removeIp];
    sortTableByCluster();
    const arr = selected.value.redis;
    selected.value.redis = arr.filter(item => item.ip !== removeIp);
  };

  // 复制行数据
  const handleClone = (index: number, sourceData: IDataRow) => {
    const dataList = [...tableData.value];
    dataList.splice(index + 1, 0, sourceData);
    tableData.value = dataList;
    setTimeout(() => {
      rowRefs.value[rowRefs.value.length - 1].getValue();
    });
  };

  // 根据表格数据生成提交单据请求参数
  const generateRequestParam = () => {
    const clusterMap: Record<string, IDataRow[]> = {};
    tableData.value.forEach((item) => {
      if (item.slaveIp) {
        const clusterName = item.cluster.domain;
        if (!clusterMap[clusterName]) {
          clusterMap[clusterName] = [item];
        } else {
          clusterMap[clusterName].push(item);
        }
      }
    });
    const keys = Object.keys(clusterMap);
    const infos = keys.map((domain) => {
      const sameArr = clusterMap[domain];
      const infoItem: InfoItem = {
        cluster_ids: sameArr[0].clusterIds,
        bk_cloud_id: sameArr[0].bkCloudId,
        pairs: [],
      };
      const specId = sameArr[0].spec?.id;
      if (specId !== undefined) {
        sameArr.forEach((item) => {
          const pair = {
            redis_master: {
              ip: item.masterIp,
              bk_cloud_id: sameArr[0].bkCloudId,
              bk_host_id: sameArr[0].bkHostId,
            },
            redis_slave: {
              spec_id: specId,
              count: 1,
              old_slave_ip: item.slaveIp,
            },
          };
          infoItem.pairs.push(pair);
        });
      }
      return infoItem;
    });
    return infos;
  };

  // 提交
  const handleSubmit = async () => {
    try {
      isSubmitting.value = true;
      await Promise.all(rowRefs.value.map((item: { getValue: () => void }) => item.getValue()));

      const infos = generateRequestParam();
      const params = {
        bk_biz_id: currentBizId,
        ticket_type: TicketTypes.REDIS_CLUSTER_ADD_SLAVE,
        remark: remark.value,
        details: {
          ip_source: 'resource_pool',
          infos,
        },
      };
      await createTicket(params).then((data) => {
        window.changeConfirm = false;
        router.push({
          name: 'RedisDBCreateSlave',
          params: {
            page: 'success',
          },
          query: {
            ticketId: data.id,
          },
        });
      })
    } finally {
      isSubmitting.value = false;
    }
  };

  // 重置
  const handleReset = () => {
    tableData.value = [createRowData()];
    remark.value = ''
    selected.value.redis = [];
    ipMemo = {};
    window.changeConfirm = false;
  };

  // 表格排序，方便合并集群显示
  const sortTableByCluster = () => {
    const arr = tableData.value;
    const clusterMap: Record<string, IDataRow[]> = {};
    arr.forEach((item) => {
      const { domain } = item.cluster;
      if (!clusterMap[domain]) {
        clusterMap[domain] = [item];
      } else {
        clusterMap[domain].push(item);
      }
    });
    const keys = Object.keys(clusterMap);
    const retArr = [];
    for (const key of keys) {
      const sameArr = clusterMap[key];
      let isFirst = true;
      let isGeneral = true;
      if (sameArr.length > 1) {
        isGeneral  = false;
      }
      for (const item of sameArr) {
        if (isFirst) {
          item.cluster.isStart = true;
          item.cluster.rowSpan = sameArr.length;
          isFirst = false;
        } else {
          item.cluster.isStart = false;
        }
        item.cluster.isGeneral = isGeneral;
        retArr.push(item);
      }
    }
    tableData.value = retArr;
  };
</script>

<style lang="less">
  .master-slave-cutoff-page {
    padding-bottom: 20px;

    .page-action-box {
      display: flex;
      align-items: center;
      margin-top: 16px;
    }
  }
</style>
