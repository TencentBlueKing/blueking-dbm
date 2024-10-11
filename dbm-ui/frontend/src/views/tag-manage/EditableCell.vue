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
      v-if="data.is_show_edit"
      :clearable="false"
      :model-value="data.tag"
      @blur="handleBlur(data)" />
    <span v-else>{{ data.tag }}</span>
    <DbIcon
      v-if="!data.is_show_edit"
      class="operation-icon"
      style="font-size: 18px"
      type="edit"
      @click="handleEdit(data)" />
  </div>
</template>

<script setup lang="ts">
  import { defineEmits, defineProps } from 'vue';

  import AutoFocusInput from '@views/tag-manage/AutoFocusInput.vue';

  import type { ResourceTagListItem } from './Index.vue';

  defineProps<{
    data: ResourceTagListItem;
  }>();

  const emit = defineEmits<{
    (event: 'blur', data: ResourceTagListItem): void;
    (event: 'edit', data: ResourceTagListItem): void;
  }>();

  const handleBlur = (data: ResourceTagListItem) => {
    emit('blur', data);
  };

  const handleEdit = (data: ResourceTagListItem) => {
    emit('edit', data);
  };
</script>

<style scoped>
  .tag-box {
    display: flex;
    align-items: center;

    &:hover {
      .operation-icon {
        display: block;
      }
    }

    .operation-icon {
      display: none;
      color: #3a84ff;
      cursor: pointer;
      margin-left: 7.5px;
    }
  }

  .operation-icon {
    cursor: pointer;
  }
</style>
