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
    <div
      class="render-text-box"
      :class="{ 'default-display': !data }">
      <span
        v-if="!data.total"
        key="empty"
        style="color: #c4c6cc">
        {{ $t('选择主机后自动生成') }}
      </span>
      <span v-else>
        <span style="color: red">{{ data.faults }}</span> / {{ data.total }}
      </span>
    </div>
  </BkLoading>
</template>
<script setup lang="ts">
  interface Props {
    data?: {
      faults: number;
      total: number;
    };
    isLoading?: boolean;
  }

  withDefaults(defineProps<Props>(), {
    data: () => ({
      faults: 0,
      total: 0,
    }),
    isLoading: false,
  });
</script>
<style lang="less" scoped>
  .render-text-box {
    width: 100%;
    padding: 10px 16px;
    overflow: hidden;
    line-height: 20px;
    color: #63656e;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .default-display {
    background: #fafbfd;
  }
</style>
