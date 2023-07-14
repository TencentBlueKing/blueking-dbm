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
        :title="$t('新建从库：XXX')" />
      <RenderData
        class="mt16"
        @show-master-batch-selector="handleShowMasterBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :data="item"
          :removeable="tableData.length <2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @on-ip-input-finish="(ip: string) => handleChangeHostIp(index, ip)"
          @remove="handleRemove(index)" />
      </RenderData>
      <InstanceSelector
        v-model:is-show="isShowMasterInstanceSelector"
        active-tab="idleHosts"
        db-type="redis"
        :panel-list="['idleHosts', 'manualInput']"
        role="ip"
        @change="handelMasterProxyChange" />
    </div>
    <template #action>
      <BkButton
        class="w-88"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ $t('提交') }}
      </BkButton>
      <DbPopconfirm
        :confirm-handler="handleReset"
        :content="$t('重置将会情况当前填写的所有内容_请谨慎操作')"
        :title="$t('确认重置页面')">
        <BkButton
          class="ml8 w-88"
          :disabled="isSubmitting">
          {{ $t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import RedisClusterNodeByIpModel from '@services/model/redis/redis-cluster-node-by-ip';
  import { queryInfoByIp, queryMasterSlavePairs } from '@services/redis/toolbox';
  import { createTicket } from '@services/ticket';
  import type { SubmitTicket } from '@services/types/ticket';

  import { useGlobalBizs } from '@stores';

  import { TicketTypes } from '@common/const';

  import InstanceSelector, {
    type InstanceSelectorValues,
  } from '@views/redis/common/instance-selector/Index.vue';

  import RenderData from './components/Index.vue';
  import RenderDataRow, {
    createRowData,
    type IDataRow,
  } from './components/Row.vue';

  interface InfoItem {
    cluster_id: number,
    redis_masters: string[],
    resource_spec: {
      add_slave_hosts: {
        spec_id: number,
        count: number,
      }
    }
  }

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const router = useRouter();
  const rowRefs = ref();
  const isShowMasterInstanceSelector = ref(false);
  const isSubmitting  = ref(false);

  const tableData = ref<Array<IDataRow>>([createRowData()]);

  const totalNum = computed(() => tableData.value.filter(item => Boolean(item.ip)).length);


  // slave -> master
  const slaveMasterMap: Record<string, string> = {};

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
    }).catch((e) => {
      console.error('queryMasterSlavePairs error: ', e);
      return null;
    })));
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
    const newList: IDataRow[] = [];
    const ips = data.idleHosts.map(item => item.ip);
    const retArr = await queryInfoByIp({
      ips,
    });
    const infoMap: Record<string, RedisClusterNodeByIpModel> = {};
    retArr.forEach((item) => {
      infoMap[item.ip] = item;
    });
    data.idleHosts.forEach((item) => {
      const { ip } = item;
      if (!ipMemo[ip] && infoMap[ip].cluster.redis_slave_count === 0) {
        newList.push({
          rowKey: ip,
          isLoading: false,
          ip,
          clusterId: item.cluster_id,
          slaveNum: infoMap[ip].cluster.redis_slave_count,
          cluster: {
            domain: item.cluster_domain,
            isStart: false,
            isGeneral: true,
            rowSpan: 1,
          },
          spec: item.spec_config,
          targetNum: '1',
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
    if (tableData.value[index].ip === ip) return;
    // 去重
    if (tableData.value.filter(item => item.ip === ip).length > 0) return;
    tableData.value[index].isLoading = true;
    tableData.value[index].ip = ip;
    const ret = await queryInfoByIp({
      ips: [ip],
    });
    const data = ret[0];
    const obj: IDataRow = {
      rowKey: tableData.value[index].rowKey,
      isLoading: false,
      ip,
      clusterId: data.cluster.id,
      slaveNum: data.cluster.redis_slave_count,
      cluster: {
        domain: data.cluster?.immute_domain,
        isStart: false,
        isGeneral: true,
        rowSpan: 1,
      },
      spec: data.spec_config,
      targetNum: '1',
    };
    tableData.value[index] = obj;
    ipMemo[ip]  = true;
    sortTableByCluster();
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
        redis_masters: [],
        resource_spec: {
          add_slave_hosts: {
            spec_id: sameArr[0].spec?.id ?? 0,
            count: 1,
          },
        },
      };

      sameArr.forEach((item) => {
        infoItem.redis_masters.push(item.ip);
      });
      return infoItem;
    });
    return infos;
  };

  // 提交
  const handleSubmit = () => {
    const infos = generateRequestParam();
    const params: SubmitTicket<TicketTypes, InfoItem[]> = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.ADD_SLAVE,
      details: {
        ip_source: 'resource_pool',
        infos,
      },
    };
    console.log('submit params: ', params);
    InfoBox({
      title: t('确认新建n台从库主机？', { n: totalNum.value }),
      subTitle: t('请谨慎操作！'),
      width: 480,
      infoType: 'warning',
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
            console.error('单据提交失败：', e);
            // 暂时先按成功处理
            window.changeConfirm = false;
            router.push({
              name: 'RedisDBCreateSlave',
              params: {
                page: 'success',
              },
              query: {
                ticketId: '',
              },
            });
          })
          .finally(() => {
            isSubmitting.value = false;
          });
      } });
  };

  // 重置
  const handleReset = () => {
    tableData.value = [createRowData()];
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
