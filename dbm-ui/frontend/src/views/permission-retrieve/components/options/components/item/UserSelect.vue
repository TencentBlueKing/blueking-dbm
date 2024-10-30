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
    class="permission-user-select"
    collapse-tags
    filterable
    multiple
    multiple-mode="tag"
    :placeholder="t('请选择或直接输入账号，Enter完成输入')">
    <BkOption
      v-for="item in userOptionList"
      :id="item.value"
      :key="item.value"
      :name="item.label" />
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
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type { AccountTypes, ClusterTypes } from '@common/const';
  import { batchSplitRegex } from '@common/regex';

  import accoutMap from '../common/config';

  interface Props {
    formData: {
      ips: string;
      immute_domains: string;
      users: string[];
      dbs: string[];
      cluster_type: ClusterTypes;
      account_type: AccountTypes;
      is_master: boolean;
    };
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<string[]>({
    required: true,
  });

  const { t } = useI18n();

  const userOptionList = computed(() =>
    (userList.value?.results || []).map((userItem) => ({
      label: userItem,
      value: userItem,
    })),
  );

  const { data: userList, run: runGetUserList } = useRequest(
    accoutMap[props.formData.account_type as keyof typeof accoutMap].ruleApi,
    {
      manual: true,
    },
  );

  watch(
    () => [props.formData.ips, props.formData.immute_domains],
    () => {
      if (props.formData.ips && props.formData.immute_domains) {
        runGetUserList({
          ips: props.formData.ips.replace(batchSplitRegex, ','),
          immute_domains: props.formData.immute_domains.replace(batchSplitRegex, ','),
          cluster_type: props.formData.cluster_type,
          account_type: props.formData.account_type,
          limit: -1,
          offset: 0,
        });
      }
    },
  );

  const handleUserClose = (value: string) => {
    const index = modelValue.value.findIndex((userItem) => userItem === value);
    if (index > -1) {
      modelValue.value.splice(index, 1);
    }
  };
</script>

<style lang="less" scoped>
  .permission-user-select {
    :deep(.bk-select-tag-wrapper) {
      flex: 1;
    }
  }
</style>
