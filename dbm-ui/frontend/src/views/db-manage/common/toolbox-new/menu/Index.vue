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
      <template v-if="fixedDataList.length > 0 || groupDataList.length > 0">
        <BkCollapse
          v-if="fixedDataList.length > 0"
          v-model="fixedActiveIndex"
          header-icon-align="right"
          use-block-theme>
          <BkCollapsePanel
            v-for="menuItem in fixedDataList"
            :key="menuItem.id"
            :name="menuItem.id">
            <div class="tool-group">
              <DbIcon
                class="tool-group-icon"
                :type="menuItem.icon" />
              <div class="tool-group-name ml-4">{{ menuItem.name }}</div>
            </div>
            <template #content>
              <div class="tool-list">
                <MenuItem
                  v-for="childrenItem in getLeafChildren(menuItem)"
                  :key="childrenItem.id"
                  :data="childrenItem">
                </MenuItem>
              </div>
            </template>
          </BkCollapsePanel>
        </BkCollapse>
        <div
          v-if="groupDataList.length > 0 && !searchKey"
          class="group-directory-control ml-16">
          <BkButton
            text
            theme="primary"
            @click="handleToggleAll">
            {{ isAllExpanded ? t('收起全部分组') : t('展开全部分组') }}
          </BkButton>
        </div>
        <BkCollapse
          v-if="groupDataList.length > 0"
          v-model="groupActiveIndex"
          header-icon-align="right"
          use-block-theme>
          <BkCollapsePanel
            v-for="menuItem in groupDataList"
            :key="menuItem.id"
            :name="menuItem.id">
            <div class="tool-group">
              <DbIcon
                class="tool-group-icon"
                :type="menuItem.icon" />
              <div class="tool-group-name ml-4">{{ menuItem.name }}</div>
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
                        v-for="subChildrenItem in getLeafChildren(childrenItem)"
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
      </template>
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
  import { useRoute } from 'vue-router';

  import { useDebouncedRef } from '@hooks';

  import { useUserProfile } from '@stores';

  import { DBTypes, toolboxProfileKeyMap } from '@common/const';

  import { t } from '@locales/index';

  import type { ToolboxLeafNode, ToolboxTreeNode } from '../common/types';
  import { getLeafChildren, hasChildGroups, isLeafNode, isTreeNode } from '../common/utils';

  import MenuItem from './components/MenuItem.vue';

  interface Props {
    menuList: ToolboxTreeNode[];
  }

  const props = defineProps<Props>();

  const route = useRoute();
  const profileStore = useUserProfile();
  const { profile } = storeToRefs(profileStore);

  const searchKey = useDebouncedRef('');
  /** 我的收藏 / 最近使用默认展开 */
  const fixedActiveIndex = ref(['favor', 'used']);
  /** 分组目录默认全部折叠 */
  const groupActiveIndex = ref<string[]>([]);

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

  const favorItem = computed<ToolboxTreeNode>(() => {
    return {
      children: (profile.value[profileFavorKey] || [])
        .map((item: string) => menuMap[item])
        .filter((item: ToolboxLeafNode) => item),
      icon: 'star-fill',
      id: 'favor',
      name: t('我的收藏'),
    };
  });

  const usedItem = computed<ToolboxTreeNode>(() => {
    return {
      children: (profile.value[profileUsedKey] || [])
        .map((item: string) => menuMap[item])
        .filter((item: ToolboxLeafNode) => item),
      icon: 'zuijinshiyong',
      id: 'used',
      name: t('最近使用'),
    };
  });

  /** 按工具名过滤，无命中项的分组整体隐藏 */
  const filterBySearchKey = (menuList: ToolboxTreeNode[]): ToolboxTreeNode[] => {
    return menuList.reduce<ToolboxTreeNode[]>((acc, menuItem) => {
      if (hasChildGroups(menuItem)) {
        const filterChildren = menuItem.children
          .map((childrenItem) => {
            const filterList = (childrenItem.children as ToolboxLeafNode[]).filter((subChildrenItem) =>
              subChildrenItem.name.includes(searchKey.value),
            );
            return { ...childrenItem, children: filterList };
          })
          .filter((childrenItem) => childrenItem.children.length > 0);
        return filterChildren.length > 0 ? acc.concat({ ...menuItem, children: filterChildren }) : acc;
      }
      const filterList = (menuItem.children as ToolboxLeafNode[]).filter((childrenItem) =>
        childrenItem.name.includes(searchKey.value),
      );
      return filterList.length > 0 ? acc.concat({ ...menuItem, children: filterList }) : acc;
    }, []);
  };

  const fixedDataList = computed(() => {
    const menuList = [favorItem.value, usedItem.value].filter((item) => item.children.length > 0);
    return searchKey.value ? filterBySearchKey(menuList) : menuList;
  });

  const groupDataList = computed(() => {
    const menuList = props.menuList.filter((item) => item.children.length > 0);
    return searchKey.value ? filterBySearchKey(menuList) : menuList;
  });

  // 有搜索词时自动展开命中分组并隐藏展开/收起控件，清空后恢复默认折叠
  watch(searchKey, (value) => {
    groupActiveIndex.value = value ? groupDataList.value.map((item) => item.id) : [];
  });

  const getTheme = (index: number) => {
    const themeList = ['info', 'warning', 'danger', 'success'] as const;
    const themeIndex = index % themeList.length;
    return themeList[themeIndex];
  };

  /** 全部分组均已展开 */
  const isAllExpanded = computed(
    () =>
      groupDataList.value.length > 0 && groupDataList.value.every((item) => groupActiveIndex.value.includes(item.id)),
  );

  /** 未全部展开时展开全部，已全部展开时收起全部 */
  const handleToggleAll = () => {
    groupActiveIndex.value = isAllExpanded.value ? [] : groupDataList.value.map((item) => item.id);
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

    .group-directory-control {
      display: flex;
      margin-bottom: 16px;
      font-size: 12px;
      align-items: center;
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
