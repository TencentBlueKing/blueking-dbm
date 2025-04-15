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
    v-if="data.length"
    class="result-panel-tips-main">
    <template v-for="(item, index) in data">
      <TipItem
        v-if="item"
        :key="index"
        :data="item" />
    </template>
  </div>
  <BkException
    v-else
    class="mt-30 mb-30"
    :description="t('暂无提示')"
    scene="part"
    type="empty" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TipItem from './components/Tip.vue';

  interface Props {
    data?: string[];
  }

  withDefaults(defineProps<Props>(), {
    data: () => [],
  });

  const { t } = useI18n();
</script>
<style lang="less" scoped>
  .result-panel-tips-main {
    display: flex;
    flex-direction: column;
    margin-top: 8px;
  }
</style>
