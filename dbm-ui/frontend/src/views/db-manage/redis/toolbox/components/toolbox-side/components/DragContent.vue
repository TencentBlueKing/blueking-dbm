<template>
  <BkCollapse v-model="activeCollapses">
    <Vuedraggable
      v-model="allRenderMenuGroupList"
      item-key="id"
      @end="handleDragEnd">
      <template #item="{ element }">
        <RenderMenuGroup
          :id="element.id"
          v-model:favor-map="favorRouteNameMap"
          :active-view-name="activeViewName"
          :draggable="!Boolean(serachKey)"
          :serach-key="serachKey" />
      </template>
    </Vuedraggable>
  </BkCollapse>
</template>

<script setup lang="ts">
  import Vuedraggable from 'vuedraggable';

  import { useUserProfile } from '@stores';

  import { UserPersonalSettings } from '@common/const';

  import { type MenuItem } from '@views/db-manage/redis/toolbox-menu';

  import { makeMap } from '@utils';

  import RenderMenuGroup from './MenuGroup.vue';

  interface Props {
    list: MenuItem[];
    activeViewName: string;
    serachKey: string;
  }

  const props = defineProps<Props>();

  const userProfileStore = useUserProfile();

  const menuGroupIdList = props.list.map((item) => item.id);

  const activeCollapses = ref([...menuGroupIdList]);
  const allRenderMenuGroupList = ref<Record<'id' | 'name', string>[]>([]);
  const favorRouteNameMap = ref<Record<string, boolean>>({});

  watch(
    () => userProfileStore.profile,
    () => {
      const userMenuGroupSortList =
        (userProfileStore.profile[UserPersonalSettings.REDIS_TOOLBOX_MENUS] as string[]) || [];
      const allMenuGroupMap = makeMap(menuGroupIdList);
      const renderMenuGroupList: string[] = [];
      userMenuGroupSortList.forEach((item) => {
        if (allMenuGroupMap[item]) {
          renderMenuGroupList.push(item);
          delete allMenuGroupMap[item];
        }
      });
      allRenderMenuGroupList.value = renderMenuGroupList.concat(Object.keys(allMenuGroupMap)).map((item) => ({
        id: item,
        name: item,
      }));

      favorRouteNameMap.value = makeMap(userProfileStore.profile[UserPersonalSettings.REDIS_TOOLBOX_FAVOR] as string[]);
    },
    {
      immediate: true,
    },
  );

  const handleDragEnd = () => {
    userProfileStore.updateProfile({
      label: UserPersonalSettings.REDIS_TOOLBOX_MENUS,
      values: allRenderMenuGroupList.value.map((item) => item.id),
    });
  };
</script>
