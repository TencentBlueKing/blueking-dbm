import type { InjectionKey, Ref } from 'vue';

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
export const sideMenuCollapseKey: InjectionKey<Ref<boolean>> = Symbol('dbSideMenuCollapse');

export const useMenuContext = () => {
  const context = inject(menuContextKey);
  if (!context) {
    throw new Error('DbMenuGroup / DbMenuItem / DbSubmenu must be used inside DbMenu');
  }
  return context;
};

export const useMenuFlyout = () => inject(menuFlyoutKey, ref(false));

export const useSubmenuId = () => inject(submenuIdKey, undefined);

export const useSideMenuCollapse = () => inject(sideMenuCollapseKey, ref(false));
