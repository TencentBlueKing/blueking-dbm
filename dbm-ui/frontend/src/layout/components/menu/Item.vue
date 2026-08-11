<template>
  <div
    v-if="isFlyout"
    class="db-menu-flyout-item"
    :class="{ 'is-active': isActive }"
    @click="handleClick">
    <slot />
    <slot name="append" />
  </div>
  <div
    v-else
    ref="itemRef"
    class="db-menu-item"
    :class="{ 'is-active': isActive }"
    @click="handleClick">
    <span class="db-menu-item-icon">
      <DbIcon
        v-if="icon"
        :svg="svg"
        :type="icon" />
      <span
        v-else
        class="db-menu-item-dot" />
    </span>
    <span
      v-if="!isTooltip"
      class="db-menu-item-content">
      <span
        v-overflow-tips.right
        class="text-overflow">
        <slot />
      </span>
      <slot name="append" />
    </span>
    <!-- tooltip 内容在 tippy 实例创建时被移出，组件需保持单根节点以兼容 v-db-console -->
    <div
      v-else
      ref="tooltipRef"
      class="db-menu-tooltip-content">
      <slot />
      <slot name="append" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { computed, onBeforeUnmount, ref } from 'vue';

  import { useMenuContext, useMenuFlyout, useSubmenuId } from './common/context';
  import { useMenuPopover } from './hooks/useMenuPopover';

  interface Props {
    icon?: string;
    routeName: string;
    svg?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    icon: '',
    svg: false,
  });

  const { activeKey, collapse, handleItemClick, register, unregister } = useMenuContext();

  const isFlyout = useMenuFlyout();
  const parentKey = useSubmenuId();

  const itemRef = ref<HTMLElement>();
  const tooltipRef = ref<HTMLElement>();

  const isActive = computed(() => activeKey.value === props.routeName);
  // 收起态轨道只剩图标，菜单名与角标用 tooltip 承载
  const isTooltip = computed(() => !isFlyout.value && collapse.value && Boolean(props.icon));

  useMenuPopover(itemRef, tooltipRef, isTooltip, {
    placement: 'right',
    theme: 'dbm-tooltips db-menu-tooltip',
  });

  register({
    key: props.routeName,
    parentKey,
  });

  onBeforeUnmount(() => unregister(props.routeName));

  const handleClick = () => {
    handleItemClick(props.routeName);
  };
</script>
