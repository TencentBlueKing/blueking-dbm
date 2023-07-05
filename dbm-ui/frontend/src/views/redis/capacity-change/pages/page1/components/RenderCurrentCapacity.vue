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
  <BkLoading :loading="isLoading">
    <div class="capacity-box">
      <span
        v-if="!data"
        key="empty"
        style="color: #c4c6cc;">
        {{ $t('选择集群后自动生成') }}
      </span>
      <div
        v-else
        class="content">
        <span style="margin-right: 5px;">{{ $t('磁盘') }}:</span>
        <BkProgress
          color="#EA3636"
          :percent="35"
          :show-text="false"
          size="small"
          :stroke-width="18"
          type="circle"
          :width="20" />
        <span class="percent">93.12%</span>
        <span class="spec">({{ data }})</span>
      </div>
    </div>
  </BkLoading>
</template>
<script setup lang="ts">
  import type { IDataRow } from './Row.vue';

  interface Props {
    data?: IDataRow['currentCapacity'];
    isLoading?: boolean;
  }

  defineProps<Props>();

</script>
<style lang="less" scoped>
.capacity-box {
  padding: 10px 16px;
  line-height: 20px;
  color: #63656e;

  .content {
    display: flex;
    align-items: center;

    .percent {
      margin-left: 4px;
      font-family: Arial-BoldMT;
      font-size: 12px;
      font-weight: bold;
      color: #313238;
    }

    .spec {
      margin-left: 2px;
      font-family: ArialMT;
      font-size: 12px;
      color: #979BA5;
    }
  }
}

</style>
