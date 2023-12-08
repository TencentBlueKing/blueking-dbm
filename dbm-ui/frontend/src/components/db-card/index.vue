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
    class="db-card"
    :class="[{
      'db-card-collapse': !isNormalMode,
      'db-card-collapse--active': notFolded
    }]">
    <div
      class="db-card__header"
      @click="handleToggle">
      <i
        v-if="!isNormalMode"
        class="db-card__icon db-icon-down-shape" />
      <span class="db-card__title">{{ title }}</span>
      <span class="db-card__desc">
        <slot name="desc">{{ desc }}</slot>
      </span>
      <div class="db-card__header-right">
        <slot name="header-right" />
      </div>
    </div>

    <Transition mode="in-out">
      <div
        v-show="localCollpase"
        class="db-card__content">
        <slot />
      </div>
    </Transition>
  </div>
</template>

<script lang="ts">
  export default {
    name: 'DbCard',
  };
</script>

<script setup lang="ts">
  interface Props {
    title?: string,
    desc?: string,
    mode?: 'normal'| 'collapse'| string,
  }

  interface Emits {
    (e: 'collapsed', value: boolean): void
  }

  const props = withDefaults(defineProps<Props>(), {
    title: '',
    desc: '',
    mode: 'normal',
  });
  const emits = defineEmits<Emits>();
  const collapse = defineModel<boolean>('collapse', {
    default: true,
  });

  const localCollpase = ref(true);
  const isNormalMode = computed(() => props.mode === 'normal');
  const notFolded = computed(() => localCollpase.value && !isNormalMode.value);

  watch(collapse, (value: boolean) => {
    if (!isNormalMode.value) {
      localCollpase.value = value;
    }
  }, { deep: true, immediate: true });

  const handleToggle = () => {
    if (isNormalMode.value) return;
    localCollpase.value = !localCollpase.value;
    collapse.value = localCollpase.value;
    emits('collapsed', localCollpase.value);
  };
</script>

<style lang="less">
  @import "@/styles/mixins.less";

  .db-card {
    padding: 24px;
    background: #fff;
    box-shadow: 0 2px 4px 0 rgb(25 25 41 / 5%);

    &__header {
      .flex-center();
    }

    &__icon {
      margin-right: 8px;
      font-size: @font-size-normal;
      transform: rotate(-90deg);
      transition: all 0.3s;
    }

    &__header-right {
      align-self: flex-end;
    }

    &__title {
      padding-right: 8px;
      font-weight: bold;
      color: @title-color;
      flex-shrink: 0;
    }

    &__desc {
      flex: 1;
      font-size: @font-size-mini;
      color: @gray-color;
    }

    &__content {
      padding-top: 24px;
    }

    &-collapse {
      .db-card__header {
        cursor: pointer;
      }

      &--active {
        .db-card__icon {
          transform: rotate(0);
        }
      }
    }
  }
</style>
