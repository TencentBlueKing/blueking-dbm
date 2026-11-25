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
    class="deploy-cluster-tag-display"
    :class="[`is-${direction}`, { 'has-tags': tagList.length > 0 }]">
    <DbTag
      v-for="item in tagList"
      :key="item.key"
      class="tag-item">
      {{ item.key }}: {{ item.value }}
    </DbTag>
    <span v-if="!tagList.length">--</span>
  </div>
</template>

<script setup lang="ts">
  interface Props {
    /** 表格内垂直排列，InfoItem 内横向排列 */
    direction?: 'horizontal' | 'vertical';
    /** 单键对象数组，如 [{"env": "prod"}]；未设置或为空展示 -- */
    tags?: Record<string, string>[];
  }

  const props = withDefaults(defineProps<Props>(), {
    direction: 'vertical',
    tags: undefined,
  });

  const tagList = computed(() =>
    (props.tags ?? []).map((item) => {
      const key = Object.keys(item)[0] ?? '';
      return {
        key,
        value: item[key] ?? '',
      };
    }),
  );
</script>

<style lang="less" scoped>
  .deploy-cluster-tag-display {
    max-width: 100%;

    &.is-horizontal {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;

      &.has-tags {
        margin-top: 6px;
      }
    }

    &.is-vertical {
      display: flex;
      flex-direction: column;
      align-items: flex-start;
      gap: 6px;

      .tag-item {
        margin-left: 0;
      }
    }

    .tag-item {
      max-width: 100%;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
</style>
