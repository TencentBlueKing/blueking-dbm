<template>
  <div
    ref="rootRef"
    class="staff-manage-tag">
    <template v-if="tagList && tagList.length">
      <BkTag
        v-for="item in renderData"
        :key="item.value"
        :theme="item.theme">
        <BkOverflowTitle type="tips">
          {{ item.label }}
        </BkOverflowTitle>
      </BkTag>
      <BkTag
        v-if="moreTagCount > 0"
        key="more"
        ref="moreRef">
        +{{ moreTagCount }}
      </BkTag>
    </template>
    <span v-else>--</span>
    <div
      v-if="isCalcRenderTagNum"
      ref="tagList"
      style="position: absolute; word-break: keep-all; white-space: nowrap; visibility: hidden">
      <BkTag
        v-for="item in tagList"
        :key="item.value"
        :theme="item.theme">
        {{ item.label }}
      </BkTag>
    </div>
    <div style="display: none">
      <div
        ref="tipsPanel"
        class="staff-manage-tag-more-panel">
        <BkTag
          v-for="item in tagList.slice(renderData.length)"
          :key="item.value"
          :theme="item.theme">
          {{ item.label }}
        </BkTag>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import BkTag from 'bkui-vue/lib/tag';
  import { throttle } from 'lodash';
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { computed, nextTick, onBeforeUnmount, onMounted, ref, useTemplateRef, watch } from 'vue';

  interface Props {
    list: {
      label: string;
      value: number | string;
    }[];
  }

  const props = defineProps<Props>();

  const rootRef = ref();
  const moreRef = ref();
  const tagListRef = useTemplateRef('tagList');
  const tipsPanelRef = useTemplateRef('tipsPanel');
  const renderTagNum = ref(1);
  const isCalcRenderTagNum = ref(false);

  const renderData = computed(() => tagList.value.slice(0, renderTagNum.value));

  const moreTagCount = computed(() => tagList.value.length - renderTagNum.value);

  let tippyIns: Instance | undefined;

  const themeMap = {
    '0': 'success',
    '1': 'info',
    '2': 'warning',
    '3': 'danger',
  } as const;

  const tagList = computed(() =>
    props.list.map((item, index) => ({
      ...item,
      theme: themeMap[String(index % 4) as keyof typeof themeMap],
    })),
  );

  const calcRenderTagNum = () => {
    // next 确保组件是 mounted 状态
    nextTick(() => {
      if (!rootRef.value || tagList.value.length < 1) {
        return;
      }
      isCalcRenderTagNum.value = true;
      // setTimeout 确保 isCalcRenderTagNum 已经生效
      nextTick(() => {
        const { width: maxWidth } = rootRef.value.getBoundingClientRect();

        renderTagNum.value = 0;

        let renderTagCount = 0;
        const tipsTagPlaceholderWidth = 45;

        const allTagEleList = Array.from(tagListRef.value!.querySelectorAll('.bk-tag'));
        if (tagListRef.value!.getBoundingClientRect().width <= maxWidth) {
          renderTagNum.value = tagList.value.length;
        } else {
          const tagMargin = 6;
          let totalTagWidth = -tagMargin;

          for (let i = 0; i < allTagEleList.length; i++) {
            const { width: tagWidth } = allTagEleList[i].getBoundingClientRect();

            // 检查当前tag是否超过可用宽度
            const availableWidth = maxWidth - (i < allTagEleList.length - 1 ? tipsTagPlaceholderWidth : 0);
            if (tagWidth > availableWidth) {
              // 如果单个tag就超过可用宽度，不计入显示
              break;
            }

            totalTagWidth += tagWidth + tagMargin;
            if (totalTagWidth + tipsTagPlaceholderWidth <= maxWidth) {
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
    () => tagList.value,
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
<style lang="less">
  .staff-manage-tag {
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

    .bk-tag {
      max-width: calc(100% - 40px);
      margin-right: 0;
      margin-left: 0;

      & ~ .bk-tag {
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

  .staff-manage-tag-more-panel {
    margin-top: -8px;

    .bk-tag {
      margin-top: 8px;
    }
  }
</style>
