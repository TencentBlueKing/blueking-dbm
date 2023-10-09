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
    <BkSelect
      class="db-member-selector"
      :clearable="false"
      :collapse-tags="collapseTags"
      filterable
      :model-value="modelValue"
      multiple
      multiple-mode="tag"
      :remote-method="remoteFilter"
      @blur="handleBlur"
      @change="handleChange"
      @focus="handleFocus">
      <BkOption
        v-for="item of state.list"
        :key="item.username"
        :label="item.username"
        :value="item.username" />
    </BkSelect>
    <DbIcon
      v-bk-tooltips="$t('复制')"
      type="copy db-member-selector-copy"
      @click.stop="handleCopy" />
  </div>
</template>

<script setup lang="tsx">
  import { getUseList } from '@services/common';
  import type { GetUsesParams, UseItem } from '@services/types/common';

  import { useCopy } from '@hooks';

  interface Props {
    collapseTags?: boolean
  }

  withDefaults(defineProps<Props>(), {
    collapseTags: false,
  });
  const modelValue = defineModel<string[]>({
    default: () => [],
  });

  const copy = useCopy();

  const state = reactive({
    list: [] as UseItem[],
  });
  const isFocous = ref(false);

  /**
   * 获取人员列表
   */
  const fetchUseList = async (params: GetUsesParams = {}) => {
    await getUseList(params).then((res) => {
      // 过滤已经选中的用户
      state.list = res.results.filter(item => !modelValue.value?.includes(item.username));
    });
  };
  // 初始化加载
  fetchUseList({ limit: 200, offset: 0 });

  /**
   * 远程搜索人员
   */
  const remoteFilter = async (value: string) => {
    await fetchUseList({ fuzzy_lookups: value });
  };

  const handleChange = (values: string[]) => {
    modelValue.value = values;
  };

  const handleFocus = () => isFocous.value = true;
  const handleBlur = () => isFocous.value = false;

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
