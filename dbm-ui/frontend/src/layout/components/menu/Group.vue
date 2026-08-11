<template>
  <div class="db-menu-group">
    <div
      v-bk-tooltips="tooltipConfig"
      class="db-menu-group-name">
      <slot name="name">
        <span class="text-overflow">{{ displayName }}</span>
      </slot>
    </div>
    <div class="db-menu-group-wrap">
      <slot />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { computed } from 'vue';

  import { useMenuContext } from './common/context';

  interface Props {
    foldName?: string;
    name?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    foldName: '',
    name: '',
  });

  const { collapse } = useMenuContext();

  const displayName = computed(() => (collapse.value && props.foldName ? props.foldName : props.name));

  const tooltipConfig = computed(() => ({
    content: props.name,
    disabled: !collapse.value,
    placement: 'right',
  }));
</script>
<style lang="less">
  .db-menu-group {
    display: flex;
    flex-direction: column;
  }
</style>
