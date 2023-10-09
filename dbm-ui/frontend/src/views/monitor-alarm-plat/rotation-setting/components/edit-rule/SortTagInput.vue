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
    v-model="tagsList"
    class="people-select"
    :clearable="false"
    filterable
    :input-search="false"
    multiple
    multiple-mode="tag"
    :placeholder="$t('请输入/选择人员')">
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
          <DbIcon
            class="drag-icon"
            type="drag" />
          <span class="name">{{ item }}</span>
          <DbIcon
            class="close-icon"
            type="close"
            @click="() => handleDeleteTag(index)" />
        </div>
        <input
          ref="inputRef"
          v-model="localValue"
          :placeholder="$t('请输入')"
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

  let sourceValue = '';
  let targetValue = '';

  useRequest(getUseList, {
    onSuccess: (res) => {
      const list = res.results.map(item => ({ label: item.username, value: item.username }));
      contactList.value = list;
    },
  });

  watch(() => props.list, (list) => {
    if (list) {
      tagsList.value = list;
    }
  }, {
    immediate: true,
  });

  watch(tagsList, (list) => {
    emits('change', list);
    if (list.length > 0) {
      window.changeConfirm = true;
    }
  }, {
    immediate: true,
  });

  const handleMouseEnter = () => {
    inputRef.value.focus();
  };

  const handleClickEnter = () => {
    const inputValue = localValue.value;
    if (inputValue) {
      if (!tagsList.value.includes(inputValue)) {
        tagsList.value.push(inputValue);
      }
      localValue.value = '';
    }
  };

  const handleDeleteTag = (index: number) => {
    tagsList.value.splice(index, 1);
  };

  const handleDragStartItemEnd = (e: DragEvent) => {
    sourceValue = e.target.innerText;
  };

  const handleDragEnterItem = (e: DragEvent) => {
    if (e.relatedTarget !== null) {
      targetValue = e.relatedTarget.innerText;
    }
  };

  const handleDragEnd = () => {
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
  gap: 4px;

  .tag-box {
    display: flex;
    height: 22px;
    padding: 0 4px;
    font-size: 12px;
    background: #F0F1F5;
    border-radius: 2px;
    transition: 0.5s all;
    align-items: center;

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
