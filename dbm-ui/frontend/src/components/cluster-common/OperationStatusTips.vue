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
  <span>
    <span
      v-if="data?.operationDisabled"
      ref="rootRef"
      class="cluster-operation-status-tips"
      @mouseenter="handleMouseenter">
      <slot />
      <div style="display: none;">
        <div
          ref="popRef"
          style="font-size: 12px; line-height: 16px; color: #63656e;">
          <span v-if="!data.isOnline">
            {{ $t('集群已被禁用无法操作') }}
          </span>
          <I18nT
            v-else
            keypath="xx_跳转_我的服务单_查看进度"
            tag="span">
            <span>{{ data.operationStatusText }}</span>
            <RouterLink
              target="_blank"
              :to="{
                name: 'SelfServiceMyTickets',
                query: {
                  filterId: data.operationTicketId,
                },
              }">
              {{ $t('我的服务单') }}
            </RouterLink>
          </I18nT>
        </div>
      </div>
    </span>
    <slot v-else />
  </span>
</template>
<script lang="ts">
  import tippy, {
    type Instance,
    type SingleTarget,
  } from 'tippy.js';
  import {
    onBeforeUnmount,
    ref,
    watch,
  } from 'vue';

  let activeTippyIns:Instance;

</script>
<script setup lang="ts">

  interface Props {
    data?: {
      operationStatusIcon: string,
      operationStatusText: string,
      operationTicketId: number,
      operationDisabled: boolean,
      [key: string]: any
    }
  }

  const props = withDefaults(defineProps<Props>(), {
    data: () => ({} as any),
  });

  const rootRef = ref();
  const popRef = ref();

  let tippyIns:Instance | undefined;

  const handleMouseenter = () => {
    if (!tippyIns) {
      return;
    }
    if (activeTippyIns && activeTippyIns !== tippyIns) {
      activeTippyIns.hide();
    }
    tippyIns.show();
    activeTippyIns = tippyIns;
  };

  const destroyTippy = () => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
      tippyIns = undefined;
    }
  };

  watch(() => props.data, () => {
    if (props.data?.operationDisabled && !tippyIns) {
      setTimeout(() => {
        tippyIns = tippy(rootRef.value as SingleTarget, {
          content: popRef.value,
          placement: 'top',
          appendTo: () => document.body,
          theme: 'light',
          maxWidth: 'none',
          trigger: 'manual',
          interactive: true,
          arrow: true,
          offset: [0, 8],
          zIndex: 999999,
          hideOnClick: true,
        });
      });
    }
    if (!props.data.operationDisabled) {
      destroyTippy();
    }
  }, {
    immediate: true,
  });

  onBeforeUnmount(() => {
    destroyTippy();
  });
</script>
<style lang="less">
  .cluster-operation-status-tips {
    display: inline-block;

    & > * {
      pointer-events: none;
    }
  }
</style>
