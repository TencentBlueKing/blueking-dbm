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
    <div class="spider-manage-privilege-clone-inst-page">
      <BkAlert
        closable
        theme="info"
        :title="$t('DB 实例权限克隆：DB 实例 IP 替换时，克隆原实例的所有权限到新实例中')" />
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
          :removeable="tableData.length <2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @remove="handleRemove(index)" />
      </RenderData>
      <InstanceSelector
        v-model:is-show="isShowBatchInstanceSelector"
        :selected="selectedIps"
        @change="handelInstanceSelectorChange" />
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
  import { useRouter } from 'vue-router';

  import { precheckPermissionClone } from '@services/permission';
  import { createTicket } from '@services/ticket';

  import { useGlobalBizs } from '@stores';

  import InstanceSelector, {
    type InstanceSelectorValues,
  } from '@components/instance-selector-new/Index.vue';

  import RenderData from './components/RenderData/Index.vue';
  import RenderDataRow, {
    createRowData,
    type IDataRow,
  } from './components/RenderData/Row.vue';

  const router = useRouter();
  const { currentBizId } = useGlobalBizs();

  const rowRefs = ref();
  const isShowBatchInstanceSelector = ref(false);
  const isSubmitting  = ref(false);

  const tableData = shallowRef<Array<IDataRow>>([createRowData({})]);
  const selectedIps = shallowRef<InstanceSelectorValues>({ tendbcluster: [] });
  let ipMemo = {} as Record<string, boolean>;

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.source && !firstRow.target;
  };

  // 批量选择
  const handleShowBatchSelector = () => {
    isShowBatchInstanceSelector.value = true;
  };
  // 批量选择
  const handelInstanceSelectorChange = (data: InstanceSelectorValues) => {
    selectedIps.value = data;
    const newList = data.tendbcluster.reduce((result, item) => {
      const { instance_address: ip } = item;
      if (!ipMemo[ip]) {
        const row = createRowData({
          source: item,
        });
        result.push(row);
        ipMemo[ip] = true;
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

  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    const dataList = [...tableData.value];
    dataList.splice(index + 1, 0, ...appendList);
    tableData.value = dataList;
  };

  // 删除一个集群
  const handleRemove = (index: number) => {
    const dataList = [...tableData.value];
    const ip = dataList[index].source?.instance_address;
    dataList.splice(index, 1);
    tableData.value = dataList;
    if (ip) {
      delete ipMemo[ip];
      const clustersArr = selectedIps.value.tendbcluster;
      selectedIps.value.tendbcluster = clustersArr.filter(item => item.instance_address !== ip);
    }
  };

  const handleSubmit = () => {
    isSubmitting.value = true;
    Promise.all(rowRefs.value.map((item: { getValue: () => Promise<any> }) => item.getValue()))
      .then(data => precheckPermissionClone({
        bizId: currentBizId,
        clone_type: 'instance',
        clone_list: data,
        clone_cluster_type: 'tendbcluster',
      }).then((precheckResult) => {
        if (!precheckResult.pre_check) {
          return Promise.reject();
        }
        return createTicket({
          ticket_type: 'TENDBCLUSTER_INSTANCE_CLONE_RULES',
          remark: '',
          details: {
            ...precheckResult,
            clone_type: 'instance',
          },
          bk_biz_id: currentBizId,
        }).then((data) => {
          window.changeConfirm = false;

          router.push({
            name: 'spiderPrivilegeCloneInst',
            params: {
              page: 'success',
            },
            query: {
              ticketId: data.id,
            },
          });
        });
      }))
      .finally(() => {
        isSubmitting.value = false;
      });
  };

  const handleReset = () => {
    tableData.value = [createRowData()];
    ipMemo = {};
    selectedIps.value.tendbcluster = [];
    window.changeConfirm = false;
  };
</script>

<style lang="less">
  .spider-manage-privilege-clone-inst-page {
    padding-bottom: 20px;
  }
</style>
