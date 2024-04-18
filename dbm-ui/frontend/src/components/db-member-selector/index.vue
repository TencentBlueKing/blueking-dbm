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
    class="db-member-selector-wrapper"
    :class="{'is-focus': isFocous}">
    <BkTagInput
      v-model="modelValue"
      allow-auto-match
      allow-create
      :create-tag-validator="createTagValidator"
      has-delete-icon
      :list="peopleList"
      @input="remoteFilter" />
    <DbIcon
      v-bk-tooltips="t('复制')"
      type="copy db-member-selector-copy"
      @click.stop="handleCopy" />
  </div>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { getUserList } from '@services/source/user';

  import { useCopy } from '@hooks';

  type GetUsesParams = ServiceParameters<typeof getUserList>

  const modelValue = defineModel<string[]>({
    default: () => [],
  });

  const copy = useCopy();
  const { t } = useI18n();

  const peopleList = ref<{
    id: string,
    name: string,
  }[]>([]);

  const isFocous = ref(false);

  const createTagValidator = (tag: string) => !!peopleList.value.find(item => item.name === tag);

  /**
   * 获取人员列表
   */
  const fetchUseList = async (params: GetUsesParams = {}) => {
    await getUserList(params).then((res) => {
      // 过滤已经选中的用户
      peopleList.value = res.results.filter(item => !modelValue.value?.includes(item.username)).map(item => ({
        id: item.username,
        name: item.username,
      }));
    });
  };
  // 初始化加载
  fetchUseList({ limit: 200, offset: 0 });

  /**
   * 远程搜索人员
   */
  const remoteFilter = _.debounce((value: string) => fetchUseList({ fuzzy_lookups: value }), 500);

  const handleCopy = () => {
    copy(modelValue.value.join(';'));
  };
</script>

<style lang="less" scoped>
.db-member-selector-wrapper {
  position: relative;

  &:hover,
  &.is-focus {
    .db-member-selector-copy {
      display: block;
    }
  }
}

.db-member-selector-copy {
  position: absolute;
  top: 50%;
  right: 2px;
  z-index: 99;
  display: none;
  width: 20px;
  height: 20px;
  margin-top: -10px;
  margin-right: 4px;
  font-size: 16px;
  line-height: 20px;
  cursor: pointer;
  background-color: white;

  &:hover {
    color: @primary-color;
    background-color: #e1ecff;
  }
}
</style>
