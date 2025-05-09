<template>
  <div
    ref="root"
    class="cluster-list-column-operation-btn"
    :class="{
      'is-active': isShowPopMenu,
    }">
    <DbIcon type="more" />
    <div
      ref="popMenu"
      class="wrapper">
      <slot
        v-if="isShowPopMenu"
        name="default" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import tippy, { type Instance, type SingleTarget } from 'tippy.js';

  interface Slots {
    default: () => void;
  }

  defineSlots<Slots>();

  let tippyIns: Instance;

  const rootRef = useTemplateRef('root');
  const popMenuRef = useTemplateRef('popMenu');

  const isShowPopMenu = ref(false);

  onMounted(() => {
    tippyIns = tippy(rootRef.value as SingleTarget, {
      appendTo: () => document.body,
      arrow: true,
      content: popMenuRef.value as HTMLDivElement,
      hideOnClick: true,
      interactive: true,
      maxWidth: 'none',
      offset: [0, 12],
      onShow() {
        isShowPopMenu.value = true;
      },
      placement: 'bottom-start',
      popperOptions: {
        modifiers: [
          {
            name: 'flip',
            options: {
              allowedAutoPlacements: ['top-start', 'top-end'],
              fallbackPlacements: ['top', 'bottom'],
            },
          },
        ],
        strategy: 'fixed',
      },
      theme: 'light cluster-list-column-operation-panel',
      trigger: 'click',
      zIndex: 999,
    });
  });

  onBeforeUnmount(() => {
    if (tippyIns) {
      tippyIns.hide();
      tippyIns.unmount();
      tippyIns.destroy();
    }
  });
</script>
<style lang="less">
  tr.vxe-body--row {
    &:hover {
      .cluster-list-column-operation-btn {
        display: flex;
      }
    }
  }

  .cluster-list-column-operation-btn {
    display: none;
    font-size: 18px;
    cursor: pointer;
    justify-content: center;
    border-radius: 2px;
    align-items: center;

    &:hover {
      color: #3a84ff;
    }

    &.is-active {
      display: flex;
      color: #3a84ff;
    }
  }

  .tippy-box[data-theme~='cluster-list-column-operation-panel'] {
    .tippy-content {
      padding: 8px 0;
    }

    .wrapper {
      display: flex;
      flex-direction: column;

      & > * {
        &:hover {
          background-color: #f5f7fa;

          a,
          .bk-button {
            color: #3a84ff;
          }
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
</style>
