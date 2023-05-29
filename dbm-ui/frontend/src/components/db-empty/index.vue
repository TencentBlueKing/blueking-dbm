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
  <div class="db-empty">
    <div class="db-empty__content">
      <img
        src="@images/empty.png"
        :width="width">
      <p class="db-empty__text">
        {{ text || $t('暂无数据') }}
      </p>
    </div>
  </div>
</template>
<script lang="ts">
  export default {
    name: 'DbEmpty',
  };
</script>

<script setup lang="ts">
  defineProps({
    width: {
      type: Number,
      default: 200,
    },
    text: {
      type: String,
      default: '',
    },
  });
</script>

<style lang="less">
  .db-empty {
    position: relative;
    width: 100%;
    height: 100%;
    text-align: center;

    &__content {
      position: absolute;
      top: 20%;
      left: 50%;
      width: 100%;
      transform: translate(-50%, -50%);
    }
  }
</style>
