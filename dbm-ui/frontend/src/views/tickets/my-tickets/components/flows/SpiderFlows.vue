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
  <BkTimeline :list="flowTimeline">
    <template #default="item">
      <span>{{ item.tag }}</span>
      <BkPopover
        :content="t('总任务/成功/失败/忽略')">
        <span class="tag">
          <span class="default"> (</span>
          <span class="default"> 1 </span>
          <span class="default">/</span>
          <span class="success"> 1 </span>
          <span class="default">/</span>
          <span class="danger"> 1 </span>
          <span class="default">/</span>
          <span class="warning"> 1 </span>
          <span class="default">)</span>
        </span>
      </BkPopover>
    </template>
    <template #content="{content}">
      <FlowContent
        :content="content"
        @fetch-data="handleFetchData" />
    </template>
  </BkTimeline>
</template>

<script setup lang="tsx">
  import type { PropType } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { FlowItem } from '@services/types/ticket';

  import FlowContent from '../../../components/FlowContent.vue';
  import FlowIcon from '../../../components/FlowIcon.vue';

  interface Emits {
    (e: 'fetch-data'): void
  }

  const props = defineProps({
    flows: {
      type: Array as PropType<FlowItem[]>,
      default: () => [],
    },
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const flowTimeline = computed(() => props.flows.map((flow: FlowItem) => ({
    tag: flow.flow_type_display,
    type: 'default',
    filled: true,
    content: flow,
    icon: () => <FlowIcon data={flow} />,
  })));

  const handleFetchData = () => {
    emits('fetch-data');
  };

</script>

<style lang="less" scoped>
.tag {
  & .default {
    color: @default-color;
  }

  & .success {
    color: @success-color;
  }

  & .warning {
    color: @warning-color;
  }

  & .danger {
    color: @danger-color;
  }
}
</style>
