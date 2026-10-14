<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<!-- 改单新增出口词的已结束节点：{处理人} 已处理（{出口}），协助人：{协助人}，耗时：{耗时} -->
<template>
  <I18nT
    v-if="helperList.length > 0"
    keypath="n 已处理_c_协助人_h_耗时 t"
    scope="global">
    <bk-user-display-name :user-id="operator" />
    <span :style="{ color: exitColor }">{{ exitText }}</span>
    <bk-user-display-name :user-id="helperList.join(',')" />
    <CostTimer
      :is-timing="false"
      :start-time="startTime"
      :value="costTime" />
  </I18nT>
  <I18nT
    v-else
    keypath="n 已处理_c_耗时 t"
    scope="global">
    <bk-user-display-name :user-id="operator" />
    <span :style="{ color: exitColor }">{{ exitText }}</span>
    <CostTimer
      :is-timing="false"
      :start-time="startTime"
      :value="costTime" />
  </I18nT>
</template>
<script setup lang="ts">
  import CostTimer from '@components/cost-timer/CostTimer.vue';

  interface Props {
    costTime: number;
    exitColor: string;
    exitText: string;
    operator: string;
    // 该步骤待办的处理人集合，去掉实际处理人后作为协助人展示
    operators: string[];
    startTime: number;
  }

  const props = defineProps<Props>();

  const helperList = computed(() => props.operators.filter((item) => item !== props.operator));
</script>
