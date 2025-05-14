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
  <InfoList>
    <InfoItem :label="t('DB类型')">
      {{ ticketDetails.details.group }}
    </InfoItem>
    <InfoItem :label="t('前置单据')">
      <BkButton
        text
        theme="primary"
        @click="handleGoTicketDetail">
        {{ ticketDetails.details.parent_ticket }}
      </BkButton>
    </InfoItem>
  </InfoList>
  <RecycleHostCard
    :data="ticketDetails.details.fault_hosts"
    :title="t('转入故障池')" />
  <RecycleHostCard
    :data="ticketDetails.details.recycle_hosts"
    :title="t('转入待回收池')" />
  <RecycleHostCard
    :data="ticketDetails.details.resource_hosts"
    :title="t('退回资源池')" />
  <RecycleHostCard
    :data="ticketDetails.details.recycled_hosts"
    :title="t('回收')" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import TicketModel, { type Common } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import { getBusinessHref } from '@utils';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  import RecycleHostCard from './RecycleHostCard.vue';

  interface Props {
    ticketDetails: TicketModel<Common.ResourcePoolRecycle>;
  }

  defineOptions({
    name: TicketTypes.RECYCLE_OLD_HOST,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();
  const router = useRouter();

  const handleGoTicketDetail = () => {
    const { href } = router.resolve({
      name: 'bizTicketManage',
      params: {
        ticketId: props.ticketDetails.details.parent_ticket,
      },
    });
    window.open(getBusinessHref(href, props.ticketDetails.bk_biz_id), '_blank');
  };
</script>
