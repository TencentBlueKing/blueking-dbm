<template>
  <div class="bk-vxe-table-settings-other-wrapper">
    <div class="bk-vxe-table-settings-box table-size">
      <div class="bk-vxe-table-settings-title">表格行高</div>
      <BkRadioGroup
        v-model="size"
        size="small">
        <BkRadioButton label="mini">小</BkRadioButton>
        <BkRadioButton label="small">中</BkRadioButton>
        <BkRadioButton label="medium">大</BkRadioButton>
      </BkRadioGroup>
    </div>
    <div
      v-if="slots.default"
      class="bk-vxe-table-settings-box">
      <slot />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { type VNode } from 'vue';

  interface Slots {
    default?: () => VNode;
  }

  const slots = defineSlots<Slots>();

  const size = defineModel<string>();
</script>
<style lang="less">
  .bk-vxe-table-settings-other-wrapper {
    padding: 16px 0;
  }

  .bk-vxe-table-settings-box {
    padding: 0 16px;

    .bk-vxe-table-settings-title {
      height: 19px;
      margin-bottom: 8px;
      font-size: 14px;
      color: #63656e;
    }

    &.table-size {
      .bk-radio-button {
        width: 68px;
      }
    }

    & ~ .bk-vxe-table-settings-box {
      margin-top: 8px;
    }
  }
</style>
