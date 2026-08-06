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
  <div class="db-manage-toolbox-menu">
    <BkInput
      v-model.trim="searchKey"
      class="db-manage-toolbox-menu-search mb-16"
      clearable
      :placeholder="t('搜索工具名称')"
      type="search" />
    <ScrollFaker style="height: calc(100% - 64px)">
      <BkCollapse
        v-if="displayDataList.length > 0"
        v-model="activeIndex"
        header-icon-align="right"
        use-block-theme>
        <BkCollapsePanel
          v-for="menuItem in displayDataList"
          :key="menuItem.id"
          :name="menuItem.id">
          <div class="tool-group">
            <DbIcon
              class="tool-group-icon"
              :type="menuItem.icon" />
            <div class="tool-group-name ml-4">{{ menuItem.name }}</div>
            <!-- <div
              v-if="menuItem.id === 'favor'"
              class="tool-group-desc">
              {{ t('· 按收藏时间倒序 · 跨业务空间保留') }}
            </div> -->
            <!-- <div
              v-if="menuItem.id === 'used'"
              class="tool-group-desc">
              {{ t('· 按使用时间倒序 · 跨业务空间保留') }}
            </div> -->
          </div>
          <template #content>
            <template v-if="hasChildGroups(menuItem)">
              <template
                v-for="(childrenItem, childIndex) in menuItem.children"
                :key="childrenItem.id">
                <div
                  v-if="isTreeNode(childrenItem)"
                  class="sub-group">
                  <div class="sub-group-name">
                    <BkTag
                      class="ml-8"
                      :theme="getTheme(childIndex)"
                      type="stroke">
                      {{ childrenItem.name }}
                    </BkTag>
                  </div>
                  <div class="tool-list">
                    <MenuItem
                      v-for="subChildrenItem in getLeafChildren(childrenItem as ToolboxTreeNode)"
                      :key="subChildrenItem.id"
                      :data="subChildrenItem">
                    </MenuItem>
                  </div>
                </div>
              </template>
            </template>
            <div
              v-else
              class="tool-list">
              <MenuItem
                v-for="childrenItem in getLeafChildren(menuItem)"
                :key="childrenItem.id"
                :data="childrenItem">
              </MenuItem>
            </div>
          </template>
        </BkCollapsePanel>
      </BkCollapse>
      <BkException
        v-else
        class="empty-exception"
        :description="t('搜索为空')"
        scene="part"
        type="search-empty" />
    </ScrollFaker>
  </div>
</template>
<script setup lang="ts">
  import { storeToRefs } from 'pinia';
  import type { UnwrapRef } from 'vue';
  import { useRoute } from 'vue-router';

  import { useDebouncedRef } from '@hooks';

  import { useUserProfile } from '@stores';

  import { DBTypes, toolboxProfileKeyMap } from '@common/const';

  import { t } from '@wangeditor/editor';

  import type { ToolboxLeafNode, ToolboxTreeNode } from '../common/types';
  import { isLeafNode, isTreeNode } from '../common/utils.ts';

  import MenuItem from './components/MenuItem.vue';

  interface Props {
    menuList: ToolboxTreeNode[];
  }

  const props = defineProps<Props>();

  const route = useRoute();
  const profileStore = useUserProfile();
  const { profile } = storeToRefs(profileStore);

  const searchKey = useDebouncedRef('');
  const activeIndex = ref(['favor', 'used', ...props.menuList.map((item) => item.id)]);
  const displayDataList = ref<Props['menuList']>([]);

  const dbType = route.meta.dbType as DBTypes;
  const profileFavorKey = toolboxProfileKeyMap[dbType]!.favor;
  const profileUsedKey = toolboxProfileKeyMap[dbType]!.used;

  const menuMap = props.menuList.reduce(
    (acc, menuItem) => {
      const firstChild = menuItem.children[0];
      if (firstChild && isTreeNode(firstChild)) {
        menuItem.children
          .filter((item): item is ToolboxTreeNode => isTreeNode(item))
          .forEach((childrenItem) => {
            childrenItem.children
              .filter((subItem): subItem is ToolboxLeafNode => isLeafNode(subItem))
              .forEach((subChildrenItem) => {
                Object.assign(acc, { [subChildrenItem.id]: subChildrenItem });
              });
          });
      } else {
        menuItem.children
          .filter((item): item is ToolboxLeafNode => isLeafNode(item))
          .forEach((item) => {
            Object.assign(acc, { [item.id]: item });
          });
      }
      return acc;
    },
    {} as Record<string, ToolboxLeafNode>,
  );

  const favorItem = computed(() => {
    return {
      children: (profile.value[profileFavorKey] || [])
        .map((item: string) => menuMap[item])
        .filter((item: string) => item),
      icon: 'star-fill',
      id: 'favor',
      name: t('我的收藏'),
    };
  });

  const usedItem = computed(() => {
    return {
      children: (profile.value[profileUsedKey] || [])
        .map((item: string) => menuMap[item])
        .filter((item: string) => item),
      icon: 'zuijinshiyong',
      id: 'used',
      name: t('最近使用'),
    };
  });

  const originDataList = computed(() =>
    [favorItem.value, usedItem.value].concat(props.menuList).filter((item) => item.children.length > 0),
  );

  watch(
    [searchKey, originDataList],
    () => {
      if (searchKey.value) {
        displayDataList.value = originDataList.value.reduce<UnwrapRef<typeof originDataList>>((acc, menuItem) => {
          if (hasChildGroups(menuItem)) {
            const filterChildren = menuItem.children
              .map((childrenItem: ToolboxTreeNode) => {
                const filterList = (childrenItem.children as ToolboxLeafNode[]).filter(
                  (subChildrenItem: ToolboxLeafNode) => subChildrenItem.name.includes(searchKey.value),
                );
                return { ...childrenItem, children: filterList };
              })
              .filter((childrenItem: ToolboxTreeNode) => childrenItem.children.length > 0);
            return filterChildren.length > 0 ? acc.concat({ ...menuItem, children: filterChildren }) : acc;
          } else {
            const filterList = menuItem.children.filter((childrenItem: ToolboxLeafNode) =>
              childrenItem.name.includes(searchKey.value),
            );
            return filterList.length > 0 ? acc.concat({ ...menuItem, children: filterList }) : acc;
          }
        }, []);
      } else {
        displayDataList.value = originDataList.value;
      }
    },
    {
      immediate: true,
    },
  );

  const getTheme = (index: number) => {
    const themeList = ['info', 'warning', 'danger', 'success'] as const;
    const themeIndex = index % themeList.length;
    return themeList[themeIndex];
  };

  /** 判断菜单项是否有子分组（二级树形结构） */
  const hasChildGroups = (menuItem: ToolboxTreeNode): boolean => {
    return menuItem.children.length > 0 && isTreeNode(menuItem.children[0]);
  };

  /** 获取树节点的子叶子节点列表 */
  const getLeafChildren = (node: ToolboxTreeNode): ToolboxLeafNode[] => {
    return node.children.filter((item): item is ToolboxLeafNode => isLeafNode(item));
  };
</script>
<style lang="less">
  .db-manage-toolbox-menu {
    width: 100%;
    height: 100%;
    background-color: #f5f7fa;

    .db-manage-toolbox-menu-search {
      width: 700px;
    }

    .bk-collapse-header {
      height: 32px;
      background: #eaebf0 !important;
    }

    .bk-collapse-icon {
      top: 7px;
    }

    .bk-collapse-content {
      padding: 16px 0 0;
    }

    .bk-collapse-block .bk-collapse-item {
      margin-bottom: 24px;
    }

    .tool-group {
      display: flex;
      height: 32px;
      align-items: center;
      border-radius: 2px;

      .tool-group-icon {
        width: 16px;
        height: 16px;
        margin-top: 2px;

        &.db-icon-star-fill {
          color: #f59500;
        }

        &.db-icon-zuijinshiyong {
          color: #3a84ff;
        }

        &.db-icon-chaxunyubiangeng {
          color: #23c353;
        }

        &.db-icon-baofen {
          color: #476bfe;
        }

        &.db-icon-data-recovery {
          color: #9e37e8;
        }

        &.db-icon-clone {
          color: #f79413;
        }

        &.db-icon-shujuqingli {
          color: #ea3636;
        }

        &.db-icon-cluster {
          color: #3886fc;
        }

        &.db-icon-node {
          color: #14c3d6;
        }

        &.db-icon-proxy {
          color: #3886fc;
        }

        &.db-icon-resource {
          color: #3a84ff;
        }
      }

      .tool-group-name {
        font-weight: bolder;
        color: #4d4f56;
      }

      .tool-group-desc {
        margin-left: 4px;
        font-size: 12px;
        color: #979ba5;
      }
    }

    .sub-group {
      width: 100%;

      &:not(:first-child) {
        margin-top: 16px;
      }

      .sub-group-name {
        padding-bottom: 8px;
        margin-bottom: 16px;
        border-bottom: 1px solid #eaebf0;
      }
    }

    .tool-list {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }

    .empty-exception {
      display: flex;
      height: 100%;
      align-items: center;
      justify-content: center;
    }
  }
</style>
