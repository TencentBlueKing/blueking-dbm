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
  <div
    class="member-selector-wrapper"
    :class="{ 'is-hover': isHover }"
    @mouseenter="handleHover"
    @mouseleave="handleBlur">
    <UserSelector
      ref="userSelectorRef"
      v-model="modelValue"
      class="member-selector"
      :exact-search-method="exactSearchMethod"
      fast-clear
      :fixed-height="false"
      :fuzzy-search-method="fuzzySearchMethod"
      :paste-validator="pasteValidator"
      :render-list="renderList"
      :render-tag="renderTag"
      :search-from-default-alternate="false"
      tag-clearable
      @remove-selected="handleRemoveSelected" />
    <DbIcon
      v-if="modelValue.length > 0"
      v-bk-tooltips="t('复制')"
      class="db-member-selector-copy"
      type="copy"
      @click.stop="handleCopy" />
  </div>
</template>

<script setup lang="ts">
  import { Fragment } from 'vue/jsx-runtime';
  import { useI18n } from 'vue-i18n';

  import { getUserList } from '@services/source/user';

  import { execCopy } from '@utils';

  const emits = defineEmits<{
    (e: 'change', value: string[]): void;
  }>();

  const modelValue = defineModel<string[]>({
    required: true,
  });

  const { t } = useI18n();

  const userSelectorRef = ref();
  const isHover = ref(false);

  const exactSearchMethod = () =>
    getUserList({
      exact_lookups: modelValue.value.join(','),
    }).then((result) => result.results);

  const pasteValidator = (values: string[]) => values;

  const fuzzySearchMethod = (keyword: string) =>
    getUserList({
      fuzzy_lookups: keyword,
    }).then((searchList) => ({
      next: false,
      results: searchList.results.map((userItem) => ({
        username: userItem.username,
        display_name: userItem.display_name,
      })),
    }));

  const renderTag = (
    renderMethod: typeof h,
    node: {
      username: string;
      user: {
        username: string;
        display_name: string;
      };
    },
  ) =>
    renderMethod('div', null, [
      renderMethod(
        'span',
        {
          class: 'mr-4',
        },
        `${node.username}(${node.user?.display_name || node.username})`,
      ),
    ]);

  const renderList = (
    renderMethod: typeof h,
    node: {
      user: {
        username: string;
        display_name: string;
        type: string;
      };
    },
  ) => {
    const { display_name: displayName, username } = node.user;

    return renderMethod(Fragment, [renderMethod('span', `${username}(${displayName})`)]);
  };

  watch(modelValue, () => {
    console.log('from watchch modelvall = ', modelValue.value);
    emits('change', modelValue.value);
  });

  const handleRemoveSelected = () => {
    userSelectorRef.value.search();
  };

  const handleHover = () => {
    isHover.value = true;
  };

  const handleBlur = () => {
    isHover.value = false;
  };

  const handleCopy = () => {
    execCopy(modelValue.value.join(';'), t('复制成功，共n条', { n: modelValue.value.length }));
  };
</script>

<style lang="less" scoped>
  .member-selector-wrapper {
    position: relative;
    line-height: 1;

    &.is-hover {
      :deep(.user-selector-clear) {
        visibility: visible;
      }
    }

    &:hover {
      .db-member-selector-copy {
        display: block;
      }
    }

    .member-selector {
      width: 100%;
    }

    .db-member-selector-copy {
      position: absolute;
      top: 50%;
      right: 24px;
      z-index: 99;
      display: none;
      width: 20px;
      height: 20px;
      margin-top: -10px;
      font-size: 12px;
      line-height: 20px;
      color: #979ba5;
      cursor: pointer;
      background-color: white;

      &:hover {
        color: @primary-color;
        background-color: #e1ecff;
      }
    }
  }
</style>
