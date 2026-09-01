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
  <div class="db-manage-toolbox-navigation">
    <BkInput
      v-model.tirm="serachKey"
      class="tool-search"
      clearable
      :placeholder="t('请输入')"
      type="search" />
    <BkException
      v-if="!isFilterMenuExit"
      class="pt-40"
      :description="t('搜索为空')"
      scene="part"
      type="search-empty" />
    <div
      v-else
      class="tool-list-wrapper">
      <ScrollFaker>
        <BkCollapse :model-value="activeCollapseList">
          <RenderMenuGroup
            v-if="menuGroupList && menuGroupList.length > 0"
            :menu-group-list="menuGroupList"
            :menu-list="renderMenuList"
            :serach-key="serachKey" />
          <RenderMenuList
            v-else
            :data="renderMenuList"
            :serach-key="serachKey" />
        </BkCollapse>
      </ScrollFaker>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useDebouncedRef } from '@hooks';

  import { encodeRegexp } from '@utils';

  import RenderMenuGroup from './components/RenderMenuGroup.vue';
  import RenderMenuList from './components/RenderMenuList.vue';

  export interface Props {
    data: {
      children: {
        bind?: string[];
        dbConsoleValue?: string;
        id: string;
        name: string;
      }[];
      icon: string;
      id: string;
      name: string;
    }[];
    menuGroupList?: {
      description: string;
      id: string;
      menuList: string[];
      name: string;
    }[];
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const isFilterMenuExit = ref(true);

  const serachKey = useDebouncedRef('');

  const renderMenuList = computed(() => {
    const regex = new RegExp(encodeRegexp(serachKey.value), 'i');
    return props.data.reduce(
      (result, item) => {
        result.push({
          ...item,
          children: item.children.filter((child) => regex.test(child.name)),
        });
        return result;
      },
      [] as typeof props.data,
    );
  });

  const activeCollapseList = computed(() => {
    return renderMenuList.value.map((item) => item.id);
  });
</script>
<style lang="less">
  .db-manage-toolbox-navigation {
    height: 100%;
    padding: 16px 0;
    background-color: #f5f7fa;

    .tool-search {
      display: flex;
      width: calc(100% - 32px);
      margin: 0 auto;
    }

    .tool-list-wrapper {
      height: calc(100% - 40px);
      margin-top: 8px;

      .tool-group-name {
        height: 32px;
        padding-left: 21px;
        margin: 16px 0 4px;
        line-height: 32px;
        background: #eaebf0;

        .type-title {
          font-size: 12px;
          color: #313238;
        }

        .type-icon {
          margin-left: 4px;
        }
      }

      .drag-move {
        transition: all 0.5s ease;
      }
    }

    .bk-collapse-wrapper {
      .bk-collapse-header {
        height: 32px;
        padding: 0 16px;
        line-height: 32px;
        background: transparent;

        .bk-collapse-title {
          display: block;
          margin-left: 0;
        }

        &:hover {
          background-color: unset;
        }
      }

      .bk-collapse-content {
        padding: 0 16px;
      }

      .bk-collapse-icon {
        display: none !important;
      }

      .bk-collapse-item {
        margin-bottom: 16px;

        &:last-child {
          margin-bottom: 0;
        }
      }

      .bk-collapse-item-active {
        .toolbox-side-status {
          transform: rotate(0);
        }
      }
    }

    .toolbox-menu-group-name {
      height: 32px;
      padding-left: 21px;
      margin: 16px 0 4px;
      line-height: 32px;
      background: #eaebf0;

      .type-title {
        font-size: 12px;
        color: #313238;
      }

      .type-icon {
        margin-left: 4px;
      }
    }

    .toolbox-side-header {
      display: flex;
      align-items: center;
      padding-right: 8px;
      border-radius: 2px;

      &:hover {
        background-color: #eaebf0;

        .toolbox-side-drag {
          display: block;
        }
      }
    }

    .toolbox-side-status {
      margin-left: 4px;
      transform: rotate(-90deg);
      transition: all 0.2s;
    }

    .toolbox-side-icon {
      display: flex;
      align-items: center;
      width: 24px;
      height: 24px;
      margin: 0 8px 0 4px;
      font-size: @font-size-large;
      line-height: 24px;
      color: @primary-color;
      background-color: #e1ecff;
      border-radius: 50%;
      justify-content: center;

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

    .toolbox-side-title {
      font-size: @font-size-mini;
      font-weight: bold;
      color: @title-color;
      flex: 1;
    }

    .toolbox-side-drag {
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
        content: '';
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

    .toolbox-side-content {
      font-size: @font-size-mini;
    }

    .toolbox-side-item {
      display: flex;
      align-items: center;
      height: 32px;
      padding: 0 16px;
      margin-top: 8px;
      overflow: hidden;
      line-height: 32px;
      color: @default-color;
      cursor: pointer;
      background-color: @bg-white;
      border-radius: 2px;

      &:hover {
        box-shadow:
          0 2px 4px 0 rgb(0 0 0 / 10%),
          0 2px 4px 0 rgb(25 25 41 / 5%);

        .toolbox-side-favor {
          display: block;
        }
      }

      .toolbox-side-left {
        display: flex;
        align-items: center;
      }

      .count {
        flex-shrink: 0;
      }
    }

    .toolbox-side-item--active {
      color: @primary-color;
      background-color: #e1ecff;
    }

    .toolbox-side-favor {
      display: none;
      margin-left: auto;

      &.db-icon-star-fill {
        display: block;
        color: @warning-color;
      }
    }
  }
</style>
