<template>
  <div>
    <BkAlert
      class="mb-12"
      theme="warning">
      <template #title>
        {{
          t(
            'Al 日志分析基于大模型生成，汇总单据所有错误节点输出解析结果。结果生成存在一定延时，如有疑问可联系 DBA 咨询，',
          )
        }}
      </template>
    </BkAlert>
    <!-- eslint-disable vue/no-v-html -->
    <BkLoading :loading="isLoading">
      <div
        v-bk-xss-html="renderLogContent"
        style="min-height: 48px" />
    </BkLoading>
  </div>
</template>
<script setup lang="ts">
  import MarkdownIt from 'markdown-it';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import FlowMode from '@services/model/ticket/flow';
  import TicketModel from '@services/model/ticket/ticket';
  import { getFlowLogAnnlysis } from '@services/source/ai';

  interface Props {
    data: FlowMode<unknown, any>;
    ticketDetail: TicketModel<unknown>;
  }

  const props = defineProps<Props>();
  const { t } = useI18n();

  const { data: logContent, loading: isLoading } = useRequest(getFlowLogAnnlysis, {
    defaultParams: [
      {
        flow_id: props.data.flow_obj_id,
        ticket_id: props.ticketDetail.id,
      },
    ],
  });

  const renderLogContent = computed(() => {
    if (!logContent.value) {
      return '';
    }
    return MarkdownIt().render(logContent.value);
  });
</script>
