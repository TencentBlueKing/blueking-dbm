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
  <UserSelector
    ref="userSelectorRef"
    v-model="modelValue"
    class="member-selector"
    :exact-search-method="exactSearchMethod"
    :fixed-height="false"
    :fuzzy-search-method="fuzzySearchMethod"
    :paste-validator="pasteValidator"
    :render-list="renderList"
    :render-tag="renderTag"
    :search-from-default-alternate="false"
    tag-clearable
    @remove-selected="handleRemoveSelected" />
</template>

<script setup lang="ts">
  import { Fragment } from 'vue/jsx-runtime';

  import { getUserList } from '@services/source/user';

  const modelValue = defineModel<string[]>({
    required: true,
  });

  const userSelectorRef = ref();

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
        display_name: userItem.display_name,
        username: userItem.username,
      })),
    }));

  const renderTag = (
    renderMethod: typeof h,
    node: {
      user: {
        display_name: string;
        username: string;
      };
      username: string;
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
        display_name: string;
        type: string;
        username: string;
      };
    },
  ) => {
    const { display_name: displayName, username } = node.user;

    return renderMethod(Fragment, [renderMethod('span', `${username}(${displayName})`)]);
  };

  const handleRemoveSelected = () => {
    userSelectorRef.value.search();
  };
</script>

<style lang="less" scoped>
  .member-selector {
    width: 100%;
  }
</style>
