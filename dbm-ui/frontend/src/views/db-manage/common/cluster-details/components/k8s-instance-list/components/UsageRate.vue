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
  <div class="k8s-instance-list-usage-rate">
    <BkProgress
      bg-color="#EAEBF0"
      :color="color"
      :percent="percent"
      :show-text="false" />
    <span class="ml-8">
      <span class="usage-rate">{{ percent }}%</span>
    </span>
  </div>
</template>
<script setup lang="ts">
  interface Props {
    data: number;
  }

  const props = defineProps<Props>();

  const percent = computed(() => props.data || 0);

  const color = computed(() => {
    let value = '#2DCB56';

    if (percent.value >= 90) {
      value = '#EA3636';
    } else if (percent.value >= 70) {
      value = '#FF9C01';
    }

    return value;
  });
</script>

<style lang="less" scoped>
  .k8s-instance-list-usage-rate {
    display: flex;
    align-items: center;

    .usage-rate {
      font-weight: 700;
      color: #63656e;
    }

    .usage-text {
      margin-left: 2px;
      color: #979ba5;
    }
  }
</style>
