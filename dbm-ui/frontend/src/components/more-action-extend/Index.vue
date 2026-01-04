<template>
  <div class="more-action-extend">
    <div
      ref="rootRef"
      :class="{
        active: isPopoverShow,
      }"
      @click.stop="handleActive">
      <span v-bk-tooltips="t('更多操作')">
        <slot name="trigger">
          <div
            class="default-trigger"
            :class="{
              'is-active': isPopoverShow,
            }">
            <DbIcon type="more" />
          </div>
        </slot>
      </span>
    </div>
    <div
      ref="popRef"
      class="more-action-extend-popover"
      @click="handleHide">
      <template v-if="isPopoverShow">
        <slot />
      </template>
    </div>
  </div>
</template>
<script lang="ts">
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';
  import { onBeforeUnmount, onMounted, ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  let activeTippyIns: Instance;
</script>
<script setup lang="ts">
  const { t } = useI18n();

  const rootRef = ref();
  const popRef = ref();

  let tippyIns: Instance | undefined;

  const isPopoverShow = ref(false);

  const handleActive = () => {
    if (!tippyIns) {
      return;
    }
    if (activeTippyIns && activeTippyIns !== tippyIns) {
      activeTippyIns.hide();
    }
    tippyIns.show();
    activeTippyIns = tippyIns;
  };

  const handleHide = () => {
    activeTippyIns.hide();
  };

  onMounted(() => {
    tippyIns = tippy(rootRef.value as SingleTarget, {
      appendTo: () => document.body,
      arrow: false,
      content: popRef.value,
      hideOnClick: true,
      interactive: true,
      maxWidth: 'none',
      offset: [0, 8],
      onHidden() {
        isPopoverShow.value = false;
      },
      onShow() {
        isPopoverShow.value = true;
      },
      placement: 'bottom',
      theme: 'light more-action-extend-popover',
      trigger: 'manual',
      zIndex: 999999,
    });
  });

  onBeforeUnmount(() => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
      tippyIns = undefined;
    }
  });
</script>
<style lang="less">
  .more-action-extend {
    display: inline-flex;

    .default-trigger {
      display: inline-flex;
      width: 20px;
      height: 20px;
      font-size: 14px;
      cursor: pointer;
      border-radius: 50%;
      justify-content: center;
      align-items: center;

      &:hover,
      &.is-active {
        color: #3a84ff;
        background: #dcdee5;
      }
    }
  }

  .tippy-box[data-theme~='more-action-extend-popover'] {
    .tippy-content {
      padding: 8px 0;
    }

    .more-action-extend-popover {
      display: flex;
      flex-direction: column;
      min-width: 80px;

      & > * {
        display: block !important;

        & > * {
          display: block !important;
        }

        &:hover {
          background-color: #f5f7fa;

          a,
          .bk-button {
            color: #3a84ff;
          }
        }
      }

      a,
      .bk-button {
        display: block;
        width: 100%;
        padding: 0 12px;
        font-size: 12px;
        line-height: 32px;
        color: #63656e;
        text-align: left;
      }

      .bk-button {
        &.is-disabled {
          color: #dcdee5 !important;
        }
      }

      a[disabled='true'] {
        color: #dcdee5 !important;
      }
    }
  }
</style>
