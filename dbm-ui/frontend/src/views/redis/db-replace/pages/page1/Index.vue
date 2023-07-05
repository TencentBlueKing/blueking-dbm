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
        :title="$t('整机替换：XXX')" />
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
        class="w88"
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
          class="ml8 w88"
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

  interface SpecItem {
    ip: string;
    spec_id: number
  }
  interface InfoItem {
    cluster_id: number;
    cluster_domain: string;
    proxy: SpecItem[];
    redis_master: SpecItem[];
    redis_slave: SpecItem[];
  }

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const router = useRouter();
  const rowRefs = ref();
  const isShowMasterInstanceSelector = ref(false);
  const isSubmitting  = ref(false);

  const tableData = ref<Array<IDataRow>>([createRowData()]);

  const totalNum = computed(() => tableData.value.filter(item => item.ip !== undefined).length);


  // slave -> master
  const slaveMasterMap: Record<string, string> = {};

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return firstRow.ip;
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
  let ipMemo = {} as Record<string, boolean>;

  // 批量选择
  const handelMasterProxyChange = (data: InstanceSelectorValues) => {
    const newList = [] as IDataRow [];
    data.idleHosts.forEach((proxyData) => {
      const { ip } = proxyData;
      if (!ipMemo[ip]) {
        newList.push({
          rowKey: ip,
          isLoading: false,
          ip,
          role: proxyData.role,
          clusterId: proxyData.cluster_id,
          cluster: {
            domain: proxyData.cluster_domain,
            isStart: false,
            isGeneral: true,
            rowSpan: 1,
          },
          spec: proxyData.spec_config,
        });
        ipMemo[ip] = true;
      }
    });
    if (checkListEmpty(tableData.value)) {
      tableData.value = newList;
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
    }).catch((e) => {
      console.error('query cluster info by ip failed: ', e);
      return null;
    });
    if (ret) {
      const data = ret[0];
      const obj = {
        rowKey: tableData.value[index].rowKey,
        isLoading: false,
        ip,
        role: data.role,
        clusterId: data.cluster.id,
        cluster: {
          domain: data.cluster?.immute_domain,
          isStart: false,
          isGeneral: true,
          rowSpan: 1,
        },
        spec: data.spec,
      };
      tableData.value[index] = obj;
      ipMemo[ip]  = true;
      sortTableByCluster();
    }
  };

  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    const dataList = [...tableData.value];
    dataList.splice(index + 1, 0, ...appendList);
    tableData.value = dataList;
    sortTableByCluster();
  };

  // 删除一个集群
  const handleRemove = (index: number) => {
    const dataList = [...tableData.value];
    const removeItem = dataList[index];
    const removeIp = removeItem.ip;
    dataList.splice(index, 1);
    delete ipMemo[removeIp];

    // slave 与 master 删除联动
    if (removeItem.role === 'slave') {
      const masterIp = slaveMasterMap[removeItem.ip];
      if (masterIp) {
        // 看看表中有没有对应的master
        let masterIndex = -1;
        for (let i = 0; i < dataList.length; i++) {
          if (dataList[i].ip === masterIp) {
            masterIndex = i;
            break;
          }
        }
        if (masterIndex !== -1) {
          // 表格中存在master记录
          dataList.splice(masterIndex, 1);
          delete ipMemo[masterIp];
        }
      }
    }
    tableData.value = dataList;
    sortTableByCluster();
  };

  // 根据表格数据生成提交单据请求参数
  const generateRequestParam = () => {
    const clusterMap: Record<string, IDataRow[]> = {};
    const dataArr = tableData.value.filter(item => item.ip !== undefined);
    dataArr.forEach((item) => {
      const clusterName = item.cluster.domain;
      if (!clusterMap[clusterName]) {
        clusterMap[clusterName] = [item];
      } else {
        clusterMap[clusterName].push(item);
      }
    });
    const keys = Object.keys(clusterMap);
    const infos = keys.map((domain) => {
      const sameArr = clusterMap[domain];
      const infoItem: InfoItem = {
        cluster_domain: domain,
        cluster_id: sameArr[0].clusterId,
        proxy: [],
        redis_master: [],
        redis_slave: [],
      };

      sameArr.forEach((item) => {
        const specObj = {
          ip: item.ip,
          spec_id: item.spec?.id ?? 0,
        };
        if (item.role === 'slave') {
          infoItem.redis_slave.push(specObj);
        } else if (item.role === 'master') {
          infoItem.redis_master.push(specObj);
        } else {
          infoItem.proxy.push(specObj);
        }
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
      ticket_type: TicketTypes.REDIS_CLUSTER_SLAVE_CUTOFF,
      details: {
        ip_source: 'resource_pool',
        infos,
      },
    };
    InfoBox({
      title: t('确认整机替换n台主机？', { n: totalNum.value }),
      subTitle: '替换后所有的数据将会迁移到新的主机上，请谨慎操作！',
      width: 480,
      infoType: 'warning',
      onConfirm: () => {
        isSubmitting.value = true;
        createTicket(params).then((data) => {
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
        })
          .catch((e) => {
            // 目前后台还未调通
            console.error('单据提交失败：', e);
            // 暂时先按成功处理
            window.changeConfirm = false;
            router.push({
              name: 'RedisDBReplace',
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
