<template>
  <div
    ref="rootRef"
    class="dbm-tag-block">
    <template v-if="data && data.length">
      <BkTag
        v-for="item in renderData"
        :key="item">
        {{ item }}
      </BkTag>
      <BkTag
        v-if="moreTagCount > 0"
        key="more"
        ref="moreRef">
        +{{ moreTagCount }}
      </BkTag>
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
      <BkTag
        v-for="item in data"
        :key="item">
        {{ item }}
      </BkTag>
    </div>
    <div style="display: none">
      <div
        ref="tipsPanel"
        class="dbm-tag-block-more-panel">
        <BkTag
          v-for="item in data.slice(renderData.length)"
          :key="item">
          {{ item }}
        </BkTag>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { throttle } from 'lodash';
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { computed, nextTick, onBeforeUnmount, onMounted, ref, useTemplateRef, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { execCopy } from '@utils';

  interface Props {
    data: Array<string>;
    copyenable?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    max: 0,
    copyenable: false,
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

        const allTagEleList = Array.from(tagListRef.value!.querySelectorAll('.bk-tag'));
        if (tagListRef.value!.getBoundingClientRect().width + copyBtnWidth <= maxWidth || props.data.length === 1) {
          renderTagNum.value = props.data.length;
        } else {
          const tagMargin = 6;
          let totalTagWidth = -tagMargin;
          for (let i = 0; i < allTagEleList.length; i++) {
            const { width: tagWidth } = allTagEleList[i].getBoundingClientRect();
            totalTagWidth += tagWidth + tagMargin;
            if (totalTagWidth + tipsTagPlaceholderWidth + copyBtnWidth <= maxWidth) {
              renderTagCount = renderTagCount + 1;
            } else {
              break;
            }
          }
          renderTagNum.value = Math.max(renderTagCount, 1);
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
          content: tipsPanelRef.value as Element,
          placement: 'top',
          allowHTML: true,
          appendTo: () => document.body,
          theme: 'light',
          interactive: true,
          arrow: true,
          maxWidth: 400,
          offset: [0, 8],
          zIndex: 999999,
          hideOnClick: true,
          trigger: 'mouseenter',
        });
      });
    },
    {
      deep: true,
      immediate: true,
    },
  );

  const handleCopy = () => {
    execCopy(props.data.join('\n'), t('复制成功'));
  };

  let resizeObserver: any;
  onMounted(() => {
    calcRenderTagNum();

    const resizeObserver = new ResizeObserver(
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

    .bk-tag {
      margin-right: 0;
      margin-left: 0;

      & ~ .bk-tag {
        margin-left: 6px;
      }
    }

    .copy-btn {
      display: inline-block;
      padding-left: 8px;
      cursor: pointer;
      opacity: 0%;

      &:hover {
        color: #3a84ff;
      }
    }
  }

  .dbm-tag-block-more-panel {
    margin-top: -8px;

    .bk-tag {
      margin-top: 8px;
    }
  }
</style>
