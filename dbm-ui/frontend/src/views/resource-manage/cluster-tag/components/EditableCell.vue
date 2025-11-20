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
  <div class="edit-cell-main">
    <BkInput
      v-if="isEdit"
      ref="inputRef"
      v-bind="$attrs"
      v-model="editVal"
      :clearable="false"
      @blur="handleInputBlur" />
    <template v-else>
      <span>{{ editVal }}</span>
      <DbIcon
        v-if="showEdit"
        class="operation-icon"
        type="edit"
        @click="handleEdit" />
    </template>
  </div>
</template>
<script setup lang="ts">
  interface Props {
    data?: string;
    showEdit?: boolean;
  }

  type Emits = (e: 'success', value: string) => void;

  const props = withDefaults(defineProps<Props>(), {
    data: '',
    showEdit: true,
  });

  const emits = defineEmits<Emits>();

  const inputRef = ref();
  const editVal = ref('');
  const isEdit = ref(false);

  let rawValue = '';

  watch(
    () => props.data,
    () => {
      editVal.value = props.data;
      rawValue = props.data;
    },
    {
      immediate: true,
    },
  );

  watch(
    isEdit,
    () => {
      if (isEdit.value) {
        nextTick(() => {
          inputRef.value!.focus();
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleInputBlur = () => {
    isEdit.value = false;
    if (rawValue !== editVal.value) {
      emits('success', editVal.value);
    }
  };

  const handleEdit = () => {
    isEdit.value = true;
  };
</script>

<style lang="less" scoped>
  .edit-cell-main {
    display: flex;
    align-items: center;

    &:hover {
      .operation-icon {
        display: block;
      }
    }

    .operation-icon {
      display: none;
      margin-left: 8px;
      font-size: 12px;
      color: #979ba5;
      cursor: pointer;
    }
  }
</style>
