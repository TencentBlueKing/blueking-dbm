<template>
  <span class="machine-spec-item">
    <span
      class="machine-spec-item-name"
      :class="{ 'machine-spec-item-unbound': isUnbound }">
      {{ spec.spec_name }}
    </span>
    <span
      class="machine-spec-item-count"
      :class="{ 'machine-spec-item-unbound': isUnbound }">
      × {{ spec.count }}
    </span>
    <BkTag
      v-if="!spec.enable && !isUnbound"
      class="machine-spec-item-disabled">
      {{ t('已停用') }}
    </BkTag>
  </span>
</template>
<script setup lang="ts">
  import BkTag from 'bkui-vue/lib/tag';
  import { useI18n } from 'vue-i18n';

  import type { MachineSpec } from '@services/types';

  interface Props {
    spec: MachineSpec;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const isUnbound = computed(() => props.spec.enable === null || props.spec.spec_ids.length === 0);
</script>
<style lang="less">
  .machine-spec-item-name {
    color: #313238;
  }

  .machine-spec-item-count {
    margin: 0 2px;
    color: #63656e;
  }

  .machine-spec-item-unbound {
    color: #ea3636;
  }

  .machine-spec-item-disabled {
    display: inline-block;
    height: 18px;
    padding: 0 4px;
    margin-left: 4px;
    font-size: 12px;
    line-height: 18px;
    color: #979ba5;
    vertical-align: middle;
    background: #f0f1f5;
    border-radius: 2px;
  }
</style>
