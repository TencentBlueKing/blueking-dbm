<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div class="toolbox-side">
    <BkInput
      v-model.tirm="state.search"
      class="toolbox-side__search"
      clearable
      :placeholder="$t('请输入')"
      type="search" />
    <BkException
      v-if="renderMenus.length === 0"
      class="pt-40"
      :description="$t('搜索为空')"
      scene="part"
      type="search-empty" />
    <BkCollapse
      v-else
      ref="sideListRef"
      v-model="state.activeCollapses"
      class="toolbox-side__collapse bk-scroll-y">
      <TransitionGroup name="drag">
        <BkCollapsePanel
          v-for="(panel, index) in renderMenus"
          :key="panel.id"
          :name="panel.id"
          @dragend.stop="handleDragend"
          @dragenter.prevent="handleDragenter(index)"
          @dragover.prevent>
          <div
            class="toolbox-side__header"
            :draggable="draggable"
            @dragstart.stop="handleDragstart(index)">
            <i class="db-icon-down-shape toolbox-side__status" />
            <i :class="`toolbox-side__icon ${panel.icon}`" />
            <strong
              v-overflow-tips
              class="toolbox-side__title text-overflow">
              {{ panel.name }}
            </strong>
            <span
              v-if="draggable === 'true'"
              class="toolbox-side__drag" />
          </div>
          <template #content>
            <div class="toolbox-side__content">
              <template
                v-for="item of panel.children"
                :key="item.id">
                <div
                  class="toolbox-side__item"
                  :class="{'toolbox-side__item--active': item.id === activeViewName}"
                  @click="handleChangeView(item)">
                  <div class="toolbox-side__left">
                    <span
                      v-overflow-tips
                      class="text-overflow">
                      {{ item.name }}
                    </span>
                    <!-- <TaskCount
                      v-if="item.id === 'MySQLExecute'"
                      class="count" /> -->
                  </div>
                  <i
                    v-bk-tooltips="favorViewIds.includes(item.id) ? $t('从导航移除') : $t('收藏至导航')"
                    class="toolbox-side__favor"
                    :class="[favorViewIds.includes(item.id) ? 'db-icon-star-fill' : 'db-icon-star']"
                    @click.stop="handleFavorView(item)" />
                </div>
              </template>
            </div>
          </template>
        </BkCollapsePanel>
      </TransitionGroup>
    </BkCollapse>
  </div>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { useUserProfile } from '@stores';

  import { UserPersonalSettings } from '@common/const';

  import { messageSuccess } from '@utils';

  import { toolboxRoutes } from '../../routes';
  import menus, { type MenuChild } from '../common/menus';

  // import TaskCount from './TaskCount.vue';

  interface State {
    search: string,
    activeCollapses: Array<string>
  }
  interface DragState {
    dragIndex: null | number,
    dragendIndex: null | number,
  }

  const { t } = useI18n();
  const router = useRouter();
  const route = useRoute();
  const userProfileStore = useUserProfile();
  const menuActives = ['redis'];

  const sideListRef = ref();
  const state = reactive<State>({
    search: '',
    activeCollapses: [...menuActives],
  });
  const dragState = reactive<DragState>({
    dragIndex: null,
    dragendIndex: null,
  });
  const dragMenus = ref<typeof menus>([]);
  const profileMenus = computed(() => userProfileStore.profile[UserPersonalSettings.REDIS_TOOLBOX_MENUS]);
  const draggable = computed(() => (state.search ? 'false' : 'true'));
  // 需要渲染的 menus
  const renderMenus = computed(() => {
    if (state.search === '') return dragMenus.value;

    const localLowerSearch = state.search.toLocaleLowerCase();
    const filterMenus = dragMenus.value.filter(menu => menu.name.toLocaleLowerCase().includes(localLowerSearch)
      || menu.children.filter(child => child.name.toLocaleLowerCase().includes(localLowerSearch)).length > 0);
    return filterMenus.map((menu) => {
      if (menu.name.toLocaleLowerCase().includes(localLowerSearch)) {
        return menu;
      }

      return {
        ...menu,
        children: menu.children.filter(child => child.name.toLocaleLowerCase().includes(localLowerSearch)),
      };
    });
  });
  const activeViewName = computed(() => route.name);
  // 已收藏视图
  const favorViews = computed<Array<MenuChild>>(() => (
    userProfileStore.profile[UserPersonalSettings.REDIS_TOOLBOX_FAVOR] || []
  ));
  const favorViewIds = computed(() => favorViews.value.map(item => item.id));

  watch(() => state.search, () => {
    state.activeCollapses = [...menuActives];
  });

  const getMenus = () => {
    // 用户个人没有保存过配置
    if (!profileMenus.value) return menus;

    // 保证用户配置的同时加入新的内容
    const cloneMenus = _.cloneDeep(menus);
    const resMenus = [];
    for (const menu of profileMenus.value) {
      const index = cloneMenus.findIndex(m => m.id === menu.id);
      if (index >= 0) {
        const target = cloneMenus.splice(index, 1);
        resMenus.push(...target);
      }
    }
    resMenus.push(...cloneMenus);
    return resMenus;
  };

  watch(profileMenus, () => {
    dragMenus.value = getMenus();
  }, { immediate: true });

  // onBeforeUnmount(() => {
  //   userProfileStore.updateProfile({
  //     label: UserPersonalSettings.REDIS_TOOLBOX_MENUS,
  //     values: dragMenus.value,
  //   });
  // });

  /**
   * 收藏视图至导航
   */
  function handleFavorView(item: MenuChild) {
    const favors = [...favorViews.value];
    const index = favorViews.value.findIndex(favorItem => favorItem.id === item.id);
    const isCollected = index > -1;
    if (!isCollected) {
      // 添加收藏
      favors.push(item);
    } else {
      // 取消收藏
      favors.splice(index, 1);

      // 动态设置 activeMenu
      const favorRoute = toolboxRoutes.find(r => r.name === item.id);
      if (favorRoute?.meta) {
        favorRoute.meta.activeMenu = 'RedisToolbox';
      }
    }

    userProfileStore.updateProfile({
      label: UserPersonalSettings.REDIS_TOOLBOX_FAVOR,
      values: favors,
    }).then(() => {
      messageSuccess(isCollected ? t('取消收藏成功') : t('收藏成功'));
    });
  }

  /**
   * 切换操作视图
   */
  function handleChangeView(item: MenuChild) {
    router.push({ name: item.id });
  }

  /**
   * 拖拽
   */
  function handleDragenter(index: number) {
    dragState.dragendIndex = index;
  }
  function handleDragstart(index: number) {
    dragState.dragIndex = index;
  }
  function handleDragend() {
    if (
      dragState.dragIndex !== null
      && dragState.dragendIndex !== null
      && dragState.dragIndex !== dragState.dragendIndex
    ) {
      const sourceItem = dragMenus.value[dragState.dragIndex];
      dragMenus.value.splice(dragState.dragIndex, 1);
      dragMenus.value.splice(dragState.dragendIndex, 0, sourceItem);

      dragState.dragIndex = null;
      dragState.dragendIndex = null;

      userProfileStore.updateProfile({
        label: UserPersonalSettings.REDIS_TOOLBOX_MENUS,
        values: dragMenus.value,
      });
    }
  }
</script>

<style lang="less" scoped>
@import "@styles/mixins.less";

.toolbox-side {
  height: 100%;
  padding: 16px 0;
  background-color: #f5f7fa;

  &__search {
    display: flex;
    width: calc(100% - 32px);
    margin: 0 auto;
  }

  &__collapse {
    height: calc(100% - 40px);
    margin-top: 8px;

    .drag-move {
      transition: all 0.5s ease;
    }
  }

  :deep(.bk-collapse-title) {
    display: block;
    margin-left: 0;
  }

  :deep(.bk-collapse-header) {
    height: 32px;
    padding: 0 16px;
    line-height: 32px;

    &:hover {
      background-color: unset;
    }
  }

  :deep(.bk-collapse-content) {
    padding: 0 16px;
  }

  :deep(.bk-collapse-icon) {
    display: none !important;
  }

  :deep(.bk-collapse-item) {
    margin-bottom: 16px;

    &-active {
      .toolbox-side__status {
        transform: rotate(0);
      }
    }

    &:last-child {
      margin-bottom: 0;
    }
  }

  &__header {
    padding-right: 8px;
    border-radius: 2px;
    .flex-center();

    &:hover {
      background-color: #eaebf0;

      .toolbox-side__drag {
        display: block;
      }
    }
  }

  &__status {
    margin-left: 4px;
    transform: rotate(-90deg);
    transition: all 0.2s;
  }

  &__icon {
    width: 24px;
    height: 24px;
    margin: 0 8px 0 4px;
    font-size: @font-size-large;
    line-height: 24px;
    color: @primary-color;
    background-color: #e1ecff;
    border-radius: 50%;
    justify-content: center;
    .flex-center();

    &.db-icon-copy {
      color: #2dcb56;
      background-color: #dcffe2;
    }

    &.db-icon-rollback {
      color: #ff9c01;
      background-color: #ffe8c3;
    }

    &.db-icon-clone {
      color: #7153fb;
      background-color: #dfdaf2;
    }

    &.db-icon-cluster {
      color: #18bbc8;
      background-color: #d2f3f6;
    }

    &.db-icon-data {
      color: #ea3636;
      background-color: #fdd;
    }
  }

  &__title {
    font-size: @font-size-mini;
    color: @title-color;
    flex: 1;
  }

  &__drag {
    position: relative;
    display: none;
    width: 14px;
    height: 14px;
    cursor: move;

    &::after {
      position: absolute;
      top: 4px;
      left: 4px;
      width: 2px;
      height: 2px;
      color: @default-color;
      background: currentcolor;
      content: "";
      box-shadow:
        0 4px 0 0 currentcolor,
        0 8px 0 0 currentcolor,
        0 -4px 0 0 currentcolor,
        4px 0 0 0 currentcolor,
        4px 4px 0 0 currentcolor,
        4px 8px 0 0 currentcolor,
        4px -4px 0 0 currentcolor;
    }
  }

  &__content {
    font-size: @font-size-mini;
  }

  &__left {
    flex: 1;
    display: flex;
    align-items: center;
    overflow: hidden;

    .count {
      flex-shrink: 0;
    }
  }

  &__item {
    height: 32px;
    padding: 0 16px;
    margin-top: 8px;
    overflow: hidden;
    line-height: 32px;
    color: @default-color;
    cursor: pointer;
    background-color: @bg-white;
    border-radius: 2px;
    .flex-center();

    &:hover {
      box-shadow: 0 2px 4px 0 rgb(0 0 0 / 10%), 0 2px 4px 0 rgb(25 25 41 / 5%);

      .toolbox-side__favor {
        display: block;
      }
    }

    &--active {
      color: @primary-color;
      background-color: #e1ecff;
    }
  }

  &__favor {
    display: none;

    &.db-icon-star-fill {
      display: block;
      color: @warning-color;
    }
  }
}
</style>
