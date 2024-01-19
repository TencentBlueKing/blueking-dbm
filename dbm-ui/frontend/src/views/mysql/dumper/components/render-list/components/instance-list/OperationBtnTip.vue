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
  <BkPopover
    :disabled="disabled"
    placement="top"
    :popover-delay="[100, 200]"
    theme="light">
    <slot />
    <template #content>
      <I18nT
        keypath="xx_跳转_我的服务单_查看进度"
        style="font-size: 12px; line-height: 16px; color: #63656e;"
        tag="div">
        <span>{{ data.operationBtnTipStatusText }}</span>
        <RouterLink
          target="_blank"
          :to="{
            name: 'SelfServiceMyTickets',
            query: {
              id: data.operationTicketId,
            },
          }">
          {{ $t('我的服务单') }}
        </RouterLink>
      </I18nT>
    </template>
  </BkPopover>
</template>
<script setup lang="ts">
  interface Props {
    disabled: boolean,
    data: {
      operationBtnTipStatusText: string,
      operationTicketId: number,
    }
  }

  defineProps<Props>();
</script>
