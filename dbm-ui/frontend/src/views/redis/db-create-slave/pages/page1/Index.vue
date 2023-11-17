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
        :title="t('重建从库：通过整机替换来实现从库实例的重建，即对应主机上的所有从库实例均会被重建，理论上不影响业务')" />
      <RenderData
        class="mt16"
        @show-master-batch-selector="handleShowMasterBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :data="item"
          :inputed-ips="inputedIps"
          :removeable="tableData.length <2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @on-ip-input-finish="(ip: string) => handleChangeHostIp(index, ip)"
          @remove="handleRemove(index)" />
      </RenderData>
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
        :content="t('重置将会情况当前填写的所有内容_请谨慎操作')"
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
  import { InfoBox, Message } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import {
    listClusterHostsCreateSlaveProxy,
    listClustersCreateSlaveProxy,
  } from '@services/redis/toolbox';
  import {
    queryInfoByIp,
    queryMasterSlavePairs,
  } from '@services/source/redisToolbox';
  import { createTicket } from '@services/source/ticket';
  import type { SubmitTicket } from '@services/types/ticket';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type PanelListType,
  } from '@components/instance-selector-new/Index.vue';

  import RenderData from './components/Index.vue';
  import RenderDataRow, {
    createRowData,
    type IDataRow,
  } from './components/Row.vue';

  interface InfoItem {
    cluster_id: number,
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
      }
    }[]
  }

  type RedisModel = ServiceReturnType<typeof listClustersCreateSlaveProxy>[number]
  type RedisHostModel = ServiceReturnType<typeof listClusterHostsCreateSlaveProxy>['results'][number]
  type RedisClusterNodeByIpModel = ServiceReturnType<typeof queryInfoByIp>[number]


  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const router = useRouter();
  const rowRefs = ref();
  const isShowMasterInstanceSelector = ref(false);
  const isSubmitting  = ref(false);
  const tableData = ref([createRowData()]);
  const selected = shallowRef({ createSlaveIdleHosts: [] } as InstanceSelectorValues);
  const totalNum = computed(() => tableData.value.filter(item => Boolean(item.ip)).length);
  const inputedIps = computed(() => tableData.value.map(item => item.ip));

  // slave -> master
  const slaveMasterMap: Record<string, string> = {};

  const tabListConfig = {
    [ClusterTypes.REDIS]: [
      {
        id: 'createSlaveIdleHosts',
        name: t('主库故障主机'),
        topoConfig: {
          getTopoList: listClustersCreateSlaveProxy,
          countFunc: (item: RedisModel) => item.redisSlaveFaults,
          topoAlertContent: <bk-alert closable style="margin-bottom: 12px;" theme="info" title={t('仅支持从库有故障的集群新建从库')} />,
        },
        tableConfig: {
          getTableList: listClusterHostsCreateSlaveProxy,
          columnsChecked: ['ip', 'role', 'cloud_area', 'status', 'host_name'],
          statusFilter: (data: RedisHostModel) => !data.isSlaveFailover,
          disabledRowConfig: {
            handler: (data: RedisHostModel) => data.running_slave !== 0,
            tip: t('已存在正常运行的从库'),
          },
          roleFilterList: {
            list: [{ text: 'master', value: 'master' }, { text: 'slave', value: 'slave' }, { text: 'proxy', value: 'proxy' }],
          },
        },
      },
      {
        tableConfig: {
          getTableList: listClusterHostsCreateSlaveProxy,
          columnsChecked: ['ip', 'role', 'cloud_area', 'status', 'host_name'],
          statusFilter: (data: RedisHostModel) => !data.isMasterFailover,
        },
        manualConfig: {
          activePanelId: 'createSlaveIdleHosts',
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
    return !firstRow.ip;
  };

  // 更新slave -> master 映射表
  const updateSlaveMasterMap = async () => {
    const clusterIds = [...new Set(tableData.value.map(item => item.clusterId))];
    const retArr = await Promise.all(clusterIds.map(id => queryMasterSlavePairs({
      cluster_id: id,
    }).catch(() => null)));
    retArr.forEach((pairs) => {
      if (pairs !== null) {
        pairs.forEach((item) => {
          slaveMasterMap[item.slave_ip] = item.master_ip;
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
  const handelMasterProxyChange = async (data: InstanceSelectorValues) => {
    selected.value = data;
    const newList: IDataRow[] = [];
    const ips = data.createSlaveIdleHosts.map(item => item.ip);
    const retArr = await queryInfoByIp({ ips });
    const infoMap: Record<string, RedisClusterNodeByIpModel> = {};
    retArr.forEach((item) => {
      infoMap[item.ip] = item;
    });
    data.createSlaveIdleHosts.forEach((item) => {
      const { ip } = item;
      if (!ipMemo[ip] && infoMap[ip].isSlaveFailover) {
        newList.push({
          rowKey: ip,
          isLoading: false,
          ip,
          clusterId: item.cluster_id,
          bkCloudId: item.bk_cloud_id,
          bkHostId: item.bk_host_id,
          slaveNum: infoMap[ip].cluster.redis_slave_count,
          cluster: {
            domain: infoMap[item.ip].cluster.immute_domain,
            isStart: false,
            isGeneral: true,
            rowSpan: 1,
          },
          spec: infoMap[item.ip].spec_config,
          targetNum: 1,
          slaveHost: {
            faults: infoMap[item.ip].unavailable_slave,
            total: infoMap[item.ip].total_slave,
          },
        });
        ipMemo[ip] = true;
      }
    });
    if (checkListEmpty(tableData.value)) {
      if (newList.length > 0) tableData.value = newList;
    } else {
      tableData.value = [...tableData.value, ...newList];
    }
    sortTableByCluster();
    updateSlaveMasterMap();
    window.changeConfirm = true;
  };

  // 输入IP后查询详细信息
  const handleChangeHostIp = async (index: number, ip: string) => {
    if (!ip) {
      const { ip } = tableData.value[index];
      ipMemo[ip] = false;
      tableData.value[index].ip = '';
      return;
    }
    tableData.value[index].isLoading = true;
    tableData.value[index].ip = ip;
    const ret = await queryInfoByIp({ ips: [ip] }).finally(() => {
      tableData.value[index].isLoading = false;
    });
    if (ret.length === 0) {
      return;
    }
    const data = ret[0];
    if (data.isSlaveFailover) {
      const obj = {
        rowKey: tableData.value[index].rowKey,
        isLoading: false,
        ip,
        clusterId: data.cluster.id,
        bkCloudId: data.bk_cloud_id,
        bkHostId: data.bk_host_id,
        slaveNum: data.cluster.redis_slave_count,
        cluster: {
          domain: data.cluster?.immute_domain,
          isStart: false,
          isGeneral: true,
          rowSpan: 1,
        },
        spec: data.spec_config,
        targetNum: 1,
        slaveHost: {
          faults: data.unavailable_slave,
          total: data.total_slave,
        },
      };
      tableData.value[index] = obj;
      ipMemo[ip]  = true;
      sortTableByCluster();
      selected.value.createSlaveIdleHosts.push(Object.assign(data, {
        cluster_id: obj.clusterId,
        cluster_domain: data.cluster?.immute_domain,
        port: 0,
        instance_address: '',
        cluster_type: '',
      }));
    } else {
      tableData.value[index].ip = '';
      Message({
        theme: 'warning',
        message: t('已存在salve，无法创建从库'),
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
    const removeIp = removeItem.ip;
    tableData.value.splice(index, 1);
    delete ipMemo[removeIp];
    sortTableByCluster();
    const arr = selected.value.createSlaveIdleHosts;
    selected.value.createSlaveIdleHosts = arr.filter(item => item.ip !== removeIp);
  };

  // 根据表格数据生成提交单据请求参数
  const generateRequestParam = () => {
    const clusterMap: Record<string, IDataRow[]> = {};
    tableData.value.forEach((item) => {
      if (item.ip) {
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
        cluster_id: sameArr[0].clusterId,
        bk_cloud_id: sameArr[0].bkCloudId,
        pairs: [],
      };
      const specId = sameArr[0].spec?.id;
      if (specId !== undefined) {
        sameArr.forEach((item) => {
          const pair = {
            redis_master: {
              ip: item.ip,
              bk_cloud_id: sameArr[0].bkCloudId,
              bk_host_id: sameArr[0].bkHostId,
            },
            redis_slave: {
              spec_id: specId,
              count: 1,
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
    await Promise.all(rowRefs.value.map((item: {
      getValue: () => void
    }) => item.getValue()));
    const infos = generateRequestParam();
    const params: SubmitTicket<TicketTypes, InfoItem[]> = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.REDIS_CLUSTER_ADD_SLAVE,
      details: {
        ip_source: 'resource_pool',
        infos,
      },
    };

    InfoBox({
      title: t('确认新建n台从库主机？', { n: totalNum.value }),
      width: 480,
      onConfirm: () => {
        isSubmitting.value = true;
        createTicket(params).then((data) => {
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
          .catch((e) => {
            // 目前后台还未调通
            console.error('submit db create slave ticket error:', e);
          })
          .finally(() => {
            isSubmitting.value = false;
          });
      } });
  };

  // 重置
  const handleReset = () => {
    tableData.value = [createRowData()];
    selected.value.createSlaveIdleHosts = [];
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
