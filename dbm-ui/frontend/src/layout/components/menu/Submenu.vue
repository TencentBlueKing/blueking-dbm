<template>
  <div
    class="db-menu-submenu"
    :class="{ 'is-opened': isOpened }">
    <div
      ref="headerRef"
      class="db-menu-submenu-header"
      :class="{ 'is-active': collapse && isChildActive }"
      @click="handleToggle">
      <span class="db-menu-submenu-icon">
        <slot name="icon">
          <DbIcon :type="icon" />
        </slot>
      </span>
      <template v-if="!collapse">
        <span class="db-menu-submenu-title">
          <span
            v-overflow-tips.right
            class="text-overflow">
            {{ title }}
          </span>
          <slot name="append" />
        </span>
        <DbIcon
          class="db-menu-submenu-arrow"
          type="down-big" />
      </template>
    </div>
    <!-- 浮层内容渲染到 tippy 容器里，避免 tippy 搬动 Vue 管理的节点 -->
    <Teleport
      v-if="collapse"
      :to="popoverContainer">
      <div
        class="db-menu-flyout-list"
        @click="handleFlyoutClick">
        <slot />
      </div>
    </Teleport>
    <div
      v-else
      class="db-menu-submenu-list">
      <div class="db-menu-submenu-list-content">
        <slot />
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { computed, onBeforeUnmount, provide, ref, useId } from 'vue';

  import { menuFlyoutKey, submenuIdKey, useMenuContext, useSubmenuId } from './common/context';
  import { useMenuPopover } from './hooks/useMenuPopover';

  interface Props {
    icon?: string;
    id?: string;
    title?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    icon: 'cluster',
    id: '',
    title: '',
  });

  const { activeKey, collapse, menuMap, openedKeys, register, toggleSubmenu, unregister } = useMenuContext();

  const headerRef = ref<HTMLElement>();

  const fallbackId = useId();
  const submenuId = props.id || fallbackId;

  const isOpened = computed(() => openedKeys.value.includes(submenuId));
  const isChildActive = computed(() => menuMap.value[activeKey.value]?.parentKey === submenuId);

  const { container: popoverContainer, hide: hideFlyout } = useMenuPopover(headerRef, collapse, {
    arrow: false,
    interactive: true,
    // 图标与浮层之间留有间距，放宽可交互边界，避免鼠标移入过程中浮层被收起
    interactiveBorder: 12,
    placement: 'right-start',
    theme: 'light db-menu-flyout',
  });

  register({
    key: submenuId,
    parentKey: useSubmenuId(),
  });

  provide(submenuIdKey, submenuId);
  // 收起态子菜单只渲染在浮层里，展开态只渲染在轨道里
  provide(menuFlyoutKey, collapse);

  onBeforeUnmount(() => unregister(submenuId));

  const handleToggle = () => {
    if (collapse.value) {
      return;
    }
    toggleSubmenu(submenuId);
  };

  const handleFlyoutClick = () => {
    hideFlyout();
  };
</script>
