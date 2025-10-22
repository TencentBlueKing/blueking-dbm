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
    class="collapse-mini-main"
    :class="[{ 'collapse-mini-collapse': isCollapse }]">
    <div
      class="collapse-mini-header"
      @click="handleToggle">
      <i class="db-icon-down-big collapse-mini-icon" />
      <slot name="title">
        <span>{{ title ? `【${title}】` : '' }}</span>
        <p>
          {{ title ? `-` : '' }}
          <I18nT
            keypath="共n个"
            tag="span">
            <span style="font-weight: 700; color: #3a84ff">{{ countInfo.total }}</span>
          </I18nT>
          <template v-if="showUpdate">
            <template v-if="countInfo.add > 0">
              <span class="mr-4 ml-4">,</span>
              <I18nT
                keypath="新增n个"
                tag="span">
                <span style="font-weight: 700; color: #2dcb56">{{ countInfo.add }}</span>
              </I18nT>
            </template>
            <template v-if="countInfo.update > 0">
              <span class="mr-4 ml-4">,</span>
              <I18nT
                keypath="更新n个"
                tag="span">
                <span style="font-weight: 700; color: #f59500">{{ countInfo.update }}</span>
              </I18nT>
            </template>
            <template v-if="countInfo.ignore > 0">
              <span class="mr-4 ml-4">,</span>
              <I18nT
                keypath="忽略n个"
                tag="span">
                <span style="font-weight: 700; color: #75a646">{{ countInfo.ignore }}</span>
              </I18nT>
            </template>
          </template>
        </p>
      </slot>
    </div>
    <Transition mode="in-out">
      <div
        v-show="isCollapse"
        class="collapse-mini-content">
        <slot />
      </div>
    </Transition>
  </div>
</template>
<script setup lang="ts">
  interface Props {
    collapse: boolean;
    countInfo: {
      add: number;
      ignore: number;
      total: number;
      update: number;
    };
    showUpdate?: boolean;
    title: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    showUpdate: true,
  });

  const isCollapse = ref(true);

  watch(
    () => props.collapse,
    () => {
      isCollapse.value = props.collapse;
    },
  );

  const handleToggle = () => {
    isCollapse.value = !isCollapse.value;
  };
</script>

<style lang="less">
  .collapse-mini-main {
    font-size: 12px;

    .collapse-mini-header {
      display: flex;
      height: 32px;
      cursor: pointer;
      align-items: center;
    }

    .collapse-mini-icon {
      font-size: @font-size-normal;
      transform: rotate(-90deg);
      transition: all 0.2s;
    }

    .collapse-mini-content {
      max-height: 520px;
      overflow-y: auto;
    }
  }

  .collapse-mini-collapse {
    .collapse-mini-icon {
      transform: rotate(0);
    }
  }
</style>
