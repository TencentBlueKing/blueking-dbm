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
    <div class="proxy-scale-up-page">
      <BkAlert
        closable
        theme="info"
        :title="t('扩容接入层：增加集群的Proxy数量，新Proxy可以指定规格')" />
      <RenderData
        class="mt16"
        @show-batch-selector="handleShowBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :data="item"
          :inputed-clusters="inputedClusters"
          :removeable="tableData.length < 2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @clone="(payload: IDataRow) => handleClone(index, payload)"
          @cluster-input-finish="(domainObj: RedisModel) => handleChangeCluster(index, domainObj)"
          @remove="handleRemove(index)" />
      </RenderData>
      <TicketRemark v-model="remark" />
      <ClusterSelector
        v-model:is-show="isShowMasterInstanceSelector"
        :cluster-types="[ClusterTypes.REDIS]"
        :selected="selectedClusters"
        :tab-list-config="tabListConfig"
        @change="handelClusterChange" />
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
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import RedisModel from '@services/model/redis/redis';
  import { getRedisList } from '@services/source/redis';
  import { createTicket } from '@services/source/ticket';

  import { useTicketCloneInfo } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ClusterSelector from '@components/cluster-selector/Index.vue';
  import TicketRemark from '@components/ticket-remark/Index.vue';

  import RenderData from './components/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow, type InfoItem } from './components/Row.vue';

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const router = useRouter();

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.REDIS_PROXY_SCALE_UP,
    onSuccess(cloneData) {
      tableData.value = cloneData.tableDataList;
      remark.value = cloneData.remark;

      window.changeConfirm = true;
    },
  });

  const rowRefs = ref();
  const isShowMasterInstanceSelector = ref(false);
  const isSubmitting = ref(false);
  const tableData = ref([createRowData()]);
  const remark = ref('');

  const totalNum = computed(() => tableData.value.filter((item) => Boolean(item.cluster)).length);
  const inputedClusters = computed(() => tableData.value.map((item) => item.cluster));
  const selectedClusters = shallowRef<{ [key: string]: Array<RedisModel> }>({ [ClusterTypes.REDIS]: [] });

  const tabListConfig = {
    [ClusterTypes.REDIS]: {
      getResourceList: (params: ServiceParameters<typeof getRedisList>) =>
        getRedisList({
          cluster_type: [
            ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
            ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
            ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
            ClusterTypes.PREDIXY_REDIS_CLUSTER,
          ].join(','),
          ...params,
        }),
    },
  };

  // 集群域名是否已存在表格的映射表
  let domainMemo: Record<string, boolean> = {};

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.cluster;
  };

  // Master 批量选择
  const handleShowBatchSelector = () => {
    isShowMasterInstanceSelector.value = true;
  };

  // 根据集群选择返回的数据加工成table所需的数据
  const generateRowDateFromRequest = (item: RedisModel) => ({
    rowKey: item.master_domain,
    isLoading: false,
    cluster: item.master_domain,
    clusterId: item.id,
    bkCloudId: item.bk_cloud_id,
    clusterType: item.cluster_spec.spec_cluster_type,
    nodeType: 'Proxy',
    cluster_type_name: item.cluster_type_name,
    spec: {
      ...item.proxy[0].spec_config,
      name: item.cluster_spec.spec_name,
      id: item.proxy[0].spec_config.id,
      count: item.proxy.length,
    },
    targetNum: `${item.proxy.length}`,
    rowModelData: item,
  });
  // 批量选择
  const handelClusterChange = async (selected: { [key: string]: Array<RedisModel> }) => {
    selectedClusters.value = selected;
    const list = selected[ClusterTypes.REDIS];
    const newList: IDataRow[] = [];
    for (const item of list) {
      const domain = item.master_domain;
      if (!domainMemo[domain]) {
        const row = generateRowDateFromRequest(item);
        row.spec.count = item.proxy.length;
        newList.push(row);
        domainMemo[domain] = true;
      }
    }
    if (checkListEmpty(tableData.value)) {
      tableData.value = newList;
    } else {
      tableData.value = [...tableData.value, ...newList];
    }
    window.changeConfirm = true;
  };

  // 输入集群后查询集群信息并填充到table
  const handleChangeCluster = async (index: number, domainObj: RedisModel) => {
    // if (!domain) {
    //   const { cluster } = tableData.value[index];
    //   domainMemo[cluster] = false;
    //   tableData.value[index].cluster = '';
    //   return;
    // }
    // tableData.value[index].isLoading = true;
    // const result = await getRedisList({ exact_domain: domain }).finally(() => {
    //   tableData.value[index].isLoading = false;
    // });
    // if (result.results.length < 1) {
    //   return;
    // }
    // const list = result.results.filter(item => item.master_domain === domain);
    // if (list.length === 0) {
    //   return;
    // }
    // const item = list[0];
    const row = generateRowDateFromRequest(domainObj);
    tableData.value[index] = row;
    domainMemo[domainObj.master_domain] = true;
    selectedClusters.value[ClusterTypes.REDIS].push(domainObj);
  };

  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    tableData.value.splice(index + 1, 0, ...appendList);
  };
  // 删除一个集群
  const handleRemove = (index: number) => {
    const { cluster } = tableData.value[index];
    tableData.value.splice(index, 1);
    delete domainMemo[cluster];
    const clustersArr = selectedClusters.value[ClusterTypes.REDIS];
    selectedClusters.value[ClusterTypes.REDIS] = clustersArr.filter((item) => item.master_domain !== cluster);
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

  // 点击提交按钮
  const handleSubmit = async () => {
    try {
      isSubmitting.value = true;
      const infos = await Promise.all<InfoItem[]>(
        rowRefs.value.map((item: { getValue: () => Promise<InfoItem> }) => item.getValue()),
      );
      await createTicket({
        bk_biz_id: currentBizId,
        ticket_type: TicketTypes.REDIS_PROXY_SCALE_UP,
        remark: remark.value,
        details: {
          ip_source: 'resource_pool',
          infos,
        },
      }).then((data) => {
        window.changeConfirm = false;
        router.push({
          name: 'RedisProxyScaleUp',
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

  const handleReset = () => {
    tableData.value = [createRowData()];
    remark.value = '';
    selectedClusters.value[ClusterTypes.REDIS] = [];
    domainMemo = {};
    window.changeConfirm = false;
  };
</script>

<style lang="less" scoped>
  .proxy-scale-up-page {
    padding-bottom: 20px;

    .page-action-box {
      display: flex;
      align-items: center;
      margin-top: 16px;

      .safe-action {
        margin-left: auto;

        .safe-action-text {
          padding-bottom: 2px;
          border-bottom: 1px dashed #979ba5;
        }
      }
    }
  }

  .bottom-btn {
    width: 88px;
  }
</style>
