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
        :title="t('整机替换：将原主机上的所有实例搬迁到同等规格的新主机')" />
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
    <InstanceSelector
      v-model:is-show="isShowMasterInstanceSelector"
      active-tab="idleHosts"
      db-type="redis"
      :panel-list="['idleHosts', 'manualInput']"
      role="ip"
      :selected="selected"
      @change="handelMasterProxyChange" />
  </SmartAction>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { getRedisMachineList } from '@services/source/redis';
  import { queryMasterSlavePairs } from '@services/source/redisToolbox';
  import { createTicket } from '@services/source/ticket';

  import { useTicketCloneInfo } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import TicketRemark from '@components/ticket-remark/Index.vue';

  import { random } from '@utils';

  import RenderData from './components/Index.vue';
  import InstanceSelector, { type InstanceSelectorValues } from './components/instance-selector/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow } from './components/Row.vue';

  interface SpecItem {
    ip: string;
    spec_id: number;
  }

  interface InfoItem {
    cluster_ids: number[];
    bk_cloud_id: number;
    // cluster_domain: string;
    proxy: SpecItem[];
    redis_master: SpecItem[];
    redis_slave: SpecItem[];
    display_info: {
      data: {
        ip: string;
        role: string;
        cluster_domain: string;
        spec_id: number;
        spec_name: string;
      }[];
    };
  }

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const router = useRouter();

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.REDIS_CLUSTER_CUTOFF,
    onSuccess(cloneData) {
      tableData.value = cloneData.tableDataList;
      remark.value = cloneData.remark;
      sortTableByCluster();
      updateSlaveMasterMap();
      window.changeConfirm = true;
    },
  });

  const rowRefs = ref();
  const isShowMasterInstanceSelector = ref(false);
  const isSubmitting = ref(false);
  const tableData = ref([createRowData()]);
  const remark = ref('');

  const selected = shallowRef({
    idleHosts: [],
  } as InstanceSelectorValues);
  const totalNum = computed(() => tableData.value.filter((item) => Boolean(item.ip)).length);
  const inputedIps = computed(() => tableData.value.map((item) => item.ip));

  // ip 是否已存在表格的映射表
  let ipMemo = {} as Record<string, boolean>;
  // slave <-> master
  const slaveMasterMap: Record<string, string> = {};

  // Master 批量选择
  const handleShowMasterBatchSelector = () => {
    isShowMasterInstanceSelector.value = true;
  };

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length === 0) {
      return true;
    }
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.ip;
  };

  // 更新slave -> master 映射表
  const updateSlaveMasterMap = async () => {
    const clusterIds = [...new Set(_.flatMap(tableData.value.map((item) => item.clusterIds)))];
    const retArr = await Promise.all(
      clusterIds.map((id) =>
        queryMasterSlavePairs({
          cluster_id: id,
        }).catch(() => null),
      ),
    );
    retArr.forEach((pairs) => {
      if (pairs !== null) {
        pairs.forEach((item) => {
          slaveMasterMap[item.slave_ip] = item.master_ip;
          slaveMasterMap[item.master_ip] = item.slave_ip;
        });
      }
    });
  };

  // 表格排序，方便合并集群显示
  const sortTableByCluster = () => {
    const clusterMap = tableData.value.reduce<Record<string, IDataRow[]>>((acc, item) => {
      const { domain } = item.cluster;
      acc[domain] = acc[domain] || [];
      acc[domain].push(item);
      return acc;
    }, {});

    tableData.value = Object.values(clusterMap).flatMap((sameArr) => {
      const isGeneral = sameArr.length <= 1;
      return sameArr.map((item, index) => ({
        ...item,
        cluster: {
          ...item.cluster,
          isStart: index === 0,
          rowSpan: index === 0 ? sameArr.length : 1,
          isGeneral,
        },
      }));
    });
  };

  // 批量选择
  const handelMasterProxyChange = async (data: InstanceSelectorValues) => {
    selected.value = data;
    const dataList = data.idleHosts;
    const listResult = await getRedisMachineList({
      ip: dataList.map((item) => item.ip).join(','),
      add_role_count: true,
    });

    const machineIpMap = Object.fromEntries(listResult.results.map((item) => [item.ip, item]));

    const newList = dataList.reduce<IDataRow[]>((acc, item) => {
      const { ip } = item;
      if (!ipMemo[ip]) {
        acc.push({
          rowKey: random(),
          isLoading: false,
          ip,
          role: item.role,
          clusterIds: machineIpMap[ip].related_clusters.map((cluster) => cluster.id),
          bkCloudId: item.bk_cloud_id,
          cluster: {
            domain: machineIpMap[ip].related_clusters.map((cluster) => cluster.immute_domain).join(','),
            isStart: false,
            isGeneral: true,
            rowSpan: 1,
          },
          spec: item.spec_config,
        });
        ipMemo[ip] = true;
      }
      return acc;
    }, []);
    tableData.value = checkListEmpty(tableData.value) ? newList : [...tableData.value, ...newList];
    sortTableByCluster();
    updateSlaveMasterMap();
    window.changeConfirm = true;
  };

  // 输入IP后查询详细信息
  const handleChangeHostIp = async (index: number, ip: string) => {
    if (!ip) {
      const currentIp = tableData.value[index].ip;
      ipMemo[currentIp] = false;
      tableData.value[index].ip = '';
      return;
    }

    tableData.value[index].isLoading = true;
    tableData.value[index].ip = ip;

    try {
      const result = await getRedisMachineList({ ip, add_role_count: true });
      const data = result.results[0];
      const relatedClusters = data.related_clusters;
      const clusterDomain = relatedClusters.map((item) => item.immute_domain).join(',');

      const row: IDataRow = {
        rowKey: tableData.value[index].rowKey,
        isLoading: false,
        ip,
        role: data.instance_role,
        clusterIds: relatedClusters.map((item) => item.id),
        bkCloudId: data.bk_cloud_id,
        cluster: {
          domain: clusterDomain,
          isStart: false,
          isGeneral: true,
          rowSpan: 1,
        },
        spec: data.spec_config,
      };
      tableData.value[index] = row;

      const appendItem = {
        ip,
        bk_host_id: data.bk_host_id,
        bk_cloud_id: data.bk_cloud_id,
        role: data.instance_role,
        cluster_domain: clusterDomain,
        spec_config: data.spec_config,
      };
      selected.value.idleHosts.push(appendItem);
      ipMemo[ip] = true;
      sortTableByCluster();
      await updateSlaveMasterMap();

      if (data.instance_role === 'redis_master') {
        const slaveIp = slaveMasterMap[ip];
        const slaveClusterInfo = {
          role: 'redis_slave',
          ip: slaveIp,
        };
        tableData.value[index + 1] = {
          ...row,
          rowKey: random(),
          ...slaveClusterInfo,
        };
        selected.value.idleHosts.push({
          ...appendItem,
          ...slaveClusterInfo,
        });
        sortTableByCluster();
      }
    } finally {
      tableData.value[index].isLoading = false;
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
    let masterIp = '';
    // slave 与 master 删除联动
    if (removeItem.role === 'redis_slave') {
      masterIp = slaveMasterMap[removeItem.ip];
      if (masterIp) {
        // 看看表中有没有对应的master
        let masterIndex = -1;
        for (let i = 0; i < tableData.value.length; i++) {
          if (tableData.value[i].ip === masterIp) {
            masterIndex = i;
            break;
          }
        }
        if (masterIndex !== -1) {
          // 表格中存在master记录
          tableData.value.splice(masterIndex, 1);
          delete ipMemo[masterIp];
        }
      }
    }
    sortTableByCluster();
    const ipsArr = selected.value.idleHosts;
    selected.value.idleHosts = ipsArr.filter((item) => ![removeIp, masterIp].includes(item.ip));
    if (tableData.value.length === 0) {
      tableData.value = [createRowData()];
      return;
    }
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
    const clusterMap = tableData.value.reduce<Record<string, IDataRow[]>>((acc, item) => {
      if (item.ip) {
        const clusterName = item.cluster.domain;
        acc[clusterName] = acc[clusterName] || [];
        acc[clusterName].push(item);
      }
      return acc;
    }, {});
    const domains = Object.keys(clusterMap);
    const infos = domains.map((domain) => {
      const sameArr = clusterMap[domain];
      const infoItem: InfoItem = {
        // cluster_domain: domain,
        cluster_ids: sameArr[0].clusterIds,
        bk_cloud_id: sameArr[0].bkCloudId,
        proxy: [],
        redis_master: [],
        redis_slave: [],
        display_info: {
          data: [],
        },
      };
      const needDeleteSlaves: string[] = [];
      sameArr.forEach((item) => {
        const specObj = {
          ip: item.ip,
          spec_id: item.spec?.id ?? 0,
        };
        infoItem.display_info.data.push({
          ip: item.ip,
          role: item.role,
          cluster_domain: item.cluster.domain,
          spec_id: item.spec?.id ?? 0,
          spec_name: item.spec?.name ?? '',
        });
        if (item.role === 'redis_slave') {
          infoItem.redis_slave.push(specObj);
        } else if (item.role === 'redis_master') {
          infoItem.redis_master.push(specObj);
          const deleteSlaveIp = slaveMasterMap[item.ip];

          if (deleteSlaveIp) {
            needDeleteSlaves.push(deleteSlaveIp);
          }
        } else {
          infoItem.proxy.push(specObj);
        }
      });
      // 当选择了master的时候，对应的slave不要传给后端
      infoItem.redis_slave = infoItem.redis_slave.filter((item) => !needDeleteSlaves.includes(item.ip));
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
        ticket_type: TicketTypes.REDIS_CLUSTER_CUTOFF,
        remark: remark.value,
        details: {
          ip_source: 'resource_pool',
          infos,
        },
      };
      await createTicket(params).then((data) => {
        window.changeConfirm = false;
        router.push({
          name: 'RedisDBReplace',
          params: {
            page: 'success',
          },
          query: {
            ticketId: data.id,
          },
        });
      });
    } finally {
      isSubmitting.value = false;
    }
  };

  // 重置
  const handleReset = () => {
    tableData.value = [createRowData()];
    remark.value = '';
    selected.value.idleHosts = [];
    ipMemo = {};
    window.changeConfirm = false;
  };
</script>

<style lang="less" scoped>
  .master-slave-cutoff-page {
    padding-bottom: 20px;

    .page-action-box {
      display: flex;
      align-items: center;
      margin-top: 16px;
    }
  }
</style>
