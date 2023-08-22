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
  <BkPopover
    v-model:is-show="state.isShow"
    :arrow="false"
    boundary="parent"
    placement="bottom-start"
    :theme="wrapperCls"
    trigger="manual"
    :width="320">
    <div
      v-clickoutside:[appContentRef]="handleClose"
      class="dbm-app-selector-trigger"
      @click="handleToggle">
      <template v-if="collapsed">
        <span class="dbm-app-selector__name">{{ collapsedName }}</span>
      </template>
      <template v-else>
        <div
          v-overflow-tips.right
          class="dbm-app-selector__display text-overflow">
          {{ bizInfo?.name }}
        </div>
        <i class="db-icon-up-big dbm-app-selector__arrow" />
      </template>
    </div>
    <template #content>
      <div
        ref="appContentRef"
        class="dbm-app-selector-main">
        <div class="dbm-app-selector__search">
          <input
            ref="searchRef"
            v-model="state.search"
            :placeholder="$t('关键字')"
            spellcheck="false"
            @compositionend="handleCompositionEnd"
            @compositionstart="handleCompositionStart"
            @input="handleSearchInput"
            @keydown.down.prevent="handleMove('down')"
            @keydown.enter.prevent="handleSelect"
            @keydown.up.prevent="handleMove('up')">
          <i class="db-icon-search" />
        </div>
        <div
          ref="listRef"
          class="dbm-app-selector-list"
          @scroll="handleScroll">
          <template v-if="renderList.length > 0">
            <!-- <BkVirtualRender
              :height="238"
              :line-height="32"
              :list="renderList"
              :preload-item-count="10">
              <template #default="{ data }">
              </template>
            </BkVirtualRender> -->
            <AuthComponent
              v-for="(item, index) in renderList"
              :key="item.bk_biz_id"
              action-id="DB_MANAGE"
              :permission="item.permission.db_manage"
              :resource-id="item.bk_biz_id"
              resource-type="BUSINESS">
              <div
                class="dbm-app-selector-item"
                :class="[{
                  'dbm-app-selector-item--selected': item.bk_biz_id === globalBizsStore.currentBizId,
                  'dbm-app-selector-item--hover': index === state.activeIndex,
                }]"
                @click="handleChange(item.bk_biz_id)"
                @mouseenter.self="handleItemMouseenter(index)">
                <div class="dbm-app-selector-item__info">
                  <span class="dbm-app-selector-item__name text-overflow">{{ item.name }}</span>
                  <span class="dbm-app-selector-item__id">(#{{ item.bk_biz_id }})</span>
                </div>
                <svg
                  class="dbm-app-selector-item__collection"
                  :class="[{
                    'dbm-app-selector-item__collection--favor': isFavor(item)
                  }]"
                  @click.stop="handleFavor(item)">
                  <use :xlink:href="isFavor(item) ? '#db-icon-star-fill' : '#db-icon-star'" />
                </svg>
              </div>
              <template #forbid>
                <div class="dbm-app-selector-item">
                  <div class="dbm-app-selector-item__info">
                    <span class="dbm-app-selector-item__name text-overflow">{{ item.name }}</span>
                    <span class="dbm-app-selector-item__id">(#{{ item.bk_biz_id }})</span>
                  </div>
                </div>
              </template>
            </AuthComponent>
          </template>
          <template v-else>
            <div class="dbm-app-selector__empty">
              {{ $t('无匹配数据') }}
            </div>
          </template>
        </div>
        <div
          class="dbm-app-selector__create"
          @click="handleToCreate">
          <i class="db-icon-plus-circle mr-6" />
          {{ $t('新建业务') }}
        </div>
      </div>
    </template>
  </BkPopover>
</template>

<script lang="ts">
  import { Message } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import type { BizItem } from '@services/types/common';

  import {
    useGlobalBizs,
    useSystemEnviron,
    useUserProfile,
  } from '@stores';

  import { UserPersonalSettings } from '@common/const';

  import { classes } from '@utils';

  import { reload } from './utils';

  interface FavorBizInfo extends BizItem {
    favored: boolean,
  }

  export default {
    name: 'AppSelector',
  };
</script>

<script setup lang="ts">
  defineProps({
    collapsed: {
      type: Boolean,
      default: false,
    },
  });

  const router = useRouter();
  const route = useRoute();
  const globalBizsStore = useGlobalBizs();
  const systemEnvironStore = useSystemEnviron();
  const userProfileStore = useUserProfile();
  const { t } = useI18n();

  const listRef = ref<HTMLDivElement>();
  const isChineseInput = ref(false);
  const state = reactive({
    isShow: false,
    search: '',
    activeIndex: -1,
    isPrevent: false,
    bizList: [] as FavorBizInfo[],
  });

  const wrapperCls = computed(() => {
    const clsObject = {
      dark: true,
      'dbm-app-selector': true,
      'dbm-app-selector--focus': state.isShow,
    };

    return classes(clsObject);
  });

  const appContentRef = ref<HTMLDivElement>();
  const searchRef = ref<HTMLInputElement>();
  // 业务列表设置
  const searchValue = (value: string) => value.toLowerCase().includes(state.search.toLowerCase());
  const renderList = computed(() => (
    state.bizList.filter(item => (
      searchValue(String(item.bk_biz_id))
      || searchValue(item.name)
      || searchValue(item.pinyin_name)
      || searchValue(item.pinyin_head)
    ))
  ));

  /**
   * 格式化业务列表
   */
  const formatBizList = () => {
    const favorList: FavorBizInfo[] = [];
    const unfavorList: FavorBizInfo[] = [];
    for (const biz of globalBizsStore.bizs) {
      const id = String(biz.bk_biz_id);
      if (favors.value.includes(id)) {
        favorList.push({
          ...biz,
          favored: true,
        });
      } else {
        unfavorList.push({
          ...biz,
          favored: false,
        });
      }
    }

    const list = favorList.concat(unfavorList);
    for (let i = 0; i < list.length;i++) {
      const item = list[i];
      if (item.bk_biz_id === globalBizsStore.currentBizId) {
        state.activeIndex = i;
      }
    }

    return list;
  };

  /**
   * set biz id
   */
  const bizInfo = computed(() => globalBizsStore.bizs.find(item => item.bk_biz_id === globalBizsStore.currentBizId));
  const collapsedName = computed(() => bizInfo.value?.name.slice(0, 1));

  onBeforeMount(() => {
    const routeBizId = Number(route.params.bizId);
    if (
      routeBizId
      && globalBizsStore.currentBizId !== routeBizId
      && globalBizsStore.bizs.find(item => item.bk_biz_id === routeBizId)
    ) {
      globalBizsStore.currentBizId = routeBizId;
    }

    if (globalBizsStore.currentBizId !== routeBizId) {
      handleChange(globalBizsStore.currentBizId);
    }

    state.bizList = formatBizList();
  });

  /**
   * toggle selector
   */
  const handleToggle = () => {
    state.isShow = !state.isShow;

    if (state.isShow) {
      state.bizList = formatBizList();
      setTimeout(() => {
        searchRef.value?.focus?.();
      }, 500);
    }
  };

  /**
   * close selector
   */
  const handleClose = () => {
    state.isShow = false;
  };

  /**
   * change biz
   */
  const handleChange = (id: number) => {
    // 保存当前用户选中的业务
    userProfileStore.updateProfile({
      label: UserPersonalSettings.ACTIVATED_APP,
      values: id,
    });

    state.isShow = false;
    const { path, meta } = route;
    // 切换业务后需要回退到对应首页
    if (meta.activeMenu) {
      const backRoute = router.resolve({ name: meta.activeMenu });
      reload(backRoute.path, id);
      return;
    }

    reload(path, id);
  };

  /**
   * 收藏业务
   */
  const favors = computed(() => userProfileStore.profile[UserPersonalSettings.APP_FAVOR] || []);

  // 为了解决虚拟滚动响应式问题
  const isFavor = (item: FavorBizInfo) => favors.value.includes(String(item.bk_biz_id));

  // 确保是最新的个人配置
  userProfileStore.fetchProfile();

  const handleFavor = (info: FavorBizInfo) => {
    const id = String(info.bk_biz_id);
    const index = favors.value.findIndex((key: string) => key === id);
    const isFavored = index > -1;
    const params = {
      label: UserPersonalSettings.APP_FAVOR,
      values: favors.value,
    };
    if (isFavored) {
      params.values.splice(index, 1);
    } else {
      params.values.push(id);
    }
    userProfileStore.updateProfile(params)
      .then(() => {
        // eslint-disable-next-line no-param-reassign
        info.favored = !isFavored;
        Message({
          message: isFavored ? t('取消收藏成功') : t('收藏成功'),
          theme: 'success',
        });
      });
  };

  const handleSearchInput = () => {
    state.activeIndex = 0;
  };

  const handleCompositionStart = () => {
    isChineseInput.value = true;
  };

  const handleCompositionEnd = () => {
    isChineseInput.value = false;
  };

  const handleSelect = () => {
    // 中文模式下触发的enter
    if (isChineseInput.value) return;

    const activeItem = listRef.value?.querySelector?.('.dbm-app-selector-item--hover') as HTMLDivElement;
    if (activeItem) {
      activeItem.click();
    }
  };

  const handleScroll = () => {
    state.isPrevent = false;
  };

  const handleItemMouseenter = (index: number) => {
    if (!state.isPrevent) {
      state.activeIndex = index;
    }
  };

  const handleMove = (direction: 'down' | 'up') => {
    const len = renderList.value.length;
    if (direction === 'down') {
      state.activeIndex += 1;
      if (state.activeIndex === len) {
        state.activeIndex = 0;
      }
    } else if (direction === 'up') {
      state.activeIndex -= 1;
      if (state.activeIndex < 0) {
        state.activeIndex = len - 1;
      }
    }
    nextTick(() => {
      const wrapperElement = listRef.value;
      if (wrapperElement) {
        const wrapperHeight = wrapperElement.getBoundingClientRect().height;
        const activeOffsetTop = (wrapperElement.querySelector('.dbm-app-selector-item--hover') as HTMLElement).offsetTop + 32;
        state.isPrevent = true; // 防止设置 scrollTop 过程中触发 mouseenter
        if (activeOffsetTop > wrapperHeight) {
          wrapperElement.scrollTop = activeOffsetTop - wrapperHeight;
        } else if (activeOffsetTop <= 42) {
          wrapperElement.scrollTop = 0;
        }
      }
    });
  };

  /**
   * 跳转到新建业务
   */
  const handleToCreate = () => {
    const { BK_CMDB_URL } = systemEnvironStore.urls;
    if (BK_CMDB_URL) {
      window.open(`${BK_CMDB_URL}/#/resource/business`, '_blank');
    }
  };
</script>

<style lang="less">
  .dbm-app-selector {
    &.bk-popover {
      padding: 0;
      background-color: #182233;
      border: 1px solid #2f3847;
      box-shadow: 0 2px 3px 0 rgb(0 0 0 / 10%);
    }

    &-trigger {
      position: relative;
      display: block;
      width: calc(100% - 28px);
      margin: 10px auto;
    }

    &__name {
      display: inline-block;
      height: 32px;
      min-width: 32px;
      padding: 0 10px;
      font-size: @font-size-mini;
      line-height: 32px;
      color: #f0f1f5;
      text-align: center;
      cursor: pointer;
      background-color: #30384e;
    }

    &__display {
      width: 100%;
      height: 32px;
      padding: 0 24px 0 10px;
      font-size: @font-size-mini;
      line-height: 32px;
      color: #f0f1f5;
      cursor: pointer;
      background-color: #30384e;
      border: none;
      border-radius: 2px;
      outline: none;
    }

    &__arrow {
      position: absolute;
      top: 9px;
      right: 8px;
      font-size: 14px;
      color: @gray-color;
      pointer-events: none;
      transform: rotate(180deg);
      transition: all 0.15s;
    }

    &__search {
      position: relative;
      padding: 0 10px;

      input {
        width: 100%;
        height: 32px;
        padding: 0 10px 0 30px;
        line-height: 32px;
        background: transparent;
        border: none;
        border-bottom: 1px solid #404a5c;
        outline: none;

        &::placeholder {
          color: #747e94;
        }
      }

      .db-icon-search {
        position: absolute;
        top: 8px;
        left: 10px;
        font-size: @font-size-large;
        color: @gray-color;
      }
    }

    &-list {
      position: relative;
      max-height: 238px;
      margin-top: 8px;
      margin-bottom: 8px;
      overflow-y: auto;

      &::-webkit-scrollbar {
        width: 6px;
      }

      &::-webkit-scrollbar-thumb {
        background-color: #5f6e85;
        border-radius: 3px;
      }
    }

    &-item {
      display: flex;
      height: 32px;
      padding: 0 16px 0 10px;
      line-height: 32px;
      color: @light-gray;
      cursor: pointer;
      transition: all 0.1s;
      align-items: center;

      &__info {
        display: flex;
        padding-right: 4px;
        overflow: hidden;
        flex: 1;
      }

      &__id {
        padding-left: 4px;
        color: @gray-color;
        flex-shrink: 0;
      }

      &__collection {
        display: none;
        width: 1em;
        height: 1em;
        color: @gray-color;
        fill: currentcolor;
        flex-shrink: 0;
        box-sizing: content-box;

        &--favor {
          display: block;
          color: #ffb848;
        }
      }

      &:hover {
        .dbm-app-selector-item__collection {
          display: block;
        }
      }

      &--selected {
        color: #f0f1f5;
        background-color: #2d3542;
      }

      &--hover,
      &:hover {
        color: #f0f1f5;
        background: #294066;
      }
    }

    &__empty {
      text-align: center;
    }

    &__create {
      display: flex;
      align-items: center;
      height: 32px;
      padding: 0 10px;
      color: @light-gray;
      cursor: pointer;
      background: #28354d;
      border-radius: 0 0 1px 1px;

      .db-icon-plus-circle {
        font-size: 14px;
      }
    }

    &--focus {
      .dbm-app-selector__arrow {
        transform: rotate(0);
      }
    }

    .permission-disabled {
      color: #70737a !important;
      cursor: default !important;

      * {
        color: #70737a !important;
      }
    }
  }
</style>
