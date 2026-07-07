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
  <div class="db-cluster-instance-status">
    <DbIcon
      :class="{
        'rotate-loading': statusInfo.icon === 'sync-pending',
      }"
      svg
      :type="statusInfo.icon" />
    <span
      v-if="showText"
      style="margin-left: 4px">
      {{ statusInfo.text }}
    </span>
  </div>
</template>
<script setup lang="ts">
  import { clusterInstStatus } from '@common/const';

  interface Props {
    data: string;
    showText?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    showText: true,
  });

  const statusInfo = computed(() => {
    const status = props.data.toLowerCase();
    return clusterInstStatus[status as keyof typeof clusterInstStatus];
  });
</script>
<style lang="less">
  .db-cluster-instance-status {
    display: flex;
    align-items: center;
  }
</style>
