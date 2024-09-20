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
      v-if="data?.operationTicketId && !disabled"
      ref="rootRef"
      class="cluster-operation-status-tips"
      @mouseenter="handleMouseenter">
      <slot />
      <div style="display: none">
        <div
          ref="popRef"
          style="font-size: 12px; line-height: 16px; color: #63656e">
          <I18nT
            keypath="xx_跳转_单据_查看进度"
            tag="span">
            <span>{{ data.operationStatusText }}</span>
            <AuthRouterLink
              action-id="ticket_view"
              :resource="data.operationTicketId"
              target="_blank"
              :to="{
                name: 'bizTicketManage',
                query: {
                  id: data.operationTicketId,
                },
              }">
              {{ $t('单据') }}
            </AuthRouterLink>
          </I18nT>
        </div>
      </div>
    </span>
    <slot v-else />
  </span>
</template>
<script lang="ts">
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';

  let activeTippyIns: Instance;
</script>
<script setup lang="ts">
  interface Props {
    data?: {
      operationStatusText: string;
      operationTicketId: number;
    };
    disabled?: boolean;
  }

  const props = defineProps<Props>();

  const rootRef = ref();
  const popRef = ref();

  let tippyIns: Instance | undefined;

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

  watch(
    () => props.data,
    () => {
      setTimeout(() => {
        if (props.data?.operationTicketId && !props.disabled && !tippyIns) {
          tippyIns = tippy(rootRef.value as SingleTarget, {
            content: popRef.value,
            placement: 'top',
            appendTo: () => document.body,
            theme: 'light',
            maxWidth: 'none',
            interactive: true,
            arrow: true,
            offset: [0, 8],
            zIndex: 999999,
            hideOnClick: true,
          });
        }
        if (!props.data?.operationTicketId) {
          destroyTippy();
        }
      });
    },
    {
      immediate: true,
    },
  );

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
