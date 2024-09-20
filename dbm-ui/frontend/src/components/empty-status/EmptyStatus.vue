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
  <BkException
    v-if="isAnomalies"
    scene="part"
    style="font-size: 12px"
    type="500">
    <div>
      <div class="mb-8">
        {{ $t('数据获取异常') }}
      </div>
      <BkButton
        text
        theme="primary"
        @click="handleRefresh">
        {{ $t('刷新') }}
      </BkButton>
    </div>
  </BkException>
  <BkException
    v-else-if="isSearching"
    scene="part"
    style="font-size: 12px"
    type="search-empty">
    <div>
      <div>{{ $t('搜索结果为空') }}</div>
      <div style="margin-top: 8px; color: #979ba5">
        {{ $t('可以尝试调整关键词或') }}
        <BkButton
          text
          theme="primary"
          @click="handleClearSearch">
          {{ $t('清空搜索条件') }}
        </BkButton>
      </div>
    </div>
  </BkException>
  <BkException
    v-else
    :description="$t('暂无数据')"
    scene="part"
    style="font-size: 12px"
    type="empty" />
</template>

<script setup lang="ts">
  interface Emits {
    (e: 'refresh'): void;
    (e: 'clearSearch'): void;
  }

  interface Props {
    isAnomalies: boolean;
    isSearching: boolean;
  }

  defineProps<Props>();
  const emits = defineEmits<Emits>();

  const handleRefresh = () => emits('refresh');
  const handleClearSearch = () => emits('clearSearch');
</script>

<style lang="less" scoped>
  .bk-exception.bk-exception-part {
    height: 260px;
    padding-top: 48px;
  }
</style>
