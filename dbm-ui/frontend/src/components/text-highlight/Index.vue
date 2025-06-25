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
  <span>
    <template
      v-for="(item, index) in renderKeywordList"
      :key="index">
      <span
        v-if="item.hightlight"
        :style="{
          display: 'inline !important',
          color: highLightColor,
        }">
        {{ item.text }}
      </span>
      <template v-else>
        {{ item.text }}
      </template>
    </template>
    <span
      ref="root"
      style="display: none !important">
      <slot>
        {{ text }}
      </slot>
    </span>
  </span>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { computed } from 'vue';

  import { batchSplitRegex } from '@common/regex';

  import { encodeRegexp } from '@utils';

  interface Props {
    highLightColor?: string;
    keyword?: string;
    text?: string;
  }

  type Emits = (e: 'highlightHite', value: boolean) => void;

  interface Expose {
    getHighlightHited: () => boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    highLightColor: '#3A84FF',
    keyword: '',
    text: '',
  });

  const emits = defineEmits<Emits>();

  const rootRef = useTemplateRef('root');
  const localText = ref(props.text);

  const renderKeywordList = computed(() => {
    const keywordList = _.filter(props.keyword.split(batchSplitRegex), (item) => Boolean(_.trim(item)));
    if (!localText.value || keywordList.length < 1) {
      return [
        {
          hightlight: false,
          text: localText.value,
        },
      ];
    }
    const keywordReg = new RegExp(`^(${keywordList.map((item) => encodeRegexp(item)).join('|')})`, '');

    const splitStack: {
      hightlight: boolean;
      text: string;
    }[] = [];
    let localStr = localText.value;
    let originalStr = '';

    const collectionOriginalStr = () => {
      if (originalStr) {
        splitStack.push({
          hightlight: false,
          text: originalStr,
        });
        originalStr = '';
      }
    };
    while (localStr) {
      const keywordMatch = localStr.match(keywordReg);
      if (keywordMatch) {
        collectionOriginalStr();
        const [hightlightText] = keywordMatch;
        splitStack.push({
          hightlight: true,
          text: hightlightText,
        });
        localStr = localStr.slice(hightlightText.length);
        continue;
      }
      originalStr += localStr[0];
      localStr = localStr.slice(1);
    }
    collectionOriginalStr();
    return splitStack;
  });

  watch(
    renderKeywordList,
    () => {
      setTimeout(() => {
        emits(
          'highlightHite',
          _.some(renderKeywordList.value, (item) => item.hightlight),
        );
      });
    },
    {
      immediate: true,
    },
  );

  onMounted(() => {
    localText.value = rootRef.value!.innerText;
  });

  defineExpose<Expose>({
    getHighlightHited() {
      return _.some(renderKeywordList.value, (item) => item.hightlight);
    },
  });
</script>
