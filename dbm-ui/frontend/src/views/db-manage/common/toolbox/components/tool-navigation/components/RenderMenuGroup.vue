<template>
  <template
    v-for="groupItem in menuGroupList"
    :key="groupItem.id">
    <div class="toolbox-menu-group-name">
      <span class="type-title">{{ groupItem.name }}</span>
      <DbIcon
        v-bk-tooltips="{
          placement: 'right',
          content: groupItem.description,
        }"
        class="type-icon"
        type="attention" />
    </div>
    <RenderMenuList
      :data="getGroupMenuList(groupItem)"
      :group-key="groupItem.id"
      :serach-key="serachKey" />
  </template>
</template>
<script setup lang="ts">
  import _ from 'lodash';

  import { makeMap } from '@utils';

  import { type Props as ToolNavigationProps } from '../Index.vue';

  import RenderMenuList from './RenderMenuList.vue';

  interface Props {
    menuGroupList: ToolNavigationProps['menuGroupList'];
    menuList: ToolNavigationProps['data'];
    serachKey: string;
  }
  const props = defineProps<Props>();

  const getGroupMenuList = (group: NonNullable<NonNullable<ToolNavigationProps['menuGroupList']>[number]>) => {
    const menuIdMap = makeMap(group.menuList);

    return _.filter(props.menuList, (item) => menuIdMap[item.id]);
  };
</script>
