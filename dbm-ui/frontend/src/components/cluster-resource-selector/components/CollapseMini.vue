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
  <div class="cluster-resource-selector-collapse-mini">
    <div
      class="collapse-mini-header"
      @click="handleToggle">
      <i
        class="db-icon-down-big collapse-mini-icon"
        :class="[{ 'collapse-mini-collapse': state.collapse }]" />
      <slot name="title">
        <p>
          <strong>【{{ title }}】</strong>
          <span class="mr-4">-</span>
        </p>
        <I18nT
          keypath="共m个"
          tag="span">
          <template #m>
            <strong style="color: #3a84ff">{{ count }}</strong>
          </template>
        </I18nT>
      </slot>
    </div>

    <Transition mode="in-out">
      <div
        v-show="state.collapse"
        class="collapse-mini-content">
        <slot />
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
  interface Props {
    collapse: boolean;
    count: number;
    title: string;
  }

  const props = defineProps<Props>();

  const state = reactive({
    collapse: props.collapse,
  });

  watch(
    () => props.collapse,
    () => {
      state.collapse = props.collapse;
    },
  );

  const handleToggle = () => {
    state.collapse = !state.collapse;
  };
</script>

<style lang="less" scoped>
  @import '@styles/mixins.less';

  .cluster-resource-selector-collapse-mini {
    margin-bottom: 16px;

    .collapse-mini:first-child {
      margin-top: 0;
    }

    .collapse-mini-header {
      height: 24px;
      padding-bottom: 4px;
      cursor: pointer;
      .flex-center();
    }

    .collapse-mini-icon {
      font-size: @font-size-normal;
      transform: rotate(-90deg);
      transition: all 0.2s;
    }

    .collapse-mini-collapse {
      transform: rotate(0) !important;
    }
  }
</style>
