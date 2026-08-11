import _ from 'lodash';
import { type Ref, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import type DbMenu from '../menu/Index.vue';

export const useActiveKey = (
  menuRef: Ref<InstanceType<typeof DbMenu> | undefined>,
  defaultKey: string,
  options = {} as {
    checkMethod?: (routerName: string) => string;
  },
) => {
  const route = useRoute();
  const router = useRouter();

  const parentKey = ref();
  const currentRouteName = ref('');

  // 菜单项动态增删（如工具箱收藏变更、侧栏折叠重建）不应把用户踢回默认页，只有路由本身匹配不到菜单才兜底跳转
  let checkedFullPath = '';

  const handleMenuKeyChange = (routeName: string) => {
    router.push({
      name: routeName,
    });
  };

  watch(
    [() => menuRef.value?.menuMap, route],
    () => {
      const menuMap = menuRef.value?.menuMap;
      if (!menuMap) {
        return;
      }

      currentRouteName.value = '';
      _.forEachRight(route.matched, (routeItem) => {
        if (currentRouteName.value) {
          return;
        }

        const routeName = routeItem.name as string;

        const currentActiveKey = _.isFunction(options.checkMethod) ? options.checkMethod(routeName) : routeName;
        if (currentActiveKey && menuMap[currentActiveKey]) {
          currentRouteName.value = currentActiveKey;
          parentKey.value = menuMap[currentActiveKey].parentKey;
        }
      });
      const isRouteChecked = checkedFullPath === route.fullPath;
      checkedFullPath = route.fullPath;

      if (!currentRouteName.value && !isRouteChecked) {
        router.push({
          name: defaultKey,
        });
      }
    },
    {
      deep: true,
      flush: 'post',
      immediate: true,
    },
  );

  return {
    key: currentRouteName,
    parentKey,
    routeLocation: handleMenuKeyChange,
  };
};
