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
  <span
    v-if="disabled && data?.ticket_id"
    ref="rootRef"
    class="cluster-operation-status-tips">
    <slot :disabled="disabled" />
    <I18nT
      ref="popRef"
      keypath="xx_跳转_我的服务单_查看进度"
      style="font-size: 12px; line-height: 16px; color: #63656e;"
      tag="div">
      <span>{{ text }}</span>
      <RouterLink
        target="_blank"
        :to="{
          name: 'SelfServiceMyTickets',
          query: {
            filterId: data.ticket_id,
          },
        }">
        {{ $t('我的服务单') }}
      </RouterLink>
    </I18nT>
  </span>
  <slot
    v-else
    :disabled="false" />
</template>

<script setup lang="ts">
  import tippy, {
    type Instance,
    type SingleTarget,
  } from 'tippy.js';
  import {
    ref,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { TicketTypes } from '@common/const';

  interface Props {
    data?: {
      cluster_id: number,
      flow_id: number,
      status: string,
      ticket_id: number,
      ticket_type: string,
      title: string,
    },
    clusterStatus: string,
    disabledList: Array<string>
  }

  const props = defineProps<Props>();
  const { t } = useI18n();

  const textMap: Record<string, string> = {
    [TicketTypes.REDIS_DESTROY]: t('删除任务执行中'),
    [TicketTypes.REDIS_PROXY_CLOSE]: t('禁用任务执行中'),
    [TicketTypes.REDIS_PROXY_OPEN]: t('启用任务执行中'),
  };

  const text = computed(() => {
    if (props.data?.ticket_type) {
      return textMap[props.data.ticket_type];
    }

    return '';
  });

  const disabled = computed(() => {
    if (props.clusterStatus === 'unavailable') return true;

    const ticketType = props.data?.ticket_type;
    return ticketType && props.disabledList.includes(ticketType);
  });

  const rootRef = ref();
  const popRef = ref();

  let tippyIns:Instance;

  const destroyInst = () => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
    }
  };

  watch(disabled, () => {
    if (disabled.value) {
      destroyInst();
      nextTick(() => {
        tippyIns = tippy(rootRef.value as SingleTarget, {
          content: popRef.value.$el,
          placement: 'top',
          appendTo: () => document.body,
          theme: 'light',
          maxWidth: 'none',
          // trigger: 'manual',
          interactive: true,
          arrow: true,
          offset: [0, 8],
          zIndex: 999999,
          hideOnClick: true,
        });
      });
    }
  }, { immediate: true });

  onBeforeUnmount(() => {
    destroyInst();
  });
</script>
<style lang="less" scoped>
  .cluster-operation-status-tips {
    display: inline-block;
  }
</style>
