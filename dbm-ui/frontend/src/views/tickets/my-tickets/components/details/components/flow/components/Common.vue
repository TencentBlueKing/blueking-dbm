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
    <template #content="{content}">
      <FlowContent
        :content="content"
        @fetch-data="handleFetchData" />
    </template>
  </BkTimeline>
</template>

<script setup lang="tsx">
  import type { FlowItem } from '@services/types/ticket';

  import FlowIcon from '@views/tickets/common/components/flow-content/components/FlowIcon.vue';
  import FlowContent from '@views/tickets/common/components/flow-content/Index.vue';

  interface Props {
    flows?: FlowItem[]
  }

  interface Emits {
    (e: 'fetch-data'): void
  }
  const props = withDefaults(defineProps<Props>(), {
    flows: () => [],
  });
  const emits = defineEmits<Emits>();

  const flowTimeline = computed(() => props.flows.map((flow: FlowItem) => ({
    tag: flow.flow_type_display,
    type: 'default',
    filled: true,
    content: flow,
    // color,
    icon: () => <FlowIcon data={flow} />,
  })));

  const handleFetchData = () => {
    emits('fetch-data');
  };
</script>
