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
    :class="[{ 'collapse-active': localCollapse }]">
    <div
      class="collapse-header"
      @click="handleToggle">
      <div class="collapse-title">
        <slot name="title" />
      </div>
      <DbIcon
        class="collapse-icon"
        type="right-big" />
    </div>
    <Transition mode="in-out">
      <div
        v-show="localCollapse"
        class="collapse-content">
        <slot />
      </div>
    </Transition>
  </div>
</template>
<script setup lang="ts">
  import { ref } from 'vue';

  interface Props {
    collapse?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    collapse: true,
  });

  const localCollapse = ref(props.collapse);

  const handleToggle = () => {
    localCollapse.value = !localCollapse.value;
  };
</script>
<style lang="less" scoped>
  @import '@styles/mixins.less';

  .collapse {
    width: 100%;
    padding: 16px 24px;
    background-color: @bg-white;
    border: 1px solid #eaebf0;
    border-radius: 2px;

    .collapse-header {
      .flex-center();

      cursor: pointer;
      justify-content: space-between;
    }

    .collapse-title {
      .flex-center();

      font-weight: bold;
      color: @title-color;
    }

    .collapse-icon {
      font-size: @font-size-large;
      color: @gray-color;
      transition: all 0.3s;
    }

    .collapse-content {
      padding-top: 16px;
    }
  }

  .collapse-active {
    .collapse-icon {
      transform: rotate(90deg);
    }
  }
</style>
