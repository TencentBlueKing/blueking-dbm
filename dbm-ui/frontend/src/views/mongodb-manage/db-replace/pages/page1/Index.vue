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
    <div class="mongo-db-replace-page">
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
          :removeable="tableData.length < 2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @host-input-finish="(ip: string) => handleChangeHostIp(index, ip)"
          @remove="handleRemove(index)" />
      </RenderData>
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
    <InstanceSelector
      v-model:is-show="isShowMasterInstanceSelector"
      :cluster-types="[ClusterTypes.MONGOCLUSTER]"
      :selected="selected"
      @change="handleInstanceSelectChange" />
  </SmartAction>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import MongodbInstanceModel from '@services/model/mongodb/mongodb-instance';
  import { getMongoInstancesList } from '@services/source/mongodb';
  import { createTicket } from '@services/source/ticket';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import InstanceSelector, {
    type InstanceSelectorValues,
  } from '@components/instance-selector-new/Index.vue';

  import RenderData from './components/Index.vue';
  import RenderDataRow, {
    createRowData,
    type IDataRow,
  } from './components/Row.vue';

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const router = useRouter();
  const rowRefs = ref();
  const isShowMasterInstanceSelector = ref(false);
  const isSubmitting  = ref(false);

  const tableData = ref([createRowData()]);
  const selected = shallowRef({ [ClusterTypes.MONGOCLUSTER]: [] } as InstanceSelectorValues<MongodbInstanceModel>);

  const totalNum = computed(() => tableData.value.filter(item => Boolean(item.ip)).length);

  // ip 是否已存在表格的映射表
  let ipMemo = {} as Record<string, boolean>;

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

  // Master 批量选择
  const handleShowMasterBatchSelector = () => {
    isShowMasterInstanceSelector.value = true;
  };

  const generateRowDateFromRequest = (item: MongodbInstanceModel) => ({
    rowKey: item.ip,
    isLoading: false,
    ip: item.ip,
    role: item.role,
    relatedClusters: item.related_clusters.map(obj => obj.immute_domain),
    bkCloudId: item.bk_cloud_id,
    clusterId: item.cluster_id,
    clusterType: item.cluster_type,
    cluster: {
      domain: item.master_domain,
      isStart: false,
      isGeneral: true,
      rowSpan: 1,
    },
    currentSpec: item.spec_config,
    machineType: item.machine_type,
  });

  // 批量选择
  const handleInstanceSelectChange = (data: InstanceSelectorValues<MongodbInstanceModel>) => {
    selected.value = data;
    const newList: IDataRow[] = [];
    data[ClusterTypes.MONGOCLUSTER].forEach((item) => {
      const { ip } = item;
      if (!ipMemo[ip]) {
        newList.push(generateRowDateFromRequest(item));
        ipMemo[ip] = true;
      }
    });
    if (checkListEmpty(tableData.value)) {
      tableData.value = newList;
    } else {
      tableData.value = [...tableData.value, ...newList];
    }
    sortTableByCluster();
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
    const ret = await getMongoInstancesList({
      instance_address: ip,
      extra: 1,
    }).finally(() => {
      tableData.value[index].isLoading = false;
    });
    if (ret.results.length === 0) {
      return;
    }
    const data = ret.results[0];
    const obj = generateRowDateFromRequest(data);
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
    const ipsArr = selected.value[ClusterTypes.MONGOCLUSTER];
    selected.value[ClusterTypes.MONGOCLUSTER] = ipsArr.filter(item => item.ip !== removeIp);
  };

  // 根据表格数据生成提交单据请求参数
  const generateRequestParam = (ipSpecMap: Record<string, number>) => {
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
    const domains = Object.keys(clusterMap);
    const infos = domains.map((domain) => {
      const sameArr = clusterMap[domain];
      const infoItem = {
        cluster_id: sameArr[0].clusterId,
        mongos: [],
        mongodb: [],
        mongo_config: [],
      } as Record<string, any>;
      sameArr.forEach((item) => {
        const specObj = {
          ip: item.ip,
          spec_id: ipSpecMap[item.ip],
          bk_cloud_id: item.bkCloudId,
        };
        infoItem[item.machineType].push(specObj);
      });
      return infoItem;
    });
    return infos;
  };

  // 提交
  const handleSubmit = async () => {
    const ipSpecList = await Promise.all(rowRefs.value.map((item: {
      getValue: () => Promise<Record<string, number>>
    }) => item.getValue()));
    const ipSpecMap = ipSpecList.reduce((results, item) => Object.assign(results, item), {});
    const infos = generateRequestParam(ipSpecMap);
    const params = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.MONGODB_CUTOFF,
      details: {
        ip_source: 'resource_pool',
        infos,
      },
    };

    InfoBox({
      title: t('确认提交n个整机替换任务', { n: totalNum.value }),
      subTitle: t('信息将会被替换，请谨慎操作！'),
      width: 500,
      onConfirm: () => {
        isSubmitting.value = true;
        createTicket(params).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: 'MongoDBReplace',
            params: {
              page: 'success',
            },
            query: {
              ticketId: data.id,
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
    selected.value[ClusterTypes.MONGOCLUSTER] = [];
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

<style lang="less" scoped>
  .mongo-db-replace-page {
    padding-bottom: 20px;

    .page-action-box {
      display: flex;
      align-items: center;
      margin-top: 16px;
    }
  }
</style>
