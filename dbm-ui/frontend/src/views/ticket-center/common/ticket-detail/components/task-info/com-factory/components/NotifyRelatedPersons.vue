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
  <InfoItem :label="t('发送交付通知')">
    {{ data?.is_send ? t('是') : t('否') }}
  </InfoItem>
  <InfoItem
    v-if="data?.is_send"
    :label="t('额外收件人')">
    {{ receiverUsername || '--' }}
  </InfoItem>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { MessageTypes } from '@common/const/messageTypes.ts';

  import { Item as InfoItem } from './info-list/Index.vue';

  interface Props {
    data?: {
      default_receiver_username?: string;
      is_send: boolean;
      msg_type: MessageTypes[];
      receiver__username: string;
    };
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const receiverList = (props.data?.receiver__username?.split(',') ?? []).filter(Boolean);
  /**
   * 只展示额外收件人
   * 新单据有 default_receiver_username，receiver__username 即额外收件人；
   * 旧单据没有该字段，receiver__username 前两位是提单人与主DBA，需剔除
   */
  const receiverUsername = (
    props.data?.default_receiver_username === undefined ? receiverList.slice(2) : receiverList
  ).join('，');
</script>
