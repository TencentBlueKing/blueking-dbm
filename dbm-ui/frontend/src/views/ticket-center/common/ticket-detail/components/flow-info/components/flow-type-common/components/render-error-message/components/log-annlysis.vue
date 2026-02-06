<template>
  <div ref="root">
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
        class="log-annlysis-markdowm-container"
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

  type Emits = (e: 'elementHeightChange', height: number) => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const { t } = useI18n();

  const rootRef = useTemplateRef<HTMLDivElement>('root');
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

  watch(renderLogContent, () => {
    nextTick(() => {
      emits('elementHeightChange', rootRef.value?.getBoundingClientRect().height || 0);
    });
  });
</script>

<style lang="postcss">
  .log-annlysis-markdowm-container {
    font-size: 12px;
    color: #313238;

    h1,
    h2,
    h3,
    h4,
    h5 {
      height: auto;
      margin: 10px 0;
      font:
        normal 12px/1.5 'Helvetica Neue',
        Helvetica,
        Arial,
        'Lantinghei SC',
        'Hiragino Sans GB',
        'Microsoft Yahei',
        sans-serif;
      font-size: 12px;
      font-weight: bold;
      color: #34383e;
    }

    em {
      font-style: italic;
    }

    div,
    p,
    font,
    span,
    li {
      line-height: 1.3;
    }

    p {
      margin: 0 0 1em;
    }

    table,
    table p {
      margin: 0;
    }

    ul,
    ol {
      padding: 0;
      margin: 0 0 1em 2em;
      text-indent: 0;
    }

    ul {
      padding: 0;
      margin: 10px 0 10px 15px;
      list-style-type: none;
    }

    ol {
      padding: 0;
      margin: 10px 0 10px 25px;
    }

    ol > li {
      line-height: 1.8;
      white-space: normal;
      list-style: decimal;
    }

    ul > li {
      padding-left: 15px !important;
      line-height: 1.8;
      white-space: normal;

      &::before {
        float: left;
        width: 6px;
        height: 6px;
        margin-top: calc(0.9em - 5px);
        margin-left: -15px;
        background: #000;
        border-radius: 50%;
        content: '';
      }
    }

    li > ul {
      margin-bottom: 10px;
    }

    li ol {
      padding-left: 20px !important;
    }

    ul ul,
    ul ol,
    ol ol,
    ol ul {
      margin-bottom: 0;
      margin-left: 20px;
    }

    ul.list-type-1 > li {
      padding-left: 0 !important;
      margin-left: 15px !important;
      list-style: circle !important;
      background: none !important;
    }

    ul.list-type-2 > li {
      padding-left: 0 !important;
      margin-left: 15px !important;
      list-style: square !important;
      background: none !important;
    }

    ol.list-type-1 > li {
      list-style: lower-greek !important;
    }

    ol.list-type-2 > li {
      list-style: upper-roman !important;
    }

    ol.list-type-3 > li {
      list-style: cjk-ideographic !important;
    }

    pre,
    code {
      width: 95%;
      padding: 0 3px 2px;
      font-family: Monaco, Menlo, Consolas, 'Courier New', monospace;
      font-size: 12px;
      color: #333;
      border-radius: 3px;
    }

    code {
      padding: 2px 4px;
      font-family: Consolas, monospace, tahoma, Arial;
      color: #d14;
      border: 1px solid #e1e1e8;
    }

    pre {
      display: block;
      padding: 9.5px;
      margin: 0 0 10px;
      font-family: Consolas, monospace, tahoma, Arial;
      font-size: 13px;
      word-break: break-all;
      overflow-wrap: break-word;
      white-space: pre-wrap;
      background-color: #f6f6f6;
      border: 1px solid #ddd;
      border: 1px solid rgb(0 0 0 / 15%);
      border-radius: 2px;
    }

    pre code {
      padding: 0;
      white-space: pre-wrap;
      border: 0;
    }

    blockquote {
      padding: 0 0 0 14px;
      margin: 0 0 20px;
      border-left: 5px solid #dfdfdf;
    }

    blockquote p {
      margin-bottom: 0;
      font-size: 12px;
      font-weight: 300;
      line-height: 25px;
    }

    blockquote small {
      display: block;
      line-height: 20px;
      color: #999;
    }

    blockquote small::before {
      content: '\2014 \00A0';
    }

    blockquote::before,
    blockquote::after {
      content: '';
    }
  }
</style>
