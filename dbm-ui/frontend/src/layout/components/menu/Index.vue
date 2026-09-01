<template>
  <div
    class="db-menu"
    :class="{ 'is-collapse': collapse }">
    <slot />
  </div>
</template>
<script setup lang="ts">
  import { provide, ref, toRef, watch } from 'vue';

  import { type MenuContext, menuContextKey, type MenuItemInfo, useSideMenuCollapse } from './common/context';

  interface Props {
    activeKey?: string;
    openedKeys?: (string | undefined)[];
  }

  const props = withDefaults(defineProps<Props>(), {
    activeKey: '',
    openedKeys: () => [],
  });

  const emit = defineEmits<Emits>();

  type Emits = (e: 'click', routeName: string) => void;

  const collapse = useSideMenuCollapse();

  const menuMap = ref<Record<string, MenuItemInfo>>({});
  const openedKeys = ref<string[]>([]);

  watch(
    [() => props.openedKeys, collapse],
    () => {
      openedKeys.value = collapse.value ? [] : (props.openedKeys.filter((item) => item) as string[]);
    },
    {
      immediate: true,
    },
  );

  const register = (info: MenuItemInfo) => {
    menuMap.value[info.key] = info;
  };

  const unregister = (key: string) => {
    delete menuMap.value[key];
  };

  const toggleSubmenu = (id: string) => {
    openedKeys.value = openedKeys.value.includes(id) ? [] : [id];
  };

  provide<MenuContext>(menuContextKey, {
    activeKey: toRef(props, 'activeKey'),
    collapse,
    handleItemClick: (routeName: string) => emit('click', routeName),
    menuMap,
    openedKeys,
    register,
    toggleSubmenu,
    unregister,
  });

  defineExpose({
    menuMap,
  });
</script>
<style lang="less">
  .db-menu {
    display: flex;
    width: 100%;
    flex-direction: column;
    font-size: 14px;
    color: #96a2b9;

    .db-menu-group-name {
      display: flex;
      height: 40px;
      margin: 0 18px;
      overflow: hidden;
      font-size: 12px;
      line-height: 16px;
      color: #fff;
      white-space: nowrap;
      align-items: center;
    }

    .db-menu-item,
    .db-menu-submenu-header {
      display: flex;
      height: 40px;
      overflow: hidden;
      white-space: nowrap;
      cursor: pointer;
      align-items: center;

      &:hover {
        color: #fff;
        background-color: #31394f;
      }

      &.is-active {
        color: #fff;
        background: linear-gradient(90deg, #3f87ff 0%, #3a84ff 100%);
      }
    }

    .db-menu-item {
      margin: 2px 0;
    }

    .db-menu-item-icon,
    .db-menu-submenu-icon {
      display: flex;
      height: 100%;
      font-size: 16px;
      flex: 0 0 60px;
      align-items: center;
      justify-content: center;
    }

    .db-menu-item-dot {
      display: inline-block;
      width: 3px;
      height: 3px;
      background: #fff;
      border-radius: 50%;
    }

    .db-menu-item-content,
    .db-menu-submenu-title {
      display: flex;
      height: 100%;
      overflow: hidden;
      flex: 1;
      align-items: center;
    }

    .db-menu-submenu-arrow {
      margin-right: 16px;
      font-size: 16px;
      transform: rotate(-90deg);
      transition: transform 0.3s ease-out;
    }

    .db-menu-submenu {
      &.is-opened {
        background: #151d2c;

        .db-menu-submenu-arrow {
          transform: rotate(0deg);
        }

        .db-menu-submenu-list {
          grid-template-rows: 1fr;
        }
      }
    }

    .db-menu-submenu-list {
      display: grid;
      grid-template-rows: 0fr;
      transition: grid-template-rows 0.3s ease-in-out;
    }

    .db-menu-submenu-list-content {
      overflow: hidden;
    }
  }

  .db-menu.is-collapse {
    .db-menu-group-name {
      padding: 0 4px;
      margin: 0;
      justify-content: center;
    }

    .db-menu-item,
    .db-menu-submenu-header {
      height: 44px;
      margin: 0;
      justify-content: center;
    }

    .db-menu-item-icon,
    .db-menu-submenu-icon {
      flex: 0 0 auto;
    }
  }

  .tippy-box[data-theme~='db-menu-flyout'] {
    border-radius: 2px;

    .tippy-content {
      padding: 8px 0;
    }

    .db-menu-flyout-list {
      min-width: 120px;
    }

    .db-menu-flyout-item {
      display: flex;
      height: 32px;
      padding: 0 16px;
      font-size: 12px;
      color: #63656e;
      white-space: nowrap;
      cursor: pointer;
      align-items: center;

      &:hover {
        background: #f5f7fa;
      }

      &.is-active {
        color: #3a84ff;
        background: #eaf3ff;
      }
    }
  }

  .tippy-box[data-theme~='db-menu-flyout'],
  .tippy-box[data-theme~='db-menu-tooltip'] {
    .dbm-cluster-instance-count-tag,
    .ticket-count {
      color: #979ba5;
      background: #f0f1f5;
    }
  }
</style>
