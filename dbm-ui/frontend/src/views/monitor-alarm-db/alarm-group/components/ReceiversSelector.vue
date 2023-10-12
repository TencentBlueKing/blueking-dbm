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
    :class="{'is-focus': isFocus}">
    <BkSelect
      class="receivers-selector"
      :clearable="false"
      filterable
      :input-search="false"
      :model-value="modelValue"
      multiple
      multiple-mode="tag"
      @blur="handleBlur"
      @change="handleChange"
      @focus="handleFocus">
      <BkOptionGroup
        collapsible
        :label="t('用户组')">
        <BkOption
          v-for="item of userGroupListData"
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
          :key="item.id"
          :disabled="item.disabled"
          :label="item.id"
          :value="item.id" />
      </BkOptionGroup>
      <template
        v-if="!userGroupLoading"
        #tag="{ selected }">
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

  import {
    getAlarmGroupList,
    getUserGroupList,
  } from '@services/monitorAlarm';

  import { useCopy } from '@hooks';

  interface Props {
    type: 'add' | 'edit' | 'copy' | '',
    isBuiltIn: boolean,
    bizId: number
  }

  interface Exposes {
    getSelectedReceivers: () => ServiceReturnType<typeof getAlarmGroupList>['results'][number]['receivers'];
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

  const isPlatform = route.matched[0]?.name === 'Platform';
  const modelValueOrigin = _.cloneDeep(modelValue.value);
  const itemMap: Record<string, RecipientItem> = {};
  let selectedReceivers: RecipientItem[] = [];

  const userList = ref<{
    id: string,
    disabled: boolean
  }[]>([]);
  const isFocus = ref(false);

  // 获取用户组数据
  const {
    data: userGroupListData,
    loading: userGroupLoading, // 避免数据回显时，获取用户组请求未完成造成显示错误
    mutate,
  } = useRequest(getUserGroupList, {
    defaultParams: [props.bizId],
    onSuccess(userGroupList) {
      const newUserGroupList = [];
      const userArr: {
        id: string,
        disabled: boolean
      }[] = [];

      for (let i = 0; i < userGroupList.length; i++) {
        const userGroupItem = userGroupList[i];
        const newUserGroupItem = {
          ...userGroupItem,
          disabled: modelValue.value.includes(userGroupItem.id) && props.isBuiltIn,
        };
        itemMap[userGroupItem.id] = newUserGroupItem;
        newUserGroupList.push(newUserGroupItem);

        const memberList = userGroupItem.members.map(memberItem => ({
          id: memberItem,
          disabled: modelValue.value.includes(memberItem) && props.isBuiltIn,
        }));
        userArr.push(...memberList);
      }

      userList.value = userArr;
      mutate(newUserGroupList);
    },
  });

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
    if (isPlatform || props.type !== 'edit') {
      return true;
    }
    return !(props.isBuiltIn && modelValueOrigin.includes(id));
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
    isFocus.value = true;
  };

  const handleBlur = () => {
    isFocus.value = false;
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
