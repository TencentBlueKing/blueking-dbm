import { Menu } from 'bkui-vue';
import _ from 'lodash';
import {
  nextTick,
  type Ref,
  ref,
  watch,
} from 'vue';
import {
  useRoute,
  useRouter,
} from 'vue-router';

export const useActiveKey = (
  menuRef:Ref<InstanceType<typeof Menu>>,
  defaultKey: string,
  peending = ref(false),
) => {
  const route = useRoute();
  const router = useRouter();

  const parentKey = ref();
  const currentRouteName = ref('');

  const handleMenuKeyChange = (params: {key: string}) => {
    router.push({
      name: params.key,
    });
  };

  watch([menuRef, route, peending], () => {
    nextTick(() => {
      if (!menuRef.value || peending.value) {
        return;
      }
      const allMenuItems = (menuRef.value as any as {
        menuStore: Record<string, {
          key: string,
          parentKey: string
        }>
      }).menuStore;

      const allMunuRouteNameMap = Object.values(allMenuItems)
        .reduce((result, item) => Object.assign(result, {
          [item.key]: item.parentKey,
        }), {} as Record<string, string|undefined>);

      currentRouteName.value = '';
      _.forEachRight(route.matched, (routeItem) => {
        if (currentRouteName.value) {
          return;
        }
        const routeName = routeItem.name as string;
        if (routeName && _.has(allMunuRouteNameMap, routeName)) {
          currentRouteName.value = routeName;
          parentKey.value = allMunuRouteNameMap[routeName];
        }
      });

      if (!currentRouteName.value) {
        router.push({
          name: defaultKey,
        });
      }
    });
  }, {
    immediate: true,
  });

  return {
    parentKey,
    key: currentRouteName,
    routeLocation: handleMenuKeyChange,
  };
};
