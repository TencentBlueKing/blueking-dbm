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
  <BkSelect
    v-model="modelValue"
    allow-create
    collapse-tags
    filterable
    multiple
    multiple-mode="tag">
    <BkOption
      v-for="(item, index) in userList?.results"
      :id="item"
      :key="index"
      :name="item" />
    <template #tag="{ selected }">
      <BkTag
        v-for="item in selected"
        :key="item.value"
        closable
        :theme="userOptionList.findIndex((userOptionItem) => userOptionItem.value === item.value) > -1 ? '' : 'warning'"
        @close="(event: Event) => handleUserClose(item.value)">
        {{ item.value }}
      </BkTag>
    </template>
  </BkSelect>
</template>

<script setup lang="tsx">
  import { useRequest } from 'vue-request';

  import { getAccountUsers } from '@services/source/mysqlPermissionAccount';

  import { accoutMap } from './common/config';

  interface Expose {
    getUserList: (params: ServiceParameters<typeof getAccountUsers>) => void;
  }

  const modelValue = defineModel<string[]>({
    required: true,
  });

  const route = useRoute();

  const { accountType } = route.meta as { accountType: string };

  const userOptionList = computed(() =>
    (userList.value?.results || []).map((userItem) => ({
      label: userItem,
      value: userItem,
    })),
  );

  const { data: userList, run: runGetUserList } = useRequest(accoutMap[accountType].ruleApi, {
    manual: true,
  });

  const handleUserClose = (value: string) => {
    const index = modelValue.value.findIndex((userItem) => userItem === value);
    if (index > -1) {
      modelValue.value.splice(index, 1);
    }
  };

  defineExpose<Expose>({
    getUserList(params) {
      runGetUserList(params);
    },
  });
</script>
