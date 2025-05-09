<template>
  <BkDropdown
    :popover-options="{
      zIndex: 1000,
      boundary: 'body',
      clickContentAutoHide: true,
      renderDirective: 'show',
    }"
    :trigger="trigger"
    @hide="handleHidePopover">
    <div
      class="operation-more-main"
      @click="handleClickMore">
      <slot name="handler">
        <BkButton
          class="mr-4"
          text
          theme="primary">
          {{ t('更多') }}
        </BkButton>
        <DbIcon
          class="more-icon"
          :class="{ 'more-icon-active': isRotate }"
          type="down-shape" />
      </slot>
    </div>
    <template #content>
      <BkDropdownMenu class="dropdown-menu-with-button">
        <slot />
      </BkDropdownMenu>
    </template>
  </BkDropdown>
</template>
<script lang="ts" setup>
  import { Dropdown } from 'bkui-vue';
  import type { VNode } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  interface Props {
    trigger?: ComponentProps<typeof Dropdown>['trigger'];
  }
  interface Slots {
    default: () => VNode;
    handler: () => VNode;
  }

  withDefaults(defineProps<Props>(), {
    trigger: 'click',
  });

  defineSlots<Slots>();

  const { t } = useI18n();

  const isRotate = ref(false);

  const handleClickMore = () => {
    isRotate.value = !isRotate.value;
  };

  const handleHidePopover = () => {
    isRotate.value = false;
  };
</script>

<style lang="less">
  .operation-more-main {
    display: flex;
    color: #3a84ff;
    cursor: pointer;
    align-items: center;

    .more-icon {
      transform: rotate(0deg);
      transition: all 0.5s;
    }

    .more-icon-active {
      transform: rotate(-180deg);
    }
  }
</style>
