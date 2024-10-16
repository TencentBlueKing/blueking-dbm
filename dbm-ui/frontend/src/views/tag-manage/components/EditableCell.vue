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
    <AutoFocusInput
      v-if="isEdit"
      v-model="editVal"
      :clearable="false"
      @blur="handleBlur(data)" />
    <span
      v-else
      class="tag-content">
      {{ data.tag }}
      <DbIcon
        class="operation-icon"
        style="font-size: 18px"
        type="edit"
        @click="handleEdit(data)" />
    </span>
  </div>
</template>

<script setup lang="ts">
  import { defineEmits, defineProps } from 'vue';

  import type ResourceTag from '@services/model/db-resource/ResourceTag';

  import AutoFocusInput from '@views/tag-manage/components/AutoFocusInput.vue';

  interface Props {
    data: ResourceTag;
    isEdit: boolean;
  }

  interface Emits {
    (event: 'blur', data: ResourceTag, val: string): void;
    (event: 'edit', data: ResourceTag): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const editVal = ref(props.data.tag);

  const handleBlur = (data: ResourceTag) => {
    emits('blur', data, editVal.value);
  };

  const handleEdit = (data: ResourceTag) => {
    emits('edit', data);
  };
</script>

<style lang="less" scoped>
  .tag-box {
    display: flex;
    align-items: center;

    &:hover .operation-icon {
      visibility: visible;
    }

    .tag-content {
      display: flex;
      align-items: center; // 确保文字和图标垂直居中对齐
    }
  }

  .operation-icon {
    color: #3a84ff;
    cursor: pointer;
    margin-left: 7.5px;
  }
</style>
