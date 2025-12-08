import { storeToRefs } from 'pinia';

import { useUserProfile } from '@stores';

import { DBTypes } from '@common/const';

import { makeMap } from '@utils';

export const useToolboxFavor = (
  dbType: DBTypes,
  menuList?: { id: string }[],
  menuGroupList?: { id: string; menuList: string[] }[],
) => {
  const userProfile = useUserProfile();
  const { profile } = storeToRefs(userProfile);

  const toolboxFavorMap = computed(() => makeMap(profile.value[`${dbType}_toolbox_favor`.toUpperCase()]));

  const toolboxMenuSortList = computed(() => {
    if (!menuGroupList || menuGroupList.length === 0) {
      return profile.value[`${dbType}_toolbox_group_sort`.toUpperCase()] || menuList?.map((item) => item.id) || [];
    }

    return menuGroupList.reduce((acc, item) => {
      return acc.concat(profile.value[`${dbType}_${item.id}_toolbox_group_sort`.toUpperCase()] || item.menuList || []);
    }, [] as string[]);
  });

  return {
    toolboxFavorMap,
    toolboxMenuSortList,
  };
};
