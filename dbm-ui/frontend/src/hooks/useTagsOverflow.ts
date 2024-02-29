/*
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
 */
export const useTagsOverflow = (tagInputRef: Ref<HTMLDivElement>, tagList: Ref<string[]>, maxHeight = 55) => {
  const overflowTagIndex = ref(0);
  let rawList = '';

  watch(tagList, (list) => {
    if (rawList !== JSON.stringify(list)) {
      calcOverflow();
      rawList = JSON.stringify(list);
    }
  });

  // 计算出现换行的索引
  const calcOverflow = () => {
    overflowTagIndex.value = 0;
    setTimeout(() => {
      const tags: HTMLElement[] = Array.from(tagInputRef.value.querySelectorAll('.tag-item'));
      const tagIndexInSecondRow = tags.findIndex((currentTag, index) => {
        if (!index) {
          return false;
        }
        return currentTag.offsetTop > maxHeight;
      });
      overflowTagIndex.value = tagIndexInSecondRow > 0 ? tagIndexInSecondRow - 1 : 0;
    });
  };

  return { overflowTagIndex };
};
