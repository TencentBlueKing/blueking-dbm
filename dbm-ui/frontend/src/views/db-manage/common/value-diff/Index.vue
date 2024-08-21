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
    class="value-diff"
    :class="[diffInfo.isPositive ? 'positive-value' : 'negtive-value']">
    {{ `(${rate}${diffInfo.num}${numUnit})` }}
  </span>
</template>

<script setup lang="ts">
  interface Props {
    currentValue: number;
    targetValue: number;
    showRate?: boolean;
    numUnit?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    showRate: true,
    numUnit: '',
  });

  const diffInfo = computed(() => {
    const { currentValue, targetValue, showRate } = props;

    const diff = targetValue - currentValue;
    let rate = '0';
    if (diff !== 0 && currentValue > 0 && showRate) {
      rate = ((diff / currentValue) * 100).toFixed(2);
    }
    if (diff < 0) {
      return {
        rate,
        num: diff,
        isPositive: false,
      };
    }
    return {
      rate: `+${rate}`,
      num: `+${diff}`,
      isPositive: true,
    };
  });

  const rate = computed(() => {
    if (props.showRate) {
      return `${diffInfo.value.rate}% ,`;
    }
    return '';
  });
</script>

<style lang="less" scoped>
  .value-diff {
    margin-left: 5px;
    font-size: 12px;
    font-weight: bold;

    &.positive-value {
      color: #ea3636;
    }

    &.negtive-value {
      color: #2dcb56;
    }
  }
</style>
