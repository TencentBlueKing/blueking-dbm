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
    <div class="recover-from-ins-page">
      <BkAlert
        closable
        theme="info"
        :title="t('以构造实例恢复：把构造实例上的数据写回原集群')" />
      <RenderData
        v-slot="slotProps"
        class="mt16"
        @show-master-batch-selector="handleShowMasterBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :data="item"
          :inputed-clusters="inputedClusters"
          :is-fixed="slotProps.isOverflow"
          :removeable="tableData.length < 2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @cluster-input-finish="(domain: string) => handleChangeCluster(index, domain)"
          @remove="handleRemove(index)" />
      </RenderData>
      <div
        class="title-spot"
        style="margin: 25px 0 12px;">
        {{ t('写入类型') }}<span class="required" />
      </div>
      <BkRadioGroup
        v-model="writeType">
        <BkRadio
          v-for="item in writeTypeList"
          :key="item.value"
          :label="item.value">
          {{ item.label }}
        </BkRadio>
      </BkRadioGroup>
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
    <VisitEntrySelector
      v-model:is-show="isShowClusterSelector"
      :cluster-types="[ClusterTypes.REDIS]"
      :selected="selectedClusters"
      :tab-list-config="tabListConfig"
      @change="handelClusterChange" />
  </SmartAction>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { WriteModes } from '@services/model/redis/redis-dst-history-job';
  import RedisRollbackModel from '@services/model/redis/redis-rollback';
  import { getRollbackList } from '@services/source/redisRollback';
  import { createTicket } from '@services/ticket';
  import type { SubmitTicket } from '@services/types/ticket';

  import { useGlobalBizs } from '@stores';

  import {
    ClusterTypes,
    LocalStorageKeys,
    TicketTypes,
  } from '@common/const';

  import VisitEntrySelector from '@components/cluster-selector-new/Index.vue';

  import RenderData from './components/Index.vue';
  import RenderDataRow, {
    createRowData,
    type IDataRow,
    type InfoItem,
  } from './components/Row.vue';

  type SubmitTicketType = SubmitTicket<TicketTypes, InfoItem[]>
    & { details: { dts_copy_type: string; write_mode: WriteModes } };

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const router = useRouter();
  const rowRefs = ref();
  const isSubmitting  = ref(false);
  const writeType = ref(WriteModes.DELETE_AND_WRITE_TO_REDIS);

  const tableData = ref([createRowData()]);
  const isShowClusterSelector = ref(false);
  const selectedClusters = shallowRef<{[key: string]: Array<RedisRollbackModel>}>({ [ClusterTypes.REDIS]: [] });
  const totalNum = computed(() => tableData.value.filter(item => Boolean(item.srcCluster)).length);
  const inputedClusters = computed(() => tableData.value.map(item => item.srcCluster));

  const tabListConfig = {
    [ClusterTypes.REDIS]: {
      getResourceList: getRollbackList,
      customColums: [
        {
          label: t('构造产物访问入口'),
          field: 'temp_cluster_proxy',
          showOverflowTooltip: true,
        },
        {
          label: t('目标集群'),
          field: 'prod_cluster',
          showOverflowTooltip: true,
          minWidth: 100,
        },
        {
          label: t('构造到指定时间'),
          field: 'recovery_time_point',
          showOverflowTooltip: true,
        },
      ],
      previewResultKey: 'temp_cluster_proxy',
      searchSelectList: [{
        name: t('访问入口'),
        id: 'temp_cluster_proxy',
      }, {
        name: t('目标集群'),
        id: 'prod_cluster',
      }],
      searchPlaceholder: t('访问入口_目标集群'),
    },
  };

  const writeTypeList = [
    {
      label: t('先删除同名 Key，再写入（如：del  $key+ hset $key）'),
      value: WriteModes.DELETE_AND_WRITE_TO_REDIS,
    },
    {
      label: t('保留同名 Key，追加写入（如：hset $key）'),
      value: WriteModes.KEEP_AND_APPEND_TO_REDIS,
    },
    {
      label: t('清空目标集群所有数据，再写入'),
      value: WriteModes.FLUSHALL_AND_WRITE_TO_REDIS,
    },
  ];

  // 集群域名是否已存在表格的映射表
  let domainMemo: Record<string, boolean> = {};

  const recoverDataListFromLocalStorage = () => {
    const r = localStorage.getItem(LocalStorageKeys.REDIS_ROLLBACK_LIST);
    if (!r) {
      return;
    }
    const dataList = JSON.parse(r) as RedisRollbackModel[];
    tableData.value = dataList.map(item => ({
      rowKey: item.prod_cluster,
      isLoading: false,
      srcCluster: item.temp_cluster_proxy,
      targetCluster: item.prod_cluster,
      targetClusterId: item.prod_cluster_id,
      targetTime: item.recovery_time_point,
      includeKey: ['*'],
      excludeKey: [],
    }));
    localStorage.removeItem(LocalStorageKeys.REDIS_ROLLBACK_LIST);
  };

  recoverDataListFromLocalStorage();


  const handleShowMasterBatchSelector = () => {
    isShowClusterSelector.value = true;
  };

  // 检测列表是否为空
  const checkListEmpty = (list: IDataRow[]) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.srcCluster;
  };


  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    tableData.value.splice(index + 1, 0, ...appendList);
  };
  // 删除一个集群
  const handleRemove = (index: number) => {
    const removeItem = tableData.value[index];
    const { srcCluster } = removeItem;
    tableData.value.splice(index, 1);
    delete domainMemo[srcCluster];
    const clustersArr = selectedClusters.value[ClusterTypes.REDIS];
    selectedClusters.value[ClusterTypes.REDIS] = clustersArr.filter(item => item.temp_cluster_proxy !== srcCluster);
  };

  const generateTableRow = (item: RedisRollbackModel) => ({
    rowKey: item.prod_cluster,
    isLoading: false,
    srcCluster: item.temp_cluster_proxy,
    targetTime: item.recovery_time_point,
    targetCluster: item.prod_cluster,
    targetClusterId: item.prod_cluster_id,
    includeKey: ['*'],
    excludeKey: [],
  });

  // 批量选择
  const handelClusterChange = async (selected: {[key: string]: Array<RedisRollbackModel>}) => {
    selectedClusters.value = selected;
    const list = selected[ClusterTypes.REDIS];
    const newList = list.reduce((result, item) => {
      const domain = item.temp_cluster_proxy;
      if (!domainMemo[domain]) {
        const row = generateTableRow(item);
        result.push(row);
        domainMemo[domain] = true;
      }
      return result;
    }, [] as IDataRow[]);
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
      const { srcCluster } = tableData.value[index];
      domainMemo[srcCluster] = false;
      tableData.value[index].srcCluster = '';
      return;
    }
    tableData.value[index].isLoading = true;
    const ret = await getRollbackList({
      bk_biz_id: currentBizId,
      limit: 10,
      offset: 0,
      temp_cluster_proxy: domain,
    }).finally(() => {
      tableData.value[index].isLoading = false;
    });
    if (ret.results.length < 1) {
      return;
    }
    const data = ret.results[0];
    const row = generateTableRow(data);
    tableData.value[index] = row;
    domainMemo[domain] = true;
    selectedClusters.value[ClusterTypes.REDIS].push(data);
  };

  // 提交
  const handleSubmit = async () => {
    const infos = await Promise.all<InfoItem[]>(rowRefs.value.map((item: {
      getValue: () => Promise<InfoItem>
    }) => item.getValue()));
    const params: SubmitTicketType = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.REDIS_CLUSTER_ROLLBACK_DATA_COPY,
      details: {
        dts_copy_type: 'copy_from_rollback_instance',
        write_mode: writeType.value,
        infos,
      },
    };
    InfoBox({
      title: t('确认对n个构造实例进行恢复？', { n: totalNum.value }),
      width: 480,
      onConfirm: () => {
        isSubmitting.value = true;
        createTicket(params).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: 'RedisRecoverFromInstance',
            params: {
              page: 'success',
            },
            query: {
              ticketId: data.id,
            },
          });
        })
          .catch((e) => {
            console.error('recover from instance ticket error', e);
          })
          .finally(() => {
            isSubmitting.value = false;
          });
      } });
  };

  // 重置
  const handleReset = () => {
    tableData.value = [createRowData()];
    selectedClusters.value[ClusterTypes.REDIS] = [];
    domainMemo = {};
    window.changeConfirm = false;
  };

</script>

<style lang="less" scoped>
  .recover-from-ins-page {
    padding-bottom: 20px;

    .page-action-box {
      display: flex;
      align-items: center;
      margin-top: 16px;
    }
  }
</style>
