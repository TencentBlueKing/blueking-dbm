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
      <RenderData
        v-slot="slotProps"
        class="mt16"
        @show-ip-selector="handleShowIpSelector">
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
      <IpSelector
        v-model:show-dialog="isShowIpSelector"
        :biz-id="currentBizId"
        button-text=""
        :data="[]"
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

  import { precheckPermissionClone } from '@services/permission';
  import { createTicket } from '@services/ticket';
  import type { HostDetails  } from '@services/types/ip';

  import { useGlobalBizs } from '@stores';

  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import RenderData from './components/RenderData/Index.vue';
  import RenderDataRow, {
    createRowData,
    type IDataRow,
  } from './components/RenderData/Row.vue';

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.source && !firstRow.target;
  };

  const { t } = useI18n();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();

  const rowRefs = ref();
  const isShowIpSelector = ref(false);
  const isSubmitting  = ref(false);

  const tableData = shallowRef<Array<IDataRow>>([createRowData({})]);

  // Master 批量选择
  const handleShowIpSelector = () => {
    isShowIpSelector.value = true;
  };

  const handleHostChange = (data: HostDetails[]) => {
    const newList = data.map(hostData => createRowData({
      source: hostData,
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
      .then(data => precheckPermissionClone(currentBizId, {
        clone_type: 'client',
        clone_list: data,
        clone_cluster_type: 'tendbcluster',
      })
        .then((precheckResult) => {
          if (!precheckResult.pre_check) {
            return Promise.reject();
          }
          return createTicket({
            ticket_type: 'TENDBCLUSTER_CLIENT_CLONE_RULES',
            bk_biz_id: currentBizId,
            remark: '',
            details: {
              ...precheckResult,
              clone_type: 'client',
            },
          }).then((data) => {
            window.changeConfirm = false;

            router.push({
              name: 'spiderPrivilegeCloneClient',
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

    .item-block{
      margin-top: 24px;
    }
  }
</style>
