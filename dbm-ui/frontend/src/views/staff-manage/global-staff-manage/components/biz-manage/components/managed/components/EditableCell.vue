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
    <BkSelect
      v-if="editId === data.bk_biz_id"
      ref="selectRef"
      v-bind="$attrs"
      v-model="editVal"
      multiple
      multiple-mode="tag"
      @toggle="handleBlur">
      <template
        #tag="{
          selected,
        }: {
          selected: {
            value: number;
            label: string;
          }[];
        }">
        <TagList
          closeable
          :list="selected"
          @close="handleTagClose" />
      </template>
      <BkOption
        v-for="item in tagList"
        :key="item.id"
        :label="item.value"
        :value="item.id">
        {{ item.value }}
      </BkOption>
    </BkSelect>
    <span
      v-else
      class="tag-content">
      <template v-if="data.tags?.length">
        <!-- <Bktag
          v-for="item in data.tags"
          :key="item.id">
          {{ item.value }}
        </Bktag> -->
        <TagList :list="data.tags.map((tagItem) => ({ label: tagItem.value, value: tagItem.id }))" />
      </template>
      <span v-else>--</span>
      <BkButton
        class="ml-4"
        text
        @click="handleEdit(data)">
        <DbIcon
          class="operation-icon"
          type="edit" />
      </BkButton>
    </span>
  </div>
</template>

<script setup lang="ts">
  import ResourceTagModel from '@services/model/db-resource/ResourceTag';
  import type { BizItem } from '@services/types';

  import TagList from '@views/staff-manage/common/TagList.vue';

  interface Props {
    data: BizItem;
    editId: number;
    tagList?: ResourceTagModel[];
  }

  interface Emits {
    (event: 'change', data: BizItem, tags: ResourceTagModel[]): void;
    (event: 'edit', data: BizItem): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    tagList: () => [],
  });

  const emits = defineEmits<Emits>();

  const selectRef = useTemplateRef('selectRef');

  const editVal = ref<number[]>([]);

  watch(
    () => [props.data, props.editId],
    () => {
      if (props.data.bk_biz_id === props.editId) {
        editVal.value = props.data.tags?.map((item) => item.id) || [];
      }
    },
  );

  const handleTagClose = (index: number) => {
    const tags = editVal.value;
    tags.splice(index, 1);
    editVal.value = tags;
  };

  const handleBlur = (isShow: boolean) => {
    if (!isShow) {
      nextTick(() => {
        const tagMap = Object.fromEntries(editVal.value.map((item) => [item, item]));
        emits(
          'change',
          props.data,
          props.tagList.filter((item) => tagMap[item.id] === item.id),
        );
      });
    }
  };

  const handleEdit = (data: BizItem) => {
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
