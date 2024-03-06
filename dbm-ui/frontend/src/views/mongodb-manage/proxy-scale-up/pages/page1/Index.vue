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
          :select-list="specList"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @cluster-input-finish="(domain: string) => handleChangeCluster(index, domain)"
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
    <ClusterSelector
      v-model:is-show="isShowMasterInstanceSelector"
      :cluster-types="[ClusterTypes.MONGO_SHARED_CLUSTER]"
      :selected="selectedClusters"
      @change="handelClusterChange" />
  </SmartAction>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRouter } from 'vue-router';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import { getSpecResourceCount } from '@services/source/dbresourceResource';
  import { getResourceSpecList } from '@services/source/dbresourceSpec';
  import { getMongoList } from '@services/source/mongodb';
  import { createTicket } from '@services/source/ticket';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ClusterSelector from '@components/cluster-selector-new/Index.vue';

  import type { IListItem } from '@views/mongodb-manage/components/edit-field/spec-select/components/Select.vue';

  import RenderData from './components/Index.vue';
  import RenderDataRow, {
    createRowData,
    type IDataRow,
    type InfoItem,
  } from './components/Row.vue';

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const router = useRouter();

  const rowRefs = ref();
  const isShowMasterInstanceSelector = ref(false);
  const isSubmitting  = ref(false);
  const tableData = ref([createRowData()]);
  const specList = ref<IListItem[]>([]);
  const bkCloudId = ref<number>();

  const selectedClusters = shallowRef<{[key: string]: Array<MongodbModel>}>({
    [ClusterTypes.MONGO_SHARED_CLUSTER]: [],
  });

  const totalNum = computed(() => tableData.value.filter(item => Boolean(item.clusterName)).length);
  const inputedClusters = computed(() => tableData.value.map(item => item.clusterName));

  const { run: fetchSpecResourceCount } = useRequest(getSpecResourceCount, {
    manual: true,
    onSuccess(data) {
      specList.value.forEach((item) => {
        Object.assign(item.specData, {
          count: data[item.specData.id],
        });
      });
    },
  });

  useRequest(getResourceSpecList, {
    defaultParams: [{
      spec_cluster_type: 'MongoShardedCluster',
      spec_machine_type: 'mongos',
      limit: -1,
      offset: 0,
    }],
    onSuccess(data) {
      specList.value = data.results.map(item => ({
        value: item.spec_id,
        label: item.spec_name,
        specData: {
          name: item.spec_name,
          cpu: item.cpu,
          id: item.spec_id,
          mem: item.mem,
          count: 0,
          storage_spec: item.storage_spec,
        },
      }));
    },
  });

  // 集群域名是否已存在表格的映射表
  let domainMemo:Record<string, boolean> = {};

  watch(bkCloudId, () => {
    if (bkCloudId.value !== undefined) {
      fetchSpecResourceCount({
        bk_biz_id: currentBizId,
        bk_cloud_id: bkCloudId.value,
        spec_ids: specList.value.map(item => item.specData.id),
      });
    }
  });

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.clusterName;
  };

  // Master 批量选择
  const handleShowBatchSelector = () => {
    isShowMasterInstanceSelector.value = true;
  };

  // 根据集群选择返回的数据加工成table所需的数据
  const generateRowDateFromRequest = (item: MongodbModel) => ({
    rowKey: item.master_domain,
    isLoading: false,
    clusterName: item.master_domain,
    clusterId: item.id,
    shardNum: item.shard_num,
    machineNum: item.replicaset_machine_num,
    currentSpec: {
      ...item.mongos[0].spec_config,
      count: item.shard_num,
    },
  });

  // 批量选择
  const handelClusterChange = (selected: {[key: string]: Array<MongodbModel>}) => {
    selectedClusters.value = selected;
    const list = selected[ClusterTypes.MONGO_SHARED_CLUSTER];
    if (bkCloudId.value === undefined) {
      bkCloudId.value = list[0].bk_cloud_id;
    }
    const newList: IDataRow[] = [];
    for (const item of list) {
      const domain = item.master_domain;
      if (!domainMemo[domain]) {
        const row = generateRowDateFromRequest(item);
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
  const handleChangeCluster = async (index: number, domain: string) => {
    if (!domain) {
      const { clusterName } = tableData.value[index];
      domainMemo[clusterName] = false;
      tableData.value[index].clusterName = '';
      return;
    }
    tableData.value[index].isLoading = true;
    const result = await getMongoList({ exact_domain: domain }).finally(() => {
      tableData.value[index].isLoading = false;
    });
    if (result.results.length < 1) {
      return;
    }
    const item = result.results[0];
    const row = generateRowDateFromRequest(item);
    tableData.value[index] = row;
    domainMemo[domain] = true;
    selectedClusters.value[ClusterTypes.MONGO_SHARED_CLUSTER].push(item);
  };

  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    tableData.value.splice(index + 1, 0, ...appendList);
  };

  // 删除一个集群
  const handleRemove = (index: number) => {
    const { clusterName } = tableData.value[index];
    tableData.value.splice(index, 1);
    delete domainMemo[clusterName];
    const clustersArr = selectedClusters.value[ClusterTypes.MONGO_SHARED_CLUSTER];
    selectedClusters.value[ClusterTypes.MONGO_SHARED_CLUSTER] = clustersArr.filter(item => item.master_domain !== clusterName);
  };

  // 点击提交按钮
  const handleSubmit = async () => {
    const infos = await Promise.all<InfoItem[]>(rowRefs.value.map((item: {
      getValue: () => Promise<InfoItem>
    }) => item.getValue()));

    const params = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.MONGODB_ADD_MONGOS,
      details: {
        infos,
      },
    };

    InfoBox({
      title: t('确认扩容n个集群', { n: totalNum.value }),
      width: 400,
      onConfirm: () => {
        isSubmitting.value = true;
        createTicket(params).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: 'MongoProxyScaleUp',
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

  const handleReset = () => {
    tableData.value = [createRowData()];
    selectedClusters.value[ClusterTypes.MONGO_SHARED_CLUSTER] = [];
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
