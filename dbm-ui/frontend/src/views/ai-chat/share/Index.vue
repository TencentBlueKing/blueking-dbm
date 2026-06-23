<template>
  <div
    v-bk-xss-html="renderLogContent"
    class="report-share-markdowm-container" />
</template>
<script setup lang="ts">
  import MarkdownIt from 'markdown-it';
  import { useRequest } from 'vue-request';
  import { useRoute } from 'vue-router';

  import { getReportShare } from '@services/source/dbReport';

  const route = useRoute();
  const recordId = route.params.recordId as string;

  const { data: reportShare } = useRequest(getReportShare, {
    defaultParams: [
      {
        record_id: recordId,
      },
    ],
  });

  const renderLogContent = computed(() => {
    if (!reportShare.value) {
      return '';
    }
    return MarkdownIt().render(reportShare.value.content);
  });
</script>
<style lang="postcss">
  .report-share-markdowm-container {
    width: 800px;
    height: calc(100vh - 150px - var(--notice-height));
    max-width: 80%;
    padding: 16px 20px;
    margin: 0 auto;
    overflow-y: auto;
    font-size: 12px;
    line-height: 1.68;
    color: #313238;
    background-color: #fff;

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

    h1 {
      font-size: 22px;
    }

    h2 {
      font-size: 20px;
    }

    h3 {
      font-size: 18px;
    }

    h4 {
      font-size: 16px;
    }

    h5 {
      font-size: 14px;
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
