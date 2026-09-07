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
  <DbIcon
    v-if="iconType"
    class="flow-sign-icon-main"
    :style="{ color: iconColor }"
    :type="iconType" />
  <div
    v-else
    style="width: 24px">
    <StatusSign
      class="ml-4 mr-12"
      :data="status" />
  </div>
</template>
<script setup lang="ts">
  import { FlowTypes } from '@services/source/taskflow';

  import { NODE_STATUS_META, type NodeDisplayStatus } from '@views/task-history/detail/utils';

  import StatusSign from './StatusSign.vue';

  interface Props {
    status?: string;
    type?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    status: '',
    type: '',
  });

  const flowTypeIconMap = {
    [FlowTypes.ConditionalParallelGateway]: 'branch-gateway',
    [FlowTypes.ConvergeGateway]: 'converge-gateway',
    [FlowTypes.EmptyEndEvent]: 'jieshu',
    [FlowTypes.EmptyStartEvent]: 'kaishi',
    [FlowTypes.ParallelGateway]: 'parallel-gateway',
    [FlowTypes.SubProcess]: 'liuchengsheji',
  };

  const iconType = computed(() => flowTypeIconMap[props.type as keyof typeof flowTypeIconMap]);

  const iconColor = computed(() => {
    if (props.type === FlowTypes.EmptyStartEvent) {
      return NODE_STATUS_META.FINISHED.color;
    }
    if (props.type === FlowTypes.EmptyEndEvent) {
      return '#979BA5';
    }

    return NODE_STATUS_META[props.status as NodeDisplayStatus]?.color || NODE_STATUS_META.FINISHED.color;
  });
</script>
<style lang="less">
  .flow-sign-icon-main {
    margin-right: 7px;
    font-size: 18px;
  }
</style>
