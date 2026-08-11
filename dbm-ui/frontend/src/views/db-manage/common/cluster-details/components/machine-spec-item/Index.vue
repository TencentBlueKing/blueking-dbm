<template>
  <span class="machine-spec-item">
    <span
      class="machine-spec-item-name"
      :class="{ 'machine-spec-item-unbound': isUnbound, 'machine-spec-item-disabled': isDisabled }">
      {{ spec.spec_name }}
    </span>
    <span
      class="machine-spec-item-count"
      :class="{ 'machine-spec-item-unbound': isUnbound, 'machine-spec-item-disabled': isDisabled }">
      × {{ spec.count }}
    </span>
    <BkTag
      v-if="isDisabled"
      class="ml-4"
      size="small">
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
  const isDisabled = computed(() => !props.spec.enable && !isUnbound.value);
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
    color: #c4c6cc;
    text-decoration: line-through #c4c6cc;
  }
</style>
