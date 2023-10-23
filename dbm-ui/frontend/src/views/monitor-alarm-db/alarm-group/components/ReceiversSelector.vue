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
  <div class="receivers-selector-wrapper">
    <UserSelector
      v-if="!loading"
      v-model="modelValue"
      class="receivers-selector"
      :default-alternate="defaultAlternate"
      :fuzzy-search-method="fuzzySearchMethod"
      :render-list="renderList"
      :render-tag="renderTag"
      :search-from-default-alternate="false"
      tag-clearable />
  </div>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { Fragment } from 'vue/jsx-runtime';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getUseList } from '@services/common';
  import {
    getAlarmGroupList,
    getUserGroupList,
  } from '@services/monitorAlarm';

  import dbIcon from '@components/db-icon';

  interface Props {
    type: 'add' | 'edit' | 'copy' | '',
    isBuiltIn: boolean,
    bizId: number
  }

  interface Exposes {
    getSelectedReceivers: () => ServiceReturnType<typeof getAlarmGroupList>['results'][number]['receivers'];
  }

  interface RecipientItem {
    username: string,
    display_name: string,
    type: string,
  }

  const props = defineProps<Props>();
  const modelValue = defineModel<string[]>({
    required: true,
  });

  const { t } = useI18n();
  const route = useRoute();

  const isPlatform = route.matched[0]?.name === 'Platform';
  const modelValueOrigin = _.cloneDeep(modelValue.value);
  const itemMap: Record<string, RecipientItem> = {};

  const roleList = ref<RecipientItem[]>([]);

  // 获取用户组数据
  const { loading } = useRequest(getUserGroupList, {
    defaultParams: [props.bizId],
    onSuccess(userGroupList) {
      const newUserGroupList: RecipientItem[] = [];

      userGroupList.forEach((userGroupItem) => {
        const newUserGroupItem = {
          username: userGroupItem.id,
          display_name: userGroupItem.display_name,
          type: 'group',
        };
        itemMap[userGroupItem.id] = newUserGroupItem;
        newUserGroupList.push(newUserGroupItem);
      });

      roleList.value = newUserGroupList;
    },
  });

  const isClosable = (id: string) => {
    if (isPlatform || props.type !== 'edit') {
      return true;
    }
    return !(props.isBuiltIn && modelValueOrigin.includes(id));
  };

  const defaultAlternate = () => [{
    display_name: t('用户组'),
    username: 'role',
    children: _.cloneDeep(roleList.value),
  }];

  const fuzzySearchMethod = (keyword: string) => getUseList({
    fuzzy_lookups: keyword,
  }).then(searchList => ({
    next: false,
    results: [{
      display_name: t('个人用户'),
      username: 'role',
      children: searchList.results.map(userItem => ({
        username: userItem.username,
        display_name: userItem.username,
        type: 'group',
      })),
    }],
  }));

  const renderTag = (renderMethod: typeof h, node: Record<string, string>) => {
    const type = itemMap[node.username]?.type || 'user';

    return renderMethod(
      'div', {
        class: isClosable(node.username) ? '' : 'built-in',
      },
      [
        renderMethod(dbIcon, {
          class: 'receivers-selector-selected-tag-icon mr-4',
          type: type === 'group' ? 'yonghuzu' : 'dba-config',
        }),
        renderMethod(
          'span', {
            class: 'mr-4',
          },
          itemMap[node.username]?.display_name || node.username,
        ),
      ],
    );
  };

  const renderList = (renderMethod: typeof h, node: {
    user: RecipientItem
  }) => {
    const {
      type,
      display_name: displayName,
    } = node.user;

    return renderMethod(Fragment, [
      renderMethod(dbIcon, {
        class: 'receivers-selector-selected-tag-icon mr-4',
        type: type === 'group' ? 'yonghuzu' : 'dba-config',
      }),
      renderMethod('span', displayName),
    ]);
  };

  defineExpose<Exposes>({
    getSelectedReceivers() {
      return modelValue.value.map(modelValueItem => ({
        type: itemMap[modelValueItem]?.type || 'user',
        id: modelValueItem,
      }));
    },
  });
</script>

<style lang="less" scoped>
.receivers-selector-wrapper {
  .receivers-selector {
    width: 100%;
  }

  :deep(.user-selector-selected) {
    .built-in + .user-selector-selected-clear {
      display: none;
    }
  }
}
</style>

<style>
.receivers-selector-selected-tag-icon {
  font-size: 17.5px;
}
</style>
