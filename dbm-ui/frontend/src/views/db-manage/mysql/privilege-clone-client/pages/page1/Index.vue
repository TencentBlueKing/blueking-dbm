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
    <div class="spider-manage-privilege-clone-client-page">
      <BkAlert
        closable
        theme="info"
        :title="t('客户端权限克隆：访问 DB 来源 IP 替换时做的权限克隆')" />
      <BkButton
        class="clone-client-batch mt16"
        @click="() => (isShowBatchInput = true)">
        <i class="db-icon-add" />
        {{ t('批量录入') }}
      </BkButton>
      <RenderData
        class="mt16"
        @show-ip-selector="handleShowIpSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :data="item"
          :removeable="tableData.length < 2"
          @add="(payload) => handleAppend(index, payload)"
          @clone="(payload: IDataRow) => handleClone(index, payload)"
          @remove="handleRemove(index)" />
      </RenderData>
      <TicketRemark v-model="remark" />
      <BatchInput
        v-model:is-show="isShowBatchInput"
        @change="handleBatchInput" />
      <IpSelector
        v-model:show-dialog="isShowIpSelector"
        :biz-id="currentBizId"
        button-text=""
        :data="selectedIps"
        :os-types="[OSTypes.Linux]"
        service-mode="all"
        :show-view="false"
        @change="handleHostChange" />
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
  import type { HostInfo } from '@services/types';

  import { useTicketCloneInfo } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { OSTypes, TicketTypes } from '@common/const';

  import IpSelector from '@components/ip-selector/IpSelector.vue';
  import TicketRemark from '@components/ticket-remark/Index.vue';

  import BatchInput from './components/BatchInput.vue';
  import RenderData from './components/RenderData/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow } from './components/RenderData/Row.vue';

  const { t } = useI18n();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.MYSQL_CLIENT_CLONE_RULES,
    onSuccess(cloneData) {
      const { tableDataList } = cloneData;
      tableData.value = tableDataList;
      remark.value = cloneData.remark;
      window.changeConfirm = true;
    },
  });

  const rowRefs = ref();
  const isShowIpSelector = ref(false);
  const isShowBatchInput = ref(false);
  const isSubmitting = ref(false);
  const tableData = ref<Array<IDataRow>>([createRowData({})]);
  const remark = ref('');

  const selectedIps = shallowRef<HostInfo[]>([]);

  let ipMemo = {} as Record<string, boolean>;

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.source && firstRow.target.length < 1;
  };

  /**
   * 批量录入
   */
  const handleBatchInput = async (list: Array<Pick<IDataRow, 'source' | 'target'>>) => {
    const formatList = list.map((item) => ({
      ...createRowData(),
      source: item.source,
      target: item.target,
    }));

    if (checkListEmpty(tableData.value)) {
      tableData.value = formatList;
    } else {
      tableData.value = [...tableData.value, ...formatList];
    }
    window.changeConfirm = true;
  };

  const handleShowIpSelector = () => {
    isShowIpSelector.value = true;
  };

  const handleHostChange = (data: HostInfo[]) => {
    selectedIps.value = data;
    const newList = data.reduce<IDataRow[]>((result, item) => {
      const { ip } = item;
      if (!ipMemo[ip]) {
        const row = createRowData({
          source: {
            bk_cloud_id: item.cloud_id,
            ip: item.ip,
          },
        });
        result.push(row);
        ipMemo[ip] = true;
      }
      return result;
    }, []);
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
    const ip = dataList[index].source?.ip;
    dataList.splice(index, 1);
    tableData.value = dataList;
    if (ip) {
      delete ipMemo[ip];
      selectedIps.value = selectedIps.value.filter((item) => item.ip !== ip);
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

  const handleSubmit = () => {
    isSubmitting.value = true;
    Promise.all(rowRefs.value.map((item: { getValue: () => Promise<any> }) => item.getValue()))
      .then((data) =>
        precheckPermissionClone({
          bizId: currentBizId,
          clone_type: 'client',
          clone_list: data,
          clone_cluster_type: 'mysql',
        }).then((precheckResult) => {
          if (!precheckResult.pre_check) {
            return Promise.reject();
          }
          return createTicket({
            ticket_type: TicketTypes.MYSQL_CLIENT_CLONE_RULES,
            bk_biz_id: currentBizId,
            remark: remark.value,
            details: {
              ...precheckResult,
              clone_type: 'client',
            },
          }).then((data) => {
            window.changeConfirm = false;

            router.push({
              name: 'MySQLPrivilegeCloneClient',
              params: {
                page: 'success',
              },
              query: {
                ticketId: data.id,
              },
            });
          });
        }),
      )
      .finally(() => {
        isSubmitting.value = false;
      });
  };

  const handleReset = () => {
    tableData.value = [createRowData()];
    remark.value = '';
    ipMemo = {};
    selectedIps.value = [];
    window.changeConfirm = false;
  };
</script>

<style lang="less">
  .spider-manage-privilege-clone-client-page {
    padding-bottom: 20px;

    .page-action-box {
      display: flex;
      align-items: center;
      margin-top: 16px;
    }

    .item-block {
      margin-top: 24px;
    }
  }
</style>
