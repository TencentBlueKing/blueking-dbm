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
    ref="tagsRef"
    class="key-tags"
    :style="{padding: maxRow > 0 ? '5px 0' : 0}">
    <div
      v-for="(item, index) in displayList"
      :key="index"
      class="tag-item">
      <!-- {{ item }} -->
      <BkTag>{{ item }}</BkTag>
    </div>
    <BkPopover
      v-if="maxRow > 0 && overflowNum > 0"
      :disabled="overflowTagIndex === 0"
      placement="top"
      :popover-delay="0">
      <template #content>
        <div
          v-for="(item, index) in overflowTagList"
          :key="index"
          :style="{textAlign: 'center'}">
          {{ item }}
        </div>
      </template>
      <BkTag>
        +{{ overflowNum }}
      </BkTag>
    </BkPopover>
  </div>
</template>
<script setup lang="ts">
  import { useTagsOverflow } from '@hooks';
  interface Props {
    data?: string[];
    maxRow?: number
  }

  const props = withDefaults(defineProps<Props>(), {
    data: () => ([]),
    maxRow: 0, // 不限制行
  });

  const tagsRef = ref();
  const tagsList = computed(() => props.data);
  const displayList = ref(props.data);
  const { overflowTagIndex } = useTagsOverflow(tagsRef, tagsList);

  const overflowNum = computed(() => (overflowTagIndex.value === 0 ? 0 : (props.data.length - overflowTagIndex.value)));
  const overflowTagList = computed(() => [...props.data.slice(overflowTagIndex.value)]);
  let rawList = '';

  watch(() => props.data, (list) => {
    const listStr = JSON.stringify(list);
    if (rawList !== listStr) {
      displayList.value = list;
      rawList = listStr;
    }
  });


  watch(overflowTagIndex, (index) => {
    displayList.value = [...props.data.slice(0, index)];
  });


</script>
<style lang="less" scoped>
.key-tags {
  display: flex;
  width: 100%;
  max-height: 60px;
  // padding: 5px 0;
  flex-wrap: wrap;
  gap: 5px;

  .tag-item {
    display: inline-flex;
    height: 22px;
    // padding: 0 10px;
    // font-size: 12px;
    // line-height: 22px;
    // color: #63656E;
    // text-align: center;
    // background: #F0F1F5;
    // border-radius: 2px;
  }

  .overflow-num {
    .tag-item();

    // display: block;
    cursor: pointer;
  }
}
</style>
