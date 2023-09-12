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
  <div
    v-if="isRender"
    class="render-cluster-opration-tag">
    <span
      ref="rootRef"
      class="tag-placeholder">
      <DbIcon
        svg
        :type="tagIcon" />
    </span>
    <I18nT
      ref="popRef"
      keypath="xx_跳转_我的服务单_查看进度"
      style="font-size: 12px; line-height: 16px; color: #63656e;"
      tag="div">
      <span>{{ tipText }}</span>
      <RouterLink
        target="_blank"
        :to="{
          name: 'SelfServiceMyTickets',
          query: {
            filterId: data!.ticket_id,
          },
        }">
        {{ $t('我的服务单') }}
      </RouterLink>
    </I18nT>
  </div>
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
    }
  }

  const props = defineProps<Props>();
  const { t } = useI18n();

  const iconMap: Record<string, string> = {
    [TicketTypes.REDIS_PROXY_OPEN]: 'qiyongzhong',
    [TicketTypes.REDIS_PROXY_CLOSE]: 'jinyongzhong',
    [TicketTypes.REDIS_DESTROY]: 'shanchuzhong',
  };
  const tipsMap: Record<string, string> = {
    [TicketTypes.REDIS_DESTROY]: t('删除任务执行中'),
    [TicketTypes.REDIS_PROXY_CLOSE]: t('禁用任务执行中'),
    [TicketTypes.REDIS_PROXY_OPEN]: t('启用任务执行中'),
  };

  const tagIcon = computed(() => {
    if (props.data?.ticket_type) {
      return iconMap[props.data.ticket_type];
    }

    return '';
  });
  const tipText = computed(() => {
    if (props.data?.ticket_type) {
      return tipsMap[props.data.ticket_type];
    }

    return '';
  });
  const isRender = computed(() => tagIcon.value && tipText.value && !!props.data?.ticket_id);

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

  watch(isRender, () => {
    if (isRender.value) {
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
  .render-cluster-opration-tag {
    display: inline-block;
    margin-right: 4px;
    font-size: 0;

    .tag-placeholder {
      display: inline-block;
      font-size: 0;
    }

    .db-svg-icon {
      width: 38px;
      height: 16px;
    }
  }
</style>
