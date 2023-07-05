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
    class="collapse-mini"
    :class="[{ 'collapse-mini--collapse': state.collapse }]">
    <div
      class="collapse-mini__header"
      @click="handleToggle">
      <i class="db-icon-down-big collapse-mini__icon" />
      <slot name="title">
        <I18nT
          keypath="共n个"
          tag="span">
          <strong style="color: #3a84ff;">{{ count }}</strong>
        </I18nT>
      </slot>
    </div>

    <Transition mode="in-out">
      <div
        v-show="state.collapse"
        class="collapse-mini__content">
        <slot />
      </div>
    </Transition>
  </div>
</template>
<script lang="ts">
  export default {
    name: 'CollapseMini',
  };
</script>

<script setup lang="ts">
  interface Props {
    collapse: boolean;
    count: number;
  }
  const props = withDefaults(defineProps<Props>(), {
    collapse: true,
    count: 0,
  });

  const state = ref({
    collapse: props.collapse,
  });

  watch(() => props.collapse, () => {
    state.collapse = props.collapse;
  });

  function handleToggle() {
    state.collapse = !state.collapse;
  }
</script>

<style lang="less" scoped>
  @import "@styles/mixins.less";

  .collapse-mini {
    margin-top: 16px;

    &:first-child {
      margin-top: 0;
    }

    &__header {
      height: 24px;
      padding-bottom: 4px;
      cursor: pointer;
      .flex-center();
    }

    &__icon {
      font-size: @font-size-normal;
      transform: rotate(-90deg);
      transition: all 0.2s;
    }

    &--collapse {
      .collapse-mini__icon {
        transform: rotate(0);
      }
    }
  }
</style>
