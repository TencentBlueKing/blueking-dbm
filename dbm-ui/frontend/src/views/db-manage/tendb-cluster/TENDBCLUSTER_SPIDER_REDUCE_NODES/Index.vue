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
  <SmartAction class="db-toolbox">
    <BkAlert
      class="mb-20"
      closable
      :title="t('缩容接入层：减少集群的Proxy数量')" />
    <div>
      <div class="title-spot mt-12 mb-10">{{ t('缩容方式') }}<span class="required" /></div>
      <BkRadioGroup
        v-model="shrinkType"
        style="width: 450px"
        type="card">
        <BkRadioButton label="QUANTITY">
          {{ t('指定数量缩容') }}
        </BkRadioButton>
        <BkRadioButton label="HOST">
          {{ t('指定主机缩容') }}
        </BkRadioButton>
      </BkRadioGroup>
    </div>
    <BkForm
      class="mt-16 mb-20"
      form-type="vertical"
      :model="formData">
      <Component
        :is="tableMap[shrinkType]"
        ref="table"
        :ticket-details="ticketDetails" />
      <BkFormItem
        v-bk-tooltips="t('存在业务连接时需要人工确认')"
        class="fit-content">
        <BkCheckbox
          v-model="formData.isSafe"
          :false-label="false"
          true-label>
          <span class="safe-action-text">{{ t('检查业务连接') }}</span>
        </BkCheckbox>
      </BkFormItem>
      <TicketPayload v-model="formData.payload" />
    </BkForm>
    <template #action>
      <BkButton
        class="mr-8 w-88"
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
<script lang="ts" setup>
  import { reactive, useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { TendbCluster } from '@services/model/ticket/ticket';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';

  import CountShrink from './components/count-shrink/Index.vue';
  import HostShrink from './components/host-shrink/Index.vue';

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const tableMap = {
    HOST: HostShrink,
    QUANTITY: CountShrink,
  };
  const defaultData = () => ({
    isSafe: true,
    payload: createTickePayload(),
  });

  const shrinkType = ref<TendbCluster.ResourcePool.SpiderReduceNodes['shrink_type']>('QUANTITY');
  const formData = reactive(defaultData());
  const ticketDetails = ref<TendbCluster.ResourcePool.SpiderReduceNodes>();

  useTicketDetail<TendbCluster.ResourcePool.SpiderReduceNodes>(TicketTypes.TENDBCLUSTER_SPIDER_REDUCE_NODES, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      shrinkType.value = ticketDetail.details.shrink_type;
      Object.assign(formData, {
        isSafe: details.is_safe,
        payload: createTickePayload(ticketDetail),
      });
      nextTick(() => {
        ticketDetails.value = details;
      });
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    infos: {
      cluster_id: number;
      old_nodes?: {
        spider_reduced_hosts: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
      };
      reduce_spider_role: string;
      spider_reduced_to_count?: number;
    }[];
    is_safe: boolean;
    shrink_type: TendbCluster.ResourcePool.SpiderReduceNodes['shrink_type'];
  }>(TicketTypes.TENDBCLUSTER_SPIDER_REDUCE_NODES);

  const handleSubmit = async () => {
    const ticketDetails = await tableRef.value!.getValue();
    if (ticketDetails.infos.length) {
      createTicketRun({
        details: {
          ...ticketDetails,
          is_safe: formData.isSafe,
          shrink_type: shrinkType.value,
        },
        ...formData.payload,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
    tableRef.value?.reset();
  };
</script>
