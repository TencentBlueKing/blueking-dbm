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
    class="people-select"
    :clearable="false"
    filterable
    :model-value="tagsList"
    multiple
    multiple-mode="tag"
    :placeholder="$t('请输入/选择人员')"
    @change="handleChange">
    <template #trigger>
      <div
        class="sort-tag-input"
        @click="handleMouseEnter"
        @mouseenter="handleMouseEnter">
        <div
          v-for="(item, index) in tagsList"
          :key="item"
          class="tag-box"
          draggable="true"
          @dragend="handleDragEnd"
          @dragenter="(e) => handleDragEnterItem(e)"
          @dragstart="(e) => handleDragStartItemEnd(e)">
          <span
            v-show="targetIndex === index"
            class="split-line" />
          <DbIcon
            class="drag-icon"
            type="drag" />
          <span class="name">{{ item }}</span>
          <DbIcon
            class="close-icon"
            type="close"
            @click="(e: MouseEvent) => handleDeleteTag(e, index)" />
        </div>
        <input
          ref="inputRef"
          v-model="localValue"
          :placeholder="$t('请输入')"
          @input="handleInputChange"
          @keyup.enter="handleClickEnter">
      </div>
    </template>
    <BkOption
      v-for="(item, index) in contactList"
      :key="index"
      :label="item.label"
      :value="item.value" />
  </BkSelect>
</template>
<script setup lang="ts">
  import { useRequest } from 'vue-request';

  import { getUseList } from '@services/common';

  interface Props {
    list?: string[],
  }

  interface Exposes {
    getValue: () => string[];
  }

  interface Emits {
    (e: 'change', value: string[]): void
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const localValue = ref('');
  const inputRef = ref();
  const tagsList = ref<string[]>([]);
  const contactList = ref<SelectItem<string>[]>([]);
  const targetIndex = ref(-1);

  let searchTimer = 0;
  let sourceValue = '';
  let targetValue = '';

  watch(() => props.list, (list) => {
    if (list) {
      tagsList.value = list;
    }
  }, {
    immediate: true,
  });

  watch(tagsList, (list, oldList) => {
    emits('change', list);
    if (oldList && list.length > 0) {
      window.changeConfirm = true;
    }
  }, {
    immediate: true,
  });

  const { run: fetchUseList } = useRequest(getUseList, {
    manual: true,
    onSuccess: (res) => {
      contactList.value = res.results.reduce((results, item) => {
        if (!tagsList.value?.includes(item.username)) {
          const obj = {
            label: item.username,
            value: item.username,
          };
          results.push(obj);
        }
        return results;
      }, [] as {
        label: string,
        value: string,
      }[]);
    },
  });

  const handleChange = (values: string[]) => {
    localValue.value = '';
    tagsList.value = values;
    remoteFilter('');
  };

  // 初始化加载
  fetchUseList({ limit: -1, offset: 0 });

  const handleInputChange = (e: any) => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      remoteFilter(e.target.value);
    }, 200);
  };

  /**
   * 远程搜索人员
   */
  const remoteFilter = (value: string) => {
    fetchUseList({ fuzzy_lookups: value });
  };

  const handleMouseEnter = () => {
    inputRef.value.focus();
  };

  const handleClickEnter = () => {
    const inputValue = localValue.value;
    if (inputValue) {
      if (!tagsList.value.includes(inputValue) && contactList.value.findIndex(item => item.value === inputValue) > -1) {
        tagsList.value.push(inputValue);
      }
      localValue.value = '';
    }
  };

  const handleDeleteTag = (e: MouseEvent, index: number) => {
    e.preventDefault();
    e.stopPropagation();
    tagsList.value.splice(index, 1);
    remoteFilter('');
  };

  const handleDragStartItemEnd = (e: DragEvent) => {
    sourceValue = e.target.innerText;
  };

  const handleDragEnterItem = (e: DragEvent) => {
    if (e.relatedTarget !== null) {
      const targetText = e.relatedTarget.innerText;
      const index = tagsList.value.findIndex(item => item === targetText);
      targetIndex.value = index === -1 ? -1 : index + 1;
      targetValue = targetText;
    }
  };

  const handleDragEnd = () => {
    targetIndex.value = -1;
    if (targetValue && sourceValue && targetValue !== sourceValue) {
      let sourceIndex = -1;
      let targetIndex = -1;
      tagsList.value.forEach((item, index) => {
        if (item === sourceValue) {
          sourceIndex = index;
        }
        if (item === targetValue) {
          targetIndex = index;
        }
      });
      if (sourceIndex > -1 && targetIndex > -1) {
        tagsList.value.splice(sourceIndex, 1);
        nextTick(() => {
          if (sourceIndex > targetIndex) {
            tagsList.value.splice(targetIndex + 1, 0, sourceValue);
          } else {
            tagsList.value.splice(targetIndex, 0, sourceValue);
          }
        });
      }
    }
  };

  defineExpose<Exposes>({
    getValue() {
      return tagsList.value;
    },
  });
</script>
<style lang="less" scoped>
.sort-tag-input {
  display: flex;
  width: 100%;
  padding: 8px;
  border: 1px solid #C4C6CC;
  border-radius: 2px;
  flex-wrap: wrap;
  gap: 5px;

  .tag-box {
    display: flex;
    height: 22px;
    padding: 0 4px;
    font-size: 12px;
    background: #F0F1F5;
    border-radius: 2px;
    transition: 0.5s all;
    align-items: center;

    .split-line {
      display: inline-block;
      width: 2px;
      height: 22px;
      margin-left: -8px;
      background-color: #3a84ff;
    }

    .drag-icon {
      font-size: 18px;
      cursor: pointer;
    }

    .close-icon {
      font-size: 20px;
      cursor: pointer;
    }

    .name {
      margin: 0 4px;
    }
  }

  input {
    font-size: 12px;
    border: none;
    outline: none;
    flex:1;
  }

  &:hover {
    border: 1px solid #3a84ff;
  }
}

</style>
