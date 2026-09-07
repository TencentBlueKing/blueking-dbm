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
  <TextAll
    v-if="data === 'ALL'"
    style="font-size: 12px; color: #3a84ff" />
  <DbIcon
    v-else-if="isSpinning"
    style="color: #3a84ff"
    svg
    type="sync-pending" />
  <div
    v-else-if="currentStatus"
    class="status-round-main"
    :style="{ background: currentStatus.background, borderColor: currentStatus.borderColor }" />
  <span v-else />
</template>
<script setup lang="ts">
  import { TextAll } from 'bkui-vue/lib/icon';

  import { NODE_STATUS_META, type NodeDisplayStatus } from '@views/task-history/detail/utils';

  interface Props {
    data?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: '',
  });

  // 执行中、准备中画的是旋转图标，没有圆点配色，dotFill 缺省即表示不画圆点
  const currentStatus = computed(() => {
    const meta = NODE_STATUS_META[props.data as NodeDisplayStatus];
    if (!meta?.dotFill) {
      return undefined;
    }
    return {
      background: meta.dotFill,
      borderColor: meta.color,
    };
  });

  const isSpinning = computed(() => ['READY', 'RUNNING'].includes(props.data));
</script>
<style lang="less">
  .status-round-main {
    width: 8px;
    height: 8px;
    border: 1px solid transparent;
    border-radius: 4px;
  }
</style>
