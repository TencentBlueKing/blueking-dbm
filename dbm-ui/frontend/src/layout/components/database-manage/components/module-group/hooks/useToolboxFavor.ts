import { storeToRefs } from 'pinia';

import { useUserProfile } from '@stores';

import { DBTypes, toolboxProfileKeyMap } from '@common/const';

import { makeMap } from '@utils';

export const useToolboxFavor = (
  dbType: DBTypes,
  menuList?: { id: string }[],
  menuGroupList?: { id: string; menuList: string[] }[],
) => {
  const userProfile = useUserProfile();
  const { profile } = storeToRefs(userProfile);

  const toolboxFavorKey = toolboxProfileKeyMap[dbType]!.favor;
  const toolboxGroupSortKey = toolboxProfileKeyMap[dbType]!.groupSort;

  const toolboxFavorMap = computed(() => makeMap(profile.value[toolboxFavorKey.toUpperCase()]));

  const toolboxMenuSortList = computed(() => {
    if (!menuGroupList || menuGroupList.length === 0) {
      return profile.value[toolboxGroupSortKey.toUpperCase()] || menuList?.map((item) => item.id) || [];
    }

    return menuGroupList.reduce((acc, item) => {
      return acc.concat(
        profile.value[
          toolboxGroupSortKey.replace('_toolbox_group_sort', `_${item.id}_toolbox_group_sort`).toUpperCase()
        ] ||
          item.menuList ||
          [],
      );
    }, [] as string[]);
  });

  return {
    toolboxFavorMap,
    toolboxMenuSortList,
  };
};
