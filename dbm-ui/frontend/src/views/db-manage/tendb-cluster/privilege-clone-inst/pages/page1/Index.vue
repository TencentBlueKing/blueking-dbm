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
        :title="t('DB 实例权限克隆：DB 实例 IP 替换时，克隆原实例的所有权限到新实例中')" />
      <RenderData
        class="mt16"
        @batch-select-cluster="handleShowBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :data="item"
          :removeable="tableData.length < 2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @clone="(payload: IDataRow) => handleClone(index, payload)"
          @remove="handleRemove(index)" />
      </RenderData>
      <TicketRemark v-model="remark" />
      <InstanceSelector
        v-model:is-show="isShowBatchInstanceSelector"
        :cluster-types="[ClusterTypes.TENDBCLUSTER]"
        :selected="selectedIps"
        :tab-list-config="tabListConfig"
        @change="handelInstanceSelectorChange" />
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
        :content="t('重置将会清空当前填写的所有内容_请谨慎操作')"
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
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { precheckPermissionClone } from '@services/source/permission';
  import { createTicket } from '@services/source/ticket';

  import { useTicketCloneInfo } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';
  import TicketRemark from '@components/ticket-remark/Index.vue';

  import RenderData from './components/RenderData/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow } from './components/RenderData/Row.vue';

  const router = useRouter();
  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.TENDBCLUSTER_INSTANCE_CLONE_RULES,
    onSuccess(cloneData) {
      const { tableDataList } = cloneData;
      tableData.value = tableDataList;
      remark.value = cloneData.remark;
      window.changeConfirm = true;
    },
  });

  const rowRefs = ref();
  const isShowBatchInstanceSelector = ref(false);
  const isSubmitting = ref(false);
  const remark = ref('');

  const tableData = shallowRef<Array<IDataRow>>([createRowData({})]);
  const selectedIps = shallowRef<InstanceSelectorValues<IValue>>({ tendbcluster: [] });
  let ipMemo = {} as Record<string, boolean>;

  const tabListConfig = {
    [ClusterTypes.TENDBCLUSTER]: [
      {
        name: t('源实例'),
      },
    ],
  } as unknown as Record<ClusterTypes, PanelListType>;

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
  const handelInstanceSelectorChange = (data: InstanceSelectorValues<IValue>) => {
    console.log('asdasd = ', data);
    selectedIps.value = data;
    const newList = data.tendbcluster.reduce((result, item) => {
      const { instance_address: ip } = item;
      if (!ipMemo[ip]) {
        const row = createRowData({
          source: {
            clusterId: item.cluster_id,
            masterDomain: item.master_domain,
            dbModuleId: item.db_module_id,
            dbModuleName: item.db_module_name,
            instanceAddress: item.instance_address,
            bkCloudId: item.bk_cloud_id,
          },
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
    const ip = dataList[index].source?.instanceAddress;
    dataList.splice(index, 1);
    tableData.value = dataList;
    if (ip) {
      delete ipMemo[ip];
      const clustersArr = selectedIps.value.tendbcluster;
      selectedIps.value.tendbcluster = clustersArr.filter((item) => item.instance_address !== ip);
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

  const handleSubmit = async () => {
    try {
      isSubmitting.value = true;
      const infos = await Promise.all(rowRefs.value.map((item: { getValue: () => Promise<any> }) => item.getValue()));
      const precheckResult = await precheckPermissionClone({
        bizId: currentBizId,
        clone_type: 'instance',
        clone_list: infos,
        clone_cluster_type: 'tendbcluster',
      });
      if (!precheckResult.pre_check) {
        return;
      }
      await createTicket({
        ticket_type: TicketTypes.TENDBCLUSTER_INSTANCE_CLONE_RULES,
        remark: remark.value,
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
    } finally {
      isSubmitting.value = false;
    }
  };

  const handleReset = () => {
    remark.value = '';
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
