import { type ComputedRef, inject, type InjectionKey, type Ref, ref } from 'vue';

export interface MenuItemInfo {
  key: string;
  parentKey?: string;
}

export interface MenuContext {
  activeKey: Ref<string>;
  collapse: Ref<boolean>;
  handleItemClick: (routeName: string) => void;
  menuMap: Ref<Record<string, MenuItemInfo>>;
  openedKeys: Ref<string[]>;
  register: (info: MenuItemInfo) => void;
  toggleSubmenu: (id: string) => void;
  unregister: (key: string) => void;
}

export const menuContextKey: InjectionKey<MenuContext> = Symbol('dbMenuContext');
// 浮层内的菜单项走轻量渲染，与轨道内的图标项区分
export const menuFlyoutKey: InjectionKey<Ref<boolean>> = Symbol('dbMenuFlyout');
export const submenuIdKey: InjectionKey<string | undefined> = Symbol('dbSubmenuId');
export const sideMenuCollapseKey: InjectionKey<ComputedRef<boolean>> = Symbol('dbSideMenuCollapse');

export const useMenuContext = () => inject(menuContextKey) as MenuContext;

export const useMenuFlyout = () => inject(menuFlyoutKey, ref(false));

export const useSubmenuId = () => inject(submenuIdKey, undefined);

export const useSideMenuCollapse = () => inject(sideMenuCollapseKey, ref(false) as ComputedRef<boolean>);
