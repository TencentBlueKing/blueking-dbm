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
    <div class="spider-manage-add-mnt-page">
      <BkAlert
        closable
        theme="info"
        :title="t('添加运维节点：在原集群上增加运维节点实例来实现额外的数据访问，在运维节点上的操作不会影响原集群')" />
      <RenderData
        v-slot="slotProps"
        class="mt16"
        @batch-select-cluster="handleShowBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :data="item"
          :is-fixed="slotProps.isOverflow"
          :removeable="tableData.length < 2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @remove="handleRemove(index)" />
      </RenderData>
      <ClusterSelector
        v-model:is-show="isShowBatchSelector"
        :get-resource-list="getList"
        :selected="{}"
        :tab-list="clusterSelectorTabList"
        @change="handelClusterChange" />
    </div>
    <template #action>
      <BkButton
        class="w-88"
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
          class="ml8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>

<script setup lang="tsx">
  import {
    ref,
    shallowRef,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { getList } from '@services/spider';
  import { createTicket } from '@services/ticket';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  import ClusterSelector from '@components/cluster-selector/SpiderClusterSelector.vue';

  import RenderData from './components/RenderData/Index.vue';
  import RenderDataRow, {
    createRowData,
    type IDataRow,
  } from './components/RenderData/Row.vue';

  interface IClusterData {
    id: number,
    master_domain: string,
  }

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.clusterData && !firstRow.spiderIpList;
  };

  const clusterSelectorTabList = [{
    id: ClusterTypes.SPIDER,
    name: '集群',
  }];

  const { t } = useI18n();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();

  const rowRefs = ref();
  const isShowBatchSelector = ref(false);
  const isSubmitting  = ref(false);

  const tableData = shallowRef<Array<IDataRow>>([createRowData({})]);

  // 批量选择
  const handleShowBatchSelector = () => {
    isShowBatchSelector.value = true;
  };
  // 批量选择
  const handelClusterChange = (selected: {[key: string]: Array<IClusterData>}) => {
    const newList = selected[ClusterTypes.SPIDER].map(clusterData => createRowData({
      clusterData: {
        id: clusterData.id,
        domain: clusterData.master_domain,
      },
    }));
    if (checkListEmpty(tableData.value)) {
      tableData.value = newList;
    } else {
      tableData.value = [...tableData.value, ...newList];
    }
    window.changeConfirm = true;
  };
  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    const dataList = [...tableData.value];
    dataList.splice(index + 1, 0, ...appendList);
    tableData.value = dataList;
  };
  // 删除一个集群
  const handleRemove = (index: number) => {
    const dataList = [...tableData.value];
    dataList.splice(index, 1);
    tableData.value = dataList;
  };

  const handleSubmit = () => {
    isSubmitting.value = true;
    Promise.all(rowRefs.value.map((item: { getValue: () => Promise<any> }) => item.getValue()))
      .then(data => createTicket({
        ticket_type: 'TENDBCLUSTER_SPIDER_MNT_APPLY',
        remark: '',
        details: {
          infos: data,
        },
        bk_biz_id: currentBizId,
      }).then((data) => {
        window.changeConfirm = false;

        router.push({
          name: 'spiderAddMnt',
          params: {
            page: 'success',
          },
          query: {
            ticketId: data.id,
          },
        });
      }))
      .finally(() => {
        isSubmitting.value = false;
      });
  };

  const handleReset = () => {
    tableData.value = [createRowData()];
  };
</script>

<style lang="less">
  .spider-manage-add-mnt-page {
    padding-bottom: 20px;
  }
</style>
