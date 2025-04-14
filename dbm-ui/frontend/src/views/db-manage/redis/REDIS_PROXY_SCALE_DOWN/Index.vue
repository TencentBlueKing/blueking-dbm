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
    <BkAlert
      class="mb-20"
      closable
      :title="t('缩容接入层：减少集群的Proxy数量，但集群Proxy数量不能少于2')" />
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

  import type { Redis } from '@services/model/ticket/ticket';

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
    isSafe: false,
    payload: createTickePayload(),
    tableData: [],
  });

  const shrinkType = ref<Redis.ResourcePool.ProxyScaleDown['shrink_type']>('QUANTITY');
  const formData = reactive(defaultData());
  const ticketDetails = ref<Redis.ResourcePool.ProxyScaleDown>();

  useTicketDetail<Redis.ResourcePool.ProxyScaleDown>(TicketTypes.REDIS_PROXY_SCALE_DOWN, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      shrinkType.value = ticketDetail.details.shrink_type;
      Object.assign(formData, {
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
        proxy_reduced_hosts: {
          bk_biz_id: number;
          bk_cloud_id: number;
          bk_host_id: number;
          ip: string;
        }[];
      };
      online_switch_type: string;
      target_proxy_count?: number;
    }[];
    ip_source: 'resource_pool';
    shrink_type: Redis.ResourcePool.ProxyScaleDown['shrink_type'];
  }>(TicketTypes.REDIS_PROXY_SCALE_DOWN);

  const handleSubmit = async () => {
    const ticketDetails = await tableRef.value!.getValue();
    if (ticketDetails.infos.length) {
      createTicketRun({
        details: {
          ...ticketDetails,
          ip_source: 'resource_pool',
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
