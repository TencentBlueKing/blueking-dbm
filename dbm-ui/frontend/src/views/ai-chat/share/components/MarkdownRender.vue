<template>
  <div class="report-share-markdown-layout">
    <div
      v-if="headingList.length > 0"
      class="report-share-markdown-nav">
      <div class="report-share-markdown-nav-list">
        <div
          v-for="item in headingList"
          :key="item.id"
          class="report-share-markdown-nav-item"
          :class="{
            'is-active': item.id === activeHeadingId,
          }"
          :style="{ paddingLeft: `${(item.level - 1) * 12 + 12}px` }"
          :title="item.text"
          @click="handleNavClick(item)">
          {{ item.text }}
        </div>
      </div>
    </div>
    <div
      ref="contentRef"
      v-bk-xss-html="renderContent"
      class="report-share-markdown-container"
      @scroll="handleContentScroll" />
  </div>
</template>
<script setup lang="ts">
  import MarkdownIt from 'markdown-it';

  interface Props {
    content: string;
  }

  interface HeadingItem {
    id: string;
    level: number;
    text: string;
  }

  const props = defineProps<Props>();

  const contentRef = useTemplateRef('contentRef');

  const headingList = shallowRef<HeadingItem[]>([]);
  const activeHeadingId = ref('');

  let isScrollingByClick = false;
  let scrollTimer = -1;

  // 解析 markdown，为标题添加锚点 id，并提取标题层级列表用于左侧导航
  const renderContent = computed(() => {
    if (!props.content) {
      headingList.value = [];
      return '';
    }

    const md = MarkdownIt();
    const tokens = md.parse(props.content, {});
    const list: HeadingItem[] = [];

    tokens.forEach((token, index) => {
      if (token.type !== 'heading_open') {
        return;
      }
      const level = Number(token.tag.slice(1));
      const inlineToken = tokens[index + 1];
      const text = inlineToken?.content ?? '';
      const id = `report-share-heading-${list.length}`;
      token.attrSet('id', id);
      list.push({
        id,
        level,
        text,
      });
    });

    headingList.value = list;
    return md.renderer.render(tokens, md.options, {});
  });

  const handleNavClick = (item: HeadingItem) => {
    const containerEl = contentRef.value;
    if (!containerEl) {
      return;
    }
    const targetEl = containerEl.querySelector<HTMLElement>(`#${item.id}`);
    if (!targetEl) {
      return;
    }

    activeHeadingId.value = item.id;
    isScrollingByClick = true;
    containerEl.scrollTo({
      behavior: 'smooth',
      top: targetEl.offsetTop - containerEl.offsetTop,
    });

    clearTimeout(scrollTimer);
    scrollTimer = setTimeout(() => {
      isScrollingByClick = false;
    }, 600);
  };

  // 根据滚动位置高亮当前所在标题
  const handleContentScroll = () => {
    if (isScrollingByClick) {
      return;
    }
    const containerEl = contentRef.value;
    if (!containerEl) {
      return;
    }

    const scrollTop = containerEl.scrollTop;
    let currentId = headingList.value[0]?.id ?? '';

    for (const item of headingList.value) {
      const targetEl = containerEl.querySelector<HTMLElement>(`#${item.id}`);
      if (!targetEl) {
        continue;
      }
      if (targetEl.offsetTop - containerEl.offsetTop - 8 <= scrollTop) {
        currentId = item.id;
      } else {
        break;
      }
    }

    activeHeadingId.value = currentId;
  };

  watch(headingList, () => {
    activeHeadingId.value = headingList.value[0]?.id ?? '';
  });

  onBeforeUnmount(() => {
    clearTimeout(scrollTimer);
  });
</script>
<style lang="postcss">
  .report-share-markdown-layout {
    display: flex;
    justify-content: center;
    width: 100%;
    height: calc(100vh - 150px - var(--notice-height));
    margin-top: 20px;

    .report-share-markdown-nav {
      position: fixed;
      top: calc(var(--notice-height) + 124px);
      left: calc(50vw - 656px);
      display: flex;
      flex-direction: column;
      width: 240px;
      max-height: calc(100vh - 150px - var(--notice-height));
      padding: 16px 0;
      overflow: hidden;
      background-color: #fff;
      border-radius: 2px;

      .report-share-markdown-nav-title {
        padding: 0 16px 12px;
        font-size: 14px;
        font-weight: bold;
        color: #313238;
        border-bottom: 1px solid #eaebf0;
      }

      .report-share-markdown-nav-list {
        flex: 1;
        overflow-y: auto;
      }

      .report-share-markdown-nav-item {
        overflow: hidden;
        font-size: 12px;
        line-height: 32px;
        color: #63656e;
        text-overflow: ellipsis;
        white-space: nowrap;
        cursor: pointer;
        border-left: 2px solid transparent;
        transition: all 0.2s;

        &:hover {
          color: #3a84ff;
          background-color: #f0f5ff;
        }

        &.is-active {
          color: #3a84ff;
          background-color: #e1ecff;
          border-left-color: #3a84ff;
        }
      }
    }

    .report-share-markdown-container {
      width: 800px;
      height: 100%;
      max-width: 80%;
      padding: 16px 20px;
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
        scroll-margin-top: 8px;
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

      table {
        width: 95%;
        margin-bottom: 20px;
        margin-left: 10px;
        word-break: break-all;
        border-collapse: collapse;
        border-color: #dcdee5;
        border-spacing: 0;
        border-style: solid;
        border-width: 1px;
        table-layout: fixed;

        tr {
          th,
          td {
            padding: 8px;
            text-align: left;
            vertical-align: middle;
            border: 1px solid #dcdee5;
            border-color: #ced4d9;
          }

          th {
            word-break: keep-all;
            background-color: #fafbfd;
          }
        }
      }
    }
  }
</style>
