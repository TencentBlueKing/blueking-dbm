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
  <div style="padding: 20px">
    <ContentLoader
      :height="716"
      :width="maxWidth - 40"
      v-bind="attrs">
      <!-- eslint-disable vue/max-attributes-per-line -->
      <rect
        height="24"
        rx="2"
        :width="maxWidth"
        x="0"
        y="57" />
      <rect
        height="24"
        rx="2"
        :width="maxWidth"
        x="0"
        y="99" />
      <rect
        height="24"
        rx="2"
        :width="maxWidth"
        x="0"
        y="141" />
      <rect
        height="24"
        rx="2"
        :width="maxWidth"
        x="0"
        y="183" />
      <rect
        height="24"
        rx="2"
        :width="maxWidth"
        x="0"
        y="225" />
      <rect
        height="32"
        rx="2"
        width="480"
        :x="maxWidth - 480"
        y="0" />
      <rect
        height="32"
        rx="2"
        width="88"
        x="0"
        y="0" />
    </ContentLoader>
  </div>
</template>
<script lang="ts">
  export default {
    inheritAttrs: true,
  };
</script>
<script setup lang="ts">
  import { useAttrs } from 'vue';
  import { ContentLoader } from 'vue-content-loader';

  import { attrsOnlyProp } from '@utils';

  interface Props {
    maxWidth: number;
  }
  defineProps<Props>();

  const attrs = attrsOnlyProp(useAttrs());
</script>
