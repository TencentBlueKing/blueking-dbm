<template>
  <Teleport to="body">
    <div
      v-if="isEnabled"
      class="dbm-new-feature-guide">
      <div
        ref="tips"
        class="guide-info"
        :class="placement"
        :style="tipStyles">
        <div class="title">{{ currentData.title }}</div>
        <div class="content">{{ currentData.content }}</div>
        <div class="action">
          <div
            class="confirm-btn"
            @click="handleConfirm">
            {{ confirmText }}
          </div>
        </div>
        <div class="target-arrow" />
      </div>
    </div>
  </Teleport>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useStorage } from '@vueuse/core';

  interface Props {
    list: {
      content: string;
      entry?: () => void;
      leave?: () => void;
      target: string;
      title: string;
    }[];
    name: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const histroyRecord = useStorage<Record<string, any>>('new_feature_guide', {});
  const currentIndex = ref(0);
  const tipsRef = useTemplateRef('tips');
  const placement = ref('');
  const tipStyles = ref({});
  const isEnabled = ref(!histroyRecord.value[props.name]);

  const currentData = computed(() => props.list[currentIndex.value]);
  const confirmText = computed(() => (currentIndex.value < props.list.length - 1 ? t('下一步') : t('我知道了')));

  let hightlightEle: HTMLElement | undefined;

  const activeStep = () => {
    const windowWidth = window.innerWidth;
    const windowHieght = window.innerHeight;
    const currentStep = currentData.value;
    const $stepTarget = document.querySelector(currentStep.target);
    if (!$stepTarget) {
      return;
    }
    $stepTarget.classList.add('guide-highlight');

    if (currentStep.entry) {
      currentStep.entry();
    }

    setTimeout(() => {
      const {
        bottom: targeBottom,
        left: targetLeft,
        right: targetRight,
        top: targetTop,
        width: targetWidth,
      } = $stepTarget.getBoundingClientRect();
      const { height, width } = tipsRef.value!.getBoundingClientRect();

      let latestPlacement = 'left';

      if (targetTop < 0.25 * windowHieght) {
        latestPlacement = 'bottom';
      } else if (targeBottom > windowHieght - 0.25 * windowHieght) {
        latestPlacement = 'top';
      } else if (targetRight < windowWidth / 2) {
        latestPlacement = 'right';
      } else {
        latestPlacement = 'left';
      }

      let styles = {};

      if (latestPlacement === 'bottom') {
        styles = {
          left: `${targetLeft + (targetWidth - width) / 2}px`,
          top: `${targeBottom + 10}px`,
        };
      } else if (latestPlacement === 'top') {
        styles = {
          left: `${targetLeft + (targetWidth - width) / 2}px`,
          top: `${windowHieght - targetTop - height - 10}px`,
        };
      } else if (latestPlacement === 'left') {
        styles = {
          right: `${windowWidth - targetLeft + 10}px`,
          top: `${targetTop - 26}px`,
        };
      } else if (latestPlacement === 'right') {
        styles = {
          left: `${targetRight + 10}px`,
          top: `${targetTop - 26}px`,
        };
      }
      tipStyles.value = Object.freeze(styles);
      placement.value = latestPlacement;
    });
  };

  watch(
    currentData,
    () => {
      setTimeout(() => {
        if (!isEnabled.value) {
          return;
        }
        hightlightEle = document.querySelector(currentData.value.target) as HTMLElement;
        if (!hightlightEle) {
          isEnabled.value = false;
          return;
        }
        hightlightEle?.classList.add('guide-highlight');
        nextTick(() => {
          activeStep();
        });
      });
    },
    {
      immediate: true,
    },
  );

  const handleConfirm = () => {
    hightlightEle?.classList.remove('guide-highlight');
    currentData.value.leave?.();
    if (currentIndex.value < props.list.length - 1) {
      currentIndex.value += 1;
      return;
    }
    histroyRecord.value = {
      ...histroyRecord.value,
      [props.name]: true,
    };
    isEnabled.value = false;
  };
</script>
<style lang="less">
  body {
    *.guide-highlight {
      z-index: 99999999 !important;
      pointer-events: none !important;
      background: #fff;
      opacity: 100% !important;
    }
  }

  .dbm-new-feature-guide {
    position: fixed;
    inset: 0;
    z-index: 100000;
    background: rgb(0 0 0 / 60%);

    .guide-info {
      position: absolute;
      top: 100px;
      left: 100px;
      width: 270px;
      min-height: 110px;
      padding: 12px 10px 10px;
      font-size: 12px;
      color: #313238;
      background: #fff;
      border-radius: 2px;
      opacity: 0%;

      &.right,
      &.left,
      &.bottom,
      &.top {
        opacity: 100%;
      }

      &.right {
        .target-arrow {
          top: 30px;
          left: -4px;
        }
      }

      &.left {
        .target-arrow {
          top: 30px;
          right: -4px;
        }
      }

      &.bottom {
        .target-arrow {
          top: -4px;
          left: 50%;
        }
      }

      &.top {
        .target-arrow {
          bottom: -4px;
          left: 50%;
        }
      }
    }

    .title {
      font-weight: 700;
      line-height: 16px;
    }

    .content {
      margin-top: 7px;
    }

    .action {
      display: flex;
      justify-content: flex-end;
      margin-top: 14px;
    }

    .confirm-btn {
      height: 20px;
      padding: 0 8px;
      margin-left: 14px;
      line-height: 20px;
      color: #fff;
      cursor: pointer;
      background: #3a84ff;
      border-radius: 10px;
    }

    .target-arrow {
      position: absolute;
      width: 8px;
      height: 8px;
      background: inherit;
      transform: rotate(45deg);
    }
  }
</style>
