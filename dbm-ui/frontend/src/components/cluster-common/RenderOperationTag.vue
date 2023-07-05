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
    v-if="data.operationTicketId"
    class="render-cluster-opration-tag">
    <span
      ref="rootRef"
      class="tag-placeholder"
      @mouseenter="handleMouseenter">
      <DbIcon
        svg
        :type="data.operationStatusIcon" />
    </span>
    <div ref="popRef">
      <I18nT
        keypath="xx_跳转_我的服务单_查看进度"
        style="font-size: 12px; line-height: 16px; color: #63656e;"
        tag="div">
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
</template>
<script lang="ts">
  import tippy, {
    type Instance,
    type SingleTarget,
  } from 'tippy.js';
  import {
    ref,
  } from 'vue';

  let activeTippyIns:Instance;

</script>
<script setup lang="ts">
  interface Props {
    data: {
      operationStatusIcon: string,
      operationStatusText: string,
      operationTicketId: number,
      [key: string]: any
    }
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

  watch(() => props.data.operationTicketId, () => {
    if (!props.data.operationTicketId) {
      return;
    }
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
      tippyIns = undefined;
    }

    nextTick(() => {
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
  }, { immediate: true });

  onBeforeUnmount(() => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
      tippyIns = undefined;
    }
  });
</script>
<style lang="less">
  .render-cluster-opration-tag {
    position: relative;
    display: inline-block;
    width: 38px;
    height: 16px;

    .tag-placeholder {
      position: absolute;
      top: 50%;
      margin-top: 2px;
      font-size: 38px;
      transform: translateY(-50%);
    }
  }
</style>
