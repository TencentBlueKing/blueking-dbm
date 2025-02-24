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
  <span
    v-if="keywordMatch.length"
    class="highlight-text">
    <span
      v-for="(item, index) in keywordMatch"
      :key="index"
      :style="{ color: item.isHighlight ? highLightColor : 'inherit' }">
      {{ item.text || '' }}
    </span>
  </span>
  <span v-else>
    {{ props.text }}
  </span>
</template>
<script setup lang="ts">
  import { computed } from 'vue';

  import { batchSplitRegex } from '@common/regex';

  import { encodeRegexp } from '@utils';

  interface Props {
    highLightColor?: string;
    keyWord: string;
    text: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    highLightColor: '#3A84FF',
  });

  const keywordMatch = computed(() => {
    const keyWordList = props.keyWord.split(batchSplitRegex);
    // eslint-disable-next-line @typescript-eslint/prefer-for-of
    for (let i = 0; i < keyWordList.length; i++) {
      const keyWordItem = keyWordList[i];
      if (keyWordItem === props.text) {
        return [{ isHighlight: true, text: props.text }];
      }
      if (props.text.includes(':')) {
        const substringList = keyWordItem.split(':');
        const regex = new RegExp(`(${keyWordItem.split(':').join('|')})`);
        const matchResult = props.text.split(regex).map((part) => ({
          isHighlight: substringList.includes(part),
          text: part,
        }));
        if (matchResult.some((matchItem) => matchItem.isHighlight)) {
          return matchResult;
        }
      }
      const matchResult = props.text.match(new RegExp(`^(.*?)(${encodeRegexp(keyWordItem)})(.*)$`));
      if (matchResult) {
        return [
          { isHighlight: false, text: matchResult[1] },
          { isHighlight: true, text: matchResult[2] },
          { isHighlight: false, text: matchResult[3] },
        ];
      }
    }
    return [];
  });
</script>

<style lang="less" scoped>
  .highlight-text > span {
    display: inline !important;
  }
</style>
