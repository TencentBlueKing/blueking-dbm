<template>
  <div
    ref="rootRef"
    class="dbm-tag-block">
    <template v-if="data && data.length">
      <DbTag
        v-for="item in renderData"
        :key="item"
        :size="size"
        :theme="theme">
        {{ item }}
      </DbTag>
      <DbTag
        v-if="moreTagCount > 0"
        key="more"
        ref="moreRef"
        :size="size"
        :theme="theme">
        +{{ moreTagCount }}
      </DbTag>
      <div
        v-if="copyenable"
        v-bk-tooltips="t('复制所有')"
        class="copy-btn"
        @click.stop="handleCopy">
        <DbIcon type="copy" />
      </div>
    </template>
    <span v-else>--</span>
    <div
      v-if="isCalcRenderTagNum"
      ref="tagList"
      style="position: absolute; word-break: keep-all; white-space: nowrap; visibility: hidden">
      <DbTag
        v-for="item in data"
        :key="item"
        :size="size"
        :theme="theme">
        {{ item }}
      </DbTag>
    </div>
    <div style="display: none">
      <div
        ref="tipsPanel"
        class="dbm-tag-block-more-panel">
        <DbTag
          v-for="item in data.slice(renderData.length)"
          :key="item"
          :size="size"
          :theme="theme">
          {{ item }}
        </DbTag>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { throttle } from 'lodash';
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { computed, nextTick, onBeforeUnmount, onMounted, ref, useTemplateRef, watch } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import type DbTag from '@components/bkui-vue/tag/Index.vue';

  import { execCopy } from '@utils';

  interface Props {
    copyData?: Array<string>;
    copyenable?: boolean;
    data: Array<string>;
    size?: 'default' | 'small';
    // eslint-disable-next-line vue/require-default-prop
    theme?: ComponentProps<typeof DbTag>['theme'];
  }

  const props = withDefaults(defineProps<Props>(), {
    copyData: undefined,
    copyenable: false,
    max: 0,
    size: 'default',
  });

  const { t } = useI18n();
  const rootRef = ref();
  const moreRef = ref();
  const tagListRef = useTemplateRef('tagList');
  const tipsPanelRef = useTemplateRef('tipsPanel');
  const renderTagNum = ref(1);
  const isCalcRenderTagNum = ref(false);

  const renderData = computed(() => props.data.slice(0, renderTagNum.value));

  const moreTagCount = computed(() => props.data.length - renderTagNum.value);

  let tippyIns: Instance | undefined;

  const calcRenderTagNum = () => {
    // next 确保组件是 mounted 状态
    nextTick(() => {
      if (!rootRef.value || props.data.length < 1) {
        return;
      }
      isCalcRenderTagNum.value = true;
      // setTimeout 确保 isCalcRenderTagNum 已经生效
      nextTick(() => {
        const { width: maxWidth } = rootRef.value.getBoundingClientRect();

        renderTagNum.value = 0;

        let renderTagCount = 0;
        const tipsTagPlaceholderWidth = 45;
        const copyBtnWidth = props.copyenable ? 30 : 0;

        const allTagEleList = Array.from(tagListRef.value!.querySelectorAll('.dbm-tag'));
        if (tagListRef.value!.getBoundingClientRect().width + copyBtnWidth <= maxWidth) {
          renderTagNum.value = props.data.length;
        } else {
          const tagMargin = 6;
          let totalTagWidth = -tagMargin;

          for (let i = 0; i < allTagEleList.length; i++) {
            const { width: tagWidth } = allTagEleList[i].getBoundingClientRect();

            // 检查当前tag是否超过可用宽度
            const availableWidth =
              maxWidth - copyBtnWidth - (i < allTagEleList.length - 1 ? tipsTagPlaceholderWidth : 0);
            if (tagWidth > availableWidth) {
              // 如果单个tag就超过可用宽度，不计入显示
              break;
            }

            totalTagWidth += tagWidth + tagMargin;
            if (totalTagWidth + tipsTagPlaceholderWidth + copyBtnWidth <= maxWidth) {
              renderTagCount = renderTagCount + 1;
            } else {
              break;
            }
          }
          renderTagNum.value = renderTagCount;
        }

        isCalcRenderTagNum.value = false;
      });
    });
  };

  watch(
    () => props.data,
    () => {
      calcRenderTagNum();
    },
    {
      immediate: true,
    },
  );
  watch(
    moreTagCount,
    () => {
      if (moreTagCount.value < 1) {
        if (tippyIns) {
          tippyIns.hide();
          tippyIns.disable();
          tippyIns.destroy();
          tippyIns = undefined;
        }
        return;
      }

      nextTick(() => {
        if (tippyIns) {
          tippyIns.enable();
          return;
        }
        tippyIns = tippy(moreRef.value.$el as SingleTarget, {
          allowHTML: true,
          appendTo: () => document.body,
          arrow: true,
          content: tipsPanelRef.value as Element,
          hideOnClick: true,
          interactive: true,
          maxWidth: 400,
          offset: [0, 8],
          placement: 'top',
          theme: 'light',
          trigger: 'mouseenter',
          zIndex: 999999,
        });
      });
    },
    {
      deep: true,
      immediate: true,
    },
  );

  const handleCopy = () => {
    const dataList = props.copyData || props.data;
    execCopy(dataList.join('\n'), t('复制成功，共n条', { n: dataList.length }));
  };

  let resizeObserver: any;
  onMounted(() => {
    calcRenderTagNum();

    resizeObserver = new ResizeObserver(
      throttle(() => {
        calcRenderTagNum();
      }),
    );
    resizeObserver.observe(rootRef.value);
  });

  onBeforeUnmount(() => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
    }
    resizeObserver?.disconnect();
  });
</script>
<style lang="postcss">
  .dbm-tag-block {
    position: relative;
    display: block;
    overflow: hidden;
    word-break: keep-all;
    white-space: nowrap;

    .label-text {
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    &:hover {
      .copy-btn {
        opacity: 100%;
      }
    }

    .dbm-tag {
      max-width: calc(100% - 40px);

      & ~ .dbm-tag {
        margin-left: 6px;
      }
    }

    .copy-btn {
      display: inline-block;
      padding-left: 8px;
      color: #3a84ff;
      cursor: pointer;
      opacity: 0%;

      &:hover {
        color: #3a84ff;
      }
    }
  }

  .dbm-tag-block-more-panel {
    margin-top: -8px;

    .dbm-tag {
      margin-top: 8px;
    }
  }
</style>
