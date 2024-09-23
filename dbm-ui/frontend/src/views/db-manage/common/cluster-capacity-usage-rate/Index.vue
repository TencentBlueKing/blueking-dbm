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
  <div class="cluster-capacity-usage-rate">
    <template v-if="cpuInfo">
      <BkProgress
        bg-color="#EAEBF0"
        :color="cpuInfo.color"
        :percent="cpuInfo.percent"
        :show-text="false"
        stroke-linecap="square"
        :stroke-width="14"
        type="circle"
        :width="20" />
      <span class="ml-8">
        <span class="usage-rate">{{ cpuInfo.rate }}</span>
        <span class="usage-text">{{ cpuInfo.num }}</span>
      </span>
    </template>
    <span v-else>--</span>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';

  import { bytePretty } from '@utils';

  interface Props {
    clusterStats: Record<'used' | 'total' | 'in_use', number> | Record<string, never>;
  }

  const props = defineProps<Props>();

  const cpuInfo = computed(() => {
    if (_.isEmpty(props.clusterStats)) {
      return;
    }

    let color = '#2DCB56';
    const { used = 0, total = 0, in_use: inUse = 0 } = props.clusterStats;

    if (inUse >= 90) {
      color = '#EA3636';
    } else if (inUse >= 70) {
      color = '#FF9C01';
    }

    return {
      percent: inUse,
      rate: `${inUse}%`,
      num: `(${bytePretty(used)}/${bytePretty(total)})`,
      color,
    };
  });
</script>

<style lang="less" scoped>
  .cluster-capacity-usage-rate {
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
