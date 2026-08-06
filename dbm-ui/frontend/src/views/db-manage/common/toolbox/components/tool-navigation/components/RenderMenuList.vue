<template>
  <div class="root">
    <Vuedraggable
      v-model="renderMenuList"
      item-key="id"
      @end="handleDragEnd">
      <template #item="{ element }">
        <RenderMenuItem :data="element" />
      </template>
    </Vuedraggable>
  </div>
</template>
<script setup lang="ts">
  import { useRoute } from 'vue-router';
  import Vuedraggable from 'vuedraggable';

  import { useUserProfile } from '@stores';

  import { DBTypes, toolboxProfileKeyMap } from '@common/const';

  import { encodeRegexp } from '@utils';

  import { type Props as ToolNavigationProps } from '../Index.vue';

  import RenderMenuItem from './RenderMenuItem.vue';

  interface Props {
    data: ToolNavigationProps['data'];
    groupKey?: string;
    serachKey: string;
  }
  const props = withDefaults(defineProps<Props>(), {
    groupKey: '',
  });

  const route = useRoute();
  const { profile, updateProfile } = useUserProfile();

  const dbType = route.meta.dbType as DBTypes;
  const toolboxGroupSortKey = toolboxProfileKeyMap[dbType]!.groupSort;
  const profileSortKey = `${
    props.groupKey
      ? toolboxGroupSortKey.replace('_toolbox_group_sort', `_${props.groupKey}_toolbox_group_sort`)
      : toolboxGroupSortKey
  }`.toUpperCase();

  const renderMenuList = ref<ToolNavigationProps['data']>([]);

  watch(
    () => [props.data, props.serachKey],
    () => {
      const customSortList = (profile[profileSortKey] || []) as string[];
      const groupIdMap = props.data.reduce(
        (result, item) => {
          return Object.assign(result, {
            [item.id]: item,
          });
        },
        {} as Record<string, ToolNavigationProps['data'][number]>,
      );

      const regex = new RegExp(encodeRegexp(props.serachKey), 'i');

      renderMenuList.value = [];

      customSortList.forEach((item) => {
        const group = groupIdMap[item];
        if (group) {
          renderMenuList.value.push({
            ...group,
            children: group.children.filter((child) => regex.test(child.name)),
          });
          delete groupIdMap[item];
        }
      });

      Object.values(groupIdMap).forEach((item) => {
        renderMenuList.value.push({
          ...item,
          children: item.children.filter((child) => regex.test(child.name)),
        });
      });
    },
    {
      immediate: true,
    },
  );

  const handleDragEnd = () => {
    updateProfile({
      label: profileSortKey,
      values: renderMenuList.value.map((item) => item.id),
    });
  };
</script>
