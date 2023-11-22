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
  <BkTag
    class="tag-box"
    :class="extCls"
    :theme="theme"
    :type="type"
    @click="handleTagClick">
    <template
      v-if="iconType"
      #icon>
      <DbIcon
        class="icon-dander"
        :type="iconType" />
    </template>
    {{ content }}
  </BkTag>
</template>

<script setup lang="ts">
  interface Props {
    content?: string | number,
    type?: '' | 'stroke' | 'filled',
    theme?: 'info' | 'success' | 'warning' | 'danger',
    iconType?: string,
    extCls?: string
  }

  interface Emits {
    (e: 'tag-click'): void
  }

  withDefaults(defineProps<Props>(), {
    content: '',
    type: '',
    theme: undefined,
    iconType: '',
    extCls: undefined,
  });

  const emits = defineEmits<Emits>();

  const handleTagClick = () => {
    emits('tag-click');
  };
</script>

<style lang="less" scoped>
  .tag-box{
    padding: 0 6px;
    margin: 0;
    transform: scale(0.83, 0.83);

  }
</style>
