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
    class="receivers-selector-wrapper"
    :class="{'is-focus': isFocous}">
    <BkSelect
      class="receivers-selector"
      :clearable="false"
      filterable
      :model-value="modelValue"
      multiple
      multiple-mode="tag"
      :remote-method="remoteFilter"
      @blur="handleBlur"
      @change="handleChange"
      @focus="handleFocus">
      <BkOptionGroup
        collapsible
        :label="t('用户组')">
        <BkOption
          v-for="item of userGroupList"
          :key="item.id"
          :disabled="item.disabled"
          :label="item.display_name"
          :value="item.id" />
      </BkOptionGroup>
      <BkOptionGroup
        collapsible
        :label="t('个人用户')">
        <BkOption
          v-for="item of userList"
          :key="item.username"
          :label="item.username"
          :value="item.username" />
      </BkOptionGroup>
      <template #tag="{ selected }">
        <BkTag
          v-for="selectedItem in findSeletedItem(selected)"
          :key="selectedItem.id"
          :closable="isClosable(selectedItem.id)"
          @close="handleSelectedClose(selectedItem.id)">
          <template #icon>
            <DbIcon
              class="selected-tag-icon"
              :type="selectedItem.type === 'group' ? 'yonghuzu' : 'dba-config'" />
          </template>
          {{ selectedItem.display_name }}
        </BkTag>
      </template>
    </BkSelect>
    <DbIcon
      v-bk-tooltips="t('复制')"
      type="copy receivers-selector-copy"
      @click.stop="handleCopy" />
  </div>
</template>

<script setup lang="ts">
  import type { ISelected } from 'bkui-vue/lib/select/type';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getUseList } from '@services/common';
  import type { GetUsesParams, UseItem } from '@services/types/common';

  import { useCopy  } from '@hooks';

  import { getUserGroupList } from '../common/services';
  import type { AlarmGroupRecivers } from '../common/types';

  interface Props {
    type: 'add' | 'edit' | 'copy' | '',
    groupType: string
  }

  interface Exposes {
    getSelectedReceivers: () => AlarmGroupRecivers[];
  }

  interface RecipientItem {
    id: string,
    display_name: string,
    type: string,
    disabled?: boolean
  }

  const props = defineProps<Props>();
  const modelValue = defineModel<string[]>({
    required: true,
  });

  const { t } = useI18n();
  const copy = useCopy();
  const route = useRoute();

  const userList = ref([] as UseItem[]);
  const isFocous = ref(false);
  const isPlatform = computed(() => route.matched[0]?.name === 'Platform');

  const modelValueOrigin = _.cloneDeep(modelValue.value);

  let selectedReceivers = [] as RecipientItem[];
  const itemMap: Record<string, RecipientItem> = {};

  // 获取用户组数据
  const { data: userGroupList, mutate } = useRequest(getUserGroupList, {
    onSuccess(res) {
      const newRes = res.map((item) => {
        const mapItem = { ...item, disabled: modelValue.value.includes(item.id) };
        itemMap[item.id] = mapItem;
        return mapItem;
      });
      mutate(newRes);
    },
  });

  // 获取个人用户
  const fetchUseList = async (params: GetUsesParams = {}) => {
    await getUseList(params).then((res) => {
      // 过滤已经选中的用户
      userList.value = res.results.filter(item => !modelValue.value?.includes(item.username));
    });
  };
  // 初始化加载
  fetchUseList({ limit: 200, offset: 0 });

  const remoteFilter = async (value: string) => {
    await fetchUseList({ fuzzy_lookups: value });
  };

  const handleChange = (values: string[]) => {
    modelValue.value = values;
  };

  const findSeletedItem = (selected: ISelected[]) => {
    const mapItems = selected.reduce((prev, current) => {
      if (itemMap[current.value]) {
        prev.push(itemMap[current.value]);
      } else {
        prev.push({
          id: current.value,
          type: 'user',
          display_name: current.value,
        });
      }

      return prev;
    }, [] as RecipientItem[]);

    selectedReceivers = mapItems;

    return mapItems;
  };

  const isClosable = (id: string) => {
    if (isPlatform.value || props.type !== 'edit') return true;
    return !(props.groupType === 'PLATFORM' && modelValueOrigin.includes(id));
  };

  const handleSelectedClose = (id: string) => {
    const index = modelValue.value.findIndex(item => item === id);
    if (index > -1) {
      const values = _.cloneDeep(modelValue.value);

      values.splice(index, 1);
      modelValue.value = values;
    }
  };

  const handleFocus = () => {
    isFocous.value = true;
  };

  const handleBlur = () => {
    isFocous.value = false;
  };

  const handleCopy = () => {
    copy(modelValue.value.join(';'));
  };

  defineExpose<Exposes>({
    getSelectedReceivers() {
      return selectedReceivers.map(item => ({
        type: item.type,
        id: item.id,
      }));
    },
  });
</script>

<style lang="less" scoped>
  .receivers-selector-wrapper {
    position: relative;

    &:hover,
    &.is-focus {
      .receivers-selector-copy {
        display: block;
      }
    }
    .selected-tag-icon {
      font-size: 20px;
    }
  }

  .receivers-selector-copy {
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
