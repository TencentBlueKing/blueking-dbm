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
    class="operation-more-main"
    @click="handleClickMore">
    <BkButton
      class="mr-4"
      text
      theme="primary">
      {{ t('更多') }}
    </BkButton>
    <DbIcon
      class="more-icon"
      :class="{ 'more-icon-active': isRotate }"
      type="down-shape" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  const { t } = useI18n();

  const isRotate = ref(false);

  const handleClickMore = () => {
    isRotate.value = !isRotate.value;
  };
</script>
<style lang="less" scoped>
  .operation-more-main {
    color: #3a84ff;
    display: flex;
    align-items: center;
    cursor: pointer;

    .more-icon {
      transform: rotate(0deg);
      transition: all 0.5s;

      &-avtive {
        transform: rotate(180deg);
      }
    }
  }
</style>
