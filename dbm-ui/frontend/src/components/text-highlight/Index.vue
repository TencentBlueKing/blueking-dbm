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

  import { FilterType } from '@common/const';
  import { batchSplitRegex } from '@common/regex';

  import { encodeRegexp } from '@utils';

  interface Props {
    filterType?: FilterType;
    highLightColor?: string;
    keyword?: string;
    text?: string;
  }

  type Emits = (e: 'highlightHite', value: boolean) => void;

  interface Expose {
    getHighlightHited: () => boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    filterType: FilterType.CONTAINS,
    highLightColor: '#3A84FF',
    keyword: '',
    text: '',
  });

  const emits = defineEmits<Emits>();

  let observer: MutationObserver | null = null;

  const rootRef = useTemplateRef('root');
  const localText = ref(props.text);

  /**
   * 解析 key:value 格式
   * @param str 待解析的字符串
   * @returns { key, value, hasColon }
   */
  const parseKeyValue = (str: string): { hasColon: boolean; key: string; value: string } => {
    const trimmed = _.trim(str);
    const colonIndex = trimmed.indexOf(':');

    if (colonIndex === -1) {
      return {
        hasColon: false,
        key: trimmed,
        value: '',
      };
    }

    return {
      hasColon: true,
      key: trimmed.slice(0, colonIndex).trim(),
      value: trimmed.slice(colonIndex + 1).trim(),
    };
  };

  /**
   * 精确匹配检查，支持所有 key:value 组合
   */
  const checkExactMatch = (
    text: string,
    keyword: string,
  ): {
    keywordHasColon: boolean;
    keywordKey?: string;
    keywordValue?: string;
    matched: boolean;
    textHasColon: boolean;
    textKey?: string;
    textValue?: string;
  } => {
    const trimmedText = _.trim(text);
    const trimmedKeyword = _.trim(keyword);

    // 情况1：完全相等（包括 :），直接匹配
    if (trimmedText === trimmedKeyword) {
      const textParsed = parseKeyValue(trimmedText);
      return {
        keywordHasColon: textParsed.hasColon,
        keywordKey: textParsed.key,
        keywordValue: textParsed.value,
        matched: true,
        textHasColon: textParsed.hasColon,
        textKey: textParsed.key,
        textValue: textParsed.value,
      };
    }

    const textParsed = parseKeyValue(trimmedText);
    const keywordParsed = parseKeyValue(trimmedKeyword);

    // 情况2：text 和 keyword 都不包含 :
    if (!textParsed.hasColon && !keywordParsed.hasColon) {
      return {
        keywordHasColon: false,
        matched: trimmedText === trimmedKeyword,
        textHasColon: false,
      };
    }

    // 情况3：text 包含 :，keyword 不包含 :
    if (textParsed.hasColon && !keywordParsed.hasColon) {
      // 检查 keyword 是否匹配 text 的 key 或 value
      const matched = textParsed.key === trimmedKeyword || textParsed.value === trimmedKeyword;
      return {
        keywordHasColon: false,
        keywordKey: trimmedKeyword,
        matched,
        textHasColon: true,
        textKey: textParsed.key,
        textValue: textParsed.value,
      };
    }

    // 情况4：text 不包含 :，keyword 包含 :
    if (!textParsed.hasColon && keywordParsed.hasColon) {
      // 检查 text 是否匹配 keyword 的 key 或 value
      const matched = trimmedText === keywordParsed.key || trimmedText === keywordParsed.value;
      return {
        keywordHasColon: true,
        keywordKey: keywordParsed.key,
        keywordValue: keywordParsed.value,
        matched,
        textHasColon: false,
        textKey: trimmedText,
      };
    }

    // 情况5：text 和 keyword 都包含 :
    if (textParsed.hasColon && keywordParsed.hasColon) {
      // 检查 key 和 value 是否匹配
      const keyMatched = textParsed.key === keywordParsed.key;
      const valueMatched = textParsed.value === keywordParsed.value;

      // 完全匹配：key 和 value 都匹配
      if (keyMatched && valueMatched) {
        return {
          keywordHasColon: true,
          keywordKey: keywordParsed.key,
          keywordValue: keywordParsed.value,
          matched: true,
          textHasColon: true,
          textKey: textParsed.key,
          textValue: textParsed.value,
        };
      }

      // 部分匹配：只有 key 匹配
      if (keyMatched) {
        return {
          keywordHasColon: true,
          keywordKey: keywordParsed.key,
          keywordValue: keywordParsed.value,
          matched: true,
          textHasColon: true,
          textKey: textParsed.key,
          textValue: textParsed.value,
        };
      }

      // 部分匹配：只有 value 匹配
      if (valueMatched) {
        return {
          keywordHasColon: true,
          keywordKey: keywordParsed.key,
          keywordValue: keywordParsed.value,
          matched: true,
          textHasColon: true,
          textKey: textParsed.key,
          textValue: textParsed.value,
        };
      }
    }

    return {
      keywordHasColon: keywordParsed.hasColon,
      matched: false,
      textHasColon: textParsed.hasColon,
    };
  };

  /**
   * 获取精确匹配的高亮结果
   */
  const getExactHighlightResult = (text: string, keywordList: string[]): { hightlight: boolean; text: string }[] => {
    if (!text) {
      return [{ hightlight: false, text: '' }];
    }

    const trimmedText = _.trim(text);

    // 遍历所有关键词，找到匹配的
    for (const keyword of keywordList) {
      const trimmedKeyword = _.trim(keyword);
      const result = checkExactMatch(trimmedText, trimmedKeyword);

      if (result.matched) {
        // 情况1：完全相等，整体高亮（包括 :）
        if (trimmedText === trimmedKeyword) {
          return [
            {
              hightlight: true,
              text: text,
            },
          ];
        }

        // 情况2：text 包含 :，keyword 包含 :，且完全匹配 key 和 value
        if (
          result.textHasColon &&
          result.keywordHasColon &&
          result.textKey === result.keywordKey &&
          result.textValue === result.keywordValue
        ) {
          // 如果文本完全等于 key:value，整体高亮
          if (trimmedText === `${result.textKey}:${result.textValue}`) {
            return [
              {
                hightlight: true,
                text: text,
              },
            ];
          }

          // 否则分别高亮 key 和 value，: 不高亮
          const key = result.textKey!;
          const value = result.textValue!;
          const keyIndex = trimmedText.indexOf(key);
          const valueStartIndex = keyIndex + key.length + 1;

          const highlightParts: { hightlight: boolean; text: string }[] = [];

          // key 之前的内容（不高亮）
          if (keyIndex > 0) {
            highlightParts.push({
              hightlight: false,
              text: trimmedText.slice(0, keyIndex),
            });
          }

          // key（高亮）
          highlightParts.push({
            hightlight: true,
            text: key,
          });

          // ":"（不高亮）
          highlightParts.push({
            hightlight: false,
            text: ':',
          });

          // value（高亮）
          highlightParts.push({
            hightlight: true,
            text: value,
          });

          // value 之后的内容（不高亮）
          const afterValue = trimmedText.slice(valueStartIndex + value.length);
          if (afterValue) {
            highlightParts.push({
              hightlight: false,
              text: afterValue,
            });
          }

          return highlightParts;
        }

        // 情况3：text 包含 :，keyword 不包含 :（匹配 key 或 value）
        if (result.textHasColon && !result.keywordHasColon) {
          const matchedKey = result.textKey;
          const matchedValue = result.textValue;

          // 判断匹配的是 key 还是 value
          const isKeyMatch = matchedKey === trimmedKeyword;
          const isValueMatch = matchedValue === trimmedKeyword;

          if (isKeyMatch || isValueMatch) {
            const key = matchedKey!;
            const value = matchedValue!;
            const keyIndex = trimmedText.indexOf(key);
            const valueStartIndex = keyIndex + key.length + 1;

            const highlightParts: { hightlight: boolean; text: string }[] = [];

            // key 之前的内容（不高亮）
            if (keyIndex > 0) {
              highlightParts.push({
                hightlight: false,
                text: trimmedText.slice(0, keyIndex),
              });
            }

            // 高亮匹配的部分
            if (isKeyMatch) {
              // 高亮 key，不高亮 : 和 value
              highlightParts.push({
                hightlight: true,
                text: key,
              });
              highlightParts.push({
                hightlight: false,
                text: `:${value}`,
              });
            } else {
              // 高亮 value，不高亮 key 和 :
              highlightParts.push({
                hightlight: false,
                text: `${key}:`,
              });
              highlightParts.push({
                hightlight: true,
                text: value,
              });
            }

            // value 之后的内容（不高亮）
            const afterValue = trimmedText.slice(valueStartIndex + value.length);
            if (afterValue) {
              highlightParts.push({
                hightlight: false,
                text: afterValue,
              });
            }

            return highlightParts;
          }
        }

        // 情况4：text 不包含 :，keyword 包含 :（匹配 key 或 value）
        if (!result.textHasColon && result.keywordHasColon) {
          const isKeyMatch = trimmedText === result.keywordKey;
          const isValueMatch = trimmedText === result.keywordValue;

          if (isKeyMatch || isValueMatch) {
            return [
              {
                hightlight: true,
                text: text,
              },
            ];
          }
        }

        // 默认：整体高亮
        return [
          {
            hightlight: true,
            text: text,
          },
        ];
      }
    }

    // 没有匹配
    return [
      {
        hightlight: false,
        text: text,
      },
    ];
  };

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

    // 精确搜索模式
    if (props.filterType === FilterType.EXACT) {
      return getExactHighlightResult(localText.value, keywordList);
    }

    // 模糊搜索模式（保持现有逻辑）
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

    observer = new MutationObserver(() => {
      if (rootRef.value) {
        localText.value = rootRef.value.innerText;
      }
    });
    observer.observe(rootRef.value!, {
      characterData: true, // 监听文本内容变化
      childList: true, // 监听子节点变化
      subtree: true, // 监听所有后代节点
    });
  });

  onBeforeUnmount(() => {
    if (observer) {
      observer.disconnect();
      observer = null;
    }
  });

  defineExpose<Expose>({
    getHighlightHited() {
      return _.some(renderKeywordList.value, (item) => item.hightlight);
    },
  });
</script>
