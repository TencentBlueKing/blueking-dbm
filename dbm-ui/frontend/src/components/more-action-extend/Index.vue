<template>
  <BkDropdown
    :popover-options="{ zIndex: 10 }"
    trigger="click"
    @hide="handleHidePopover">
    <div
      class="operation-more-main"
      @click="handleClickMore">
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
    </div>
    <template #content>
      <BkDropdownMenu>
        <slot />
      </BkDropdownMenu>
    </template>
  </BkDropdown>
</template>
<script lang="ts" setup>
  import { useI18n } from 'vue-i18n';

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
