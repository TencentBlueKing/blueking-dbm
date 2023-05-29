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
    class="collapse"
    :class="[{ 'collapse--active': localCollapse }]">
    <div
      class="collapse__header"
      @click="handleToggle">
      <div class="collapse__left">
        <slot name="title" />
      </div>
      <i class="collapse__icon db-icon-right-big" />
    </div>
    <Transition mode="in-out">
      <div
        v-show="localCollapse"
        class="collapse__content">
        <slot />
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
  const props = defineProps({
    collapse: {
      type: Boolean,
      default: true,
    },
  });

  const localCollapse = ref(props.collapse);

  const handleToggle = () => {
    localCollapse.value = !localCollapse.value;
  };
</script>

<style lang="less" scoped>
  @import "@styles/mixins.less";

  .collapse {
    width: 100%;
    padding: 16px 24px;
    background-color: @bg-white;
    border: 1px solid #eaebf0;
    border-radius: 2px;

    &__header {
      .flex-center();

      cursor: pointer;
      justify-content: space-between;
    }

    &__left {
      .flex-center();
    }

    &__icon {
      font-size: @font-size-large;
      color: @gray-color;
      transition: all 0.3s;
    }

    &__content {
      padding-top: 16px;
    }

    &--active {
      .collapse__icon {
        transform: rotate(90deg);
      }
    }
  }
</style>
