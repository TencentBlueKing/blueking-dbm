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
  <div class="tag-box">
    <BkInput
      v-if="editId === data.id"
      ref="inputRef"
      v-bind="$attrs"
      v-model="editVal"
      :clearable="false"
      @blur="handleBlur(data)" />
    <span
      v-else
      class="tag-content">
      {{ data.value }}
      <AuthButton
        :action-id="actionId"
        :resource="resource"
        text
        @click="handleEdit(data)">
        <DbIcon
          class="operation-icon"
          type="edit" />
      </AuthButton>
    </span>
  </div>
</template>

<script setup lang="ts">
  import { defineEmits, defineProps } from 'vue';

  import ResourceTagModel from '@services/model/db-resource/ResourceTag';

  interface Props {
    actionId: string;
    data: ResourceTagModel;
    editId: number;
    resource?: number;
  }

  interface Emits {
    (event: 'blur', data: ResourceTagModel, val: string): void;
    (event: 'edit', data: ResourceTagModel): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const inputRef = useTemplateRef('inputRef');

  const editVal = ref('');

  watch(
    () => [props.data, props.editId],
    () => {
      if (props.data.id === props.editId) {
        editVal.value = props.data.value;
        nextTick(() => {
          inputRef.value!.focus();
        });
      }
    },
  );

  const handleBlur = (data: ResourceTagModel) => {
    emits('blur', data, editVal.value);
  };

  const handleEdit = (data: ResourceTagModel) => {
    emits('edit', data);
  };
</script>

<style lang="less" scoped>
  .tag-box {
    &:hover {
      .operation-icon {
        display: inline-block;
      }
    }

    .operation-icon {
      display: none;
      font-size: 18px;
      cursor: pointer;
    }
  }
</style>
