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
          @cluster-input-finish="(domain: string) => handleChangeCluster(index, domain)"
          @remove="handleRemove(index)" />
      </RenderData>
      <ClusterSelector
        v-model:is-show="isShowMasterInstanceSelector"
        :cluster-types="[ClusterTypes.REDIS]"
        :selected="selectedClusters"
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
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import RedisModel from '@services/model/redis/redis';
  import { getResourceSpecList } from '@services/source/dbresourceSpec';
  import { getRedisList } from '@services/source/redis';
  import { createTicket } from '@services/source/ticket';
  import type { SubmitTicket } from '@services/types/ticket';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ClusterSelector from '@components/cluster-selector-new/Index.vue';

  import RenderData from './components/Index.vue';
  import RenderDataRow, {
    createRowData,
    type IDataRow,
    type InfoItem,
  } from './components/Row.vue';
  import type { IListItem } from './components/SpecSelect.vue';

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const router = useRouter();

  const rowRefs = ref();
  const isShowMasterInstanceSelector = ref(false);
  const isSubmitting  = ref(false);
  const tableData = ref([createRowData()]);

  const totalNum = computed(() => tableData.value.filter(item => Boolean(item.cluster)).length);
  const inputedClusters = computed(() => tableData.value.map(item => item.cluster));
  const selectedClusters = shallowRef<{[key: string]: Array<RedisModel>}>({ [ClusterTypes.REDIS]: [] });

  // 集群域名是否已存在表格的映射表
  let domainMemo:Record<string, boolean> = {};
  let clusterSpecListMap: Record<string, IListItem[]> = {};

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
  const generateRowDateFromRequest = async (item: RedisModel) => {
    const specList = await querySpecList(item);
    return {
      rowKey: item.master_domain,
      isLoading: false,
      cluster: item.master_domain,
      clusterId: item.id,
      bkCloudId: item.bk_cloud_id,
      clusterType: item.cluster_spec.spec_cluster_type,
      nodeType: 'Proxy',
      spec: {
        ...item.proxy[0].spec_config,
        name: item.cluster_spec.spec_name,
        id: item.cluster_spec.spec_id,
        count: item.proxy.length,
      },
      targetNum: `${item.proxy.length}`,
      specList,
    };
  };

  // 批量选择
  const handelClusterChange = async (selected: {[key: string]: Array<RedisModel>}) => {
    selectedClusters.value = selected;
    const list = selected[ClusterTypes.REDIS];
    const newList: IDataRow[] = [];
    for (const item of list) {
      const domain = item.master_domain;
      if (!domainMemo[domain]) {
        const row = await generateRowDateFromRequest(item);
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

  // 查询集群对应的规格列表
  const querySpecList = async (item: RedisModel) => {
    const proxyMachineMap = {
      TwemproxyRedisInstance: 'twemproxy',
      TwemproxyTendisSSDInstance: 'twemproxy',
      PredixyTendisplusCluster: 'predixy',
    };
    const type = item.cluster_spec.spec_cluster_type;
    const machineType = proxyMachineMap[type];
    const specId = item.cluster_spec.spec_id;
    const specCount = item.proxy.length;
    if (type in clusterSpecListMap) {
      return clusterSpecListMap[type];
    }
    const ret = await getResourceSpecList({
      spec_cluster_type: type,
      spec_machine_type: machineType,
      limit: -1,
      offset: 0,
    });
    const retArr = ret.results;
    const arr = retArr.map(item => ({
      value: item.spec_id,
      label: item.spec_id === specId ? `${item.spec_name} ${t('((n))台', { n: specCount })}` : item.spec_name,
      specData: {
        name: item.spec_name,
        cpu: item.cpu,
        id: item.spec_id,
        mem: item.mem,
        count: 0,
        storage_spec: item.storage_spec,
      },
    }));
    clusterSpecListMap[type] = arr;
    return arr;
  };

  // 输入集群后查询集群信息并填充到table
  const handleChangeCluster = async (index: number, domain: string) => {
    if (!domain) {
      const { cluster } = tableData.value[index];
      domainMemo[cluster] = false;
      tableData.value[index].cluster = '';
      return;
    }
    tableData.value[index].isLoading = true;
    const result = await getRedisList({ domain }).finally(() => {
      tableData.value[index].isLoading = false;
    });
    if (result.results.length < 1) {
      return;
    }
    const data = result.results[0];
    const row = await generateRowDateFromRequest(data);
    tableData.value[index] = row;
    domainMemo[domain] = true;
    selectedClusters.value[ClusterTypes.REDIS].push(data);
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
    selectedClusters.value[ClusterTypes.REDIS] = clustersArr.filter(item => item.master_domain !== cluster);
  };

  // 点击提交按钮
  const handleSubmit = async () => {
    const infos = await Promise.all<InfoItem[]>(rowRefs.value.map((item: {
      getValue: () => Promise<InfoItem>
    }) => item.getValue()));

    const params: SubmitTicket<TicketTypes, InfoItem[]> = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.REDIS_PROXY_SCALE_UP,
      details: {
        ip_source: 'resource_pool',
        infos,
      },
    };

    InfoBox({
      title: t('确认对n个集群扩容接入层？', { n: totalNum.value }),
      width: 480,
      onConfirm: () => {
        isSubmitting.value = true;
        createTicket(params).then((data) => {
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
        })
          .catch((e) => {
            console.error('proxy scale up submit ticket error：', e);
          })
          .finally(() => {
            isSubmitting.value = false;
          });
      } });
  };

  const handleReset = () => {
    tableData.value = [createRowData()];
    selectedClusters.value[ClusterTypes.REDIS] = [];
    domainMemo = {};
    clusterSpecListMap = {};
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
