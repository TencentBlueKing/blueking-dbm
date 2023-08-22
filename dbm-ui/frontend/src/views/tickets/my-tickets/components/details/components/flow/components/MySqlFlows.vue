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
      <p v-if="content.flow_type === 'DESCRIBE_TASK'">
        {{ $t('执行完成_共执行') }}
        <span class="sql-count">{{ sqlFileTotal }}</span>
        {{ $t('个SQL文件_成功') }}
        <span class="sql-count success">{{ counts.success }}</span>
        {{ $t('个_待执行') }}
        <span class="sql-count warning">{{ notExecutedCount }}</span>
        {{ $t('个_失败') }}
        <span class="sql-count danger">{{ counts.fail }}</span>
        {{ $t('个') }}
        <template v-if="content.summary">
          ，{{ $t('耗时') }}：{{ getCostTimeDisplay(content.cost_time) }}，
        </template>
        <BkButton
          text
          theme="primary"
          @click="handleClickDetails">
          {{ $t('查看详情') }}
        </BkButton>
      </p>
      <FlowContent
        v-else
        :content="content"
        @fetch-data="handleFetchData" />
    </template>
  </BkTimeline>
  <BkSideslider
    :is-show="isShow"
    render-directive="if"
    :title="$t('模拟执行_日志详情')"
    :width="960"
    @closed="handleClose">
    <SqlFileComponent
      :node-id="nodeId"
      :root-id="rootId" />
  </BkSideslider>
</template>

<script setup lang="tsx">
  import type { FlowItem } from '@services/types/ticket';

  import SqlFileComponent from '@views/tickets/common/components/demand-factory/mysql/LogDetails.vue';
  import FlowIcon from '@views/tickets/common/components/flow-content/components/FlowIcon.vue';
  import FlowContent from '@views/tickets/common/components/flow-content/Index.vue';
  import useLogCounts from '@views/tickets/common/hooks/logCounts';

  import { getCostTimeDisplay } from '@utils';

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

  const { counts, fetchVersion } = useLogCounts();
  const isShow = ref(false);
  const notExecutedCount = computed(() => {
    const count = sqlFileTotal.value - counts.success - counts.fail;
    return count >= 0 ? count : 0;
  });

  const flowTimeline = computed(() => props.flows.map((flow: FlowItem) => ({
    tag: flow.flow_type_display,
    type: 'default',
    filled: true,
    content: flow,
    // color,
    icon: () => <FlowIcon data={flow} />,
  })));

  const sqlFileTotal = computed(() => props.flows[0]?.details?.ticket_data?.execute_sql_files?.length || 0);
  const rootId = computed(() => props.flows[0]?.details?.ticket_data?.root_id);
  const nodeId = computed(() => props.flows[0]?.details?.ticket_data?.semantic_node_id);

  watch([rootId, nodeId], ([rootId, nodeId]) => {
    if (rootId && nodeId) {
      fetchVersion(rootId, nodeId);
    }
  }, { immediate: true });

  const handleFetchData = () => {
    emits('fetch-data');
  };

  function handleClickDetails() {
    isShow.value = true;
  }

  function handleClose() {
    isShow.value = false;
  }
</script>

<style lang="less" scoped>
:deep(.bk-modal-content) {
  height: 100%;
  padding: 15px;
}

.sql-count {
  font-weight: 700;

  &.success {
    color: @success-color;
  }

  &.warning {
    color: @warning-color;
  }

  &.danger {
    color: @danger-color;
  }
}
</style>
