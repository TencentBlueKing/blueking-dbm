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

<!-- 集群列表搜索栏「运行概况」面板：左侧字段单选导航，右侧当前字段取值多选；确定 / 重置由外层值面板提供 -->
<template>
  <div class="cluster-state-search-panel">
    <div class="bk-quick-search-value-panel-filter-box">
      <Input v-model="filterKey" />
    </div>
    <BkLoading :loading="loading">
      <div
        v-if="isSearching"
        class="bk-quick-search-value-wrapper cluster-state-search-panel-result">
        <div
          v-for="item in searchResultList"
          :key="item.value"
          class="value-item"
          @click="() => handleToggle(item.value)">
          <Checkbox
            :checked="Boolean(localValueMap[item.value])"
            style="pointer-events: none" />
          {{ item.fieldName }} / {{ item.label }}
        </div>
        <div
          v-if="searchResultList.length < 1 && !loading"
          class="cluster-state-search-panel-empty">
          <BkException
            :description="t('搜索为空')"
            scene="part"
            type="search-empty" />
        </div>
      </div>
      <div
        v-else-if="filterFields.length > 0"
        class="bk-quick-search-value-wrapper cluster-state-search-panel-columns">
        <div class="cluster-state-search-panel-fields">
          <div
            v-for="field in filterFields"
            :key="field.key"
            class="value-item"
            :class="{ active: field.key === activeFieldKey }"
            @click="() => handleActiveField(field.key)">
            <span class="cluster-state-search-panel-field-name">{{ field.name }}</span>
            <span
              v-if="selectedCountMap[field.key]"
              class="cluster-state-search-panel-field-count">
              {{ selectedCountMap[field.key] }}
            </span>
          </div>
        </div>
        <div class="cluster-state-search-panel-values">
          <div
            v-for="choice in activeField?.choices"
            :key="choice.value"
            class="value-item"
            @click="() => handleToggle(encodeClusterStateFilterValue(activeField!.key, choice.value))">
            <Checkbox
              :checked="Boolean(localValueMap[encodeClusterStateFilterValue(activeField!.key, choice.value)])"
              style="pointer-events: none" />
            {{ choice.label }}
          </div>
        </div>
      </div>
      <!-- 字段定义请求失败或没有可筛选字段 -->
      <div
        v-else-if="!loading"
        class="bk-quick-search-value-wrapper cluster-state-search-panel-empty">
        <BkException
          :description="t('暂无数据')"
          scene="part"
          type="empty" />
      </div>
    </BkLoading>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import type { ClusterTypes } from '@common/const';

  import Input from '@components/db-quick-search/bk-quick-search/components/create-area/components/value-menu/common/Input.vue';
  import { isSearchKeywordMatch } from '@components/db-quick-search/bk-quick-search/components/create-area/components/value-menu/common/searchKeyword';
  import Checkbox from '@components/tdesign-ui/checkbox';

  // 直接引用文件而非 @hooks 入口：入口会引到 useClusterQuickSearch，而它引用本组件，经入口会形成循环依赖
  import {
    decodeClusterStateFilterKey,
    encodeClusterStateFilterValue,
    useClusterStateSchema,
  } from '@/hooks/useClusterStateSchema';

  interface IValueItem {
    label: string;
    value: string | number;
  }

  interface Props {
    clusterType: ClusterTypes;
    // 已生效的条件（编辑已有标签时传入），新建条件时为空
    modelValue?: IValueItem[];
  }

  type Emits = (e: 'change', value: IValueItem[]) => void;

  // 外层值面板会透传 list、remoteSearch 等本组件不使用的属性，不挂到根节点
  defineOptions({
    inheritAttrs: false,
  });

  const props = withDefaults(defineProps<Props>(), {
    modelValue: undefined,
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const { filterFields, loading } = useClusterStateSchema(props.clusterType);

  const filterKey = ref('');
  const activeFieldKey = ref('');
  // 面板内暂存的勾选，key 为编码后的取值
  const localValueMap = shallowRef<Record<string, IValueItem>>({});

  const isSearching = computed(() => Boolean(_.trim(filterKey.value)));
  const activeField = computed(() => filterFields.value.find((item) => item.key === activeFieldKey.value));

  // 左侧字段的已选数量
  const selectedCountMap = computed(() =>
    _.countBy(Object.keys(localValueMap.value), (value) => decodeClusterStateFilterKey(value)),
  );

  // 关键字同时匹配字段名与取值：命中字段名时列出该字段全部取值
  const searchResultList = computed(() =>
    filterFields.value.reduce<{ fieldName: string; label: string; value: string }[]>((result, field) => {
      const isFieldMatch = isSearchKeywordMatch(field.name, filterKey.value);
      field.choices.forEach((choice) => {
        if (isFieldMatch || isSearchKeywordMatch(choice.label, filterKey.value)) {
          result.push({
            fieldName: field.name,
            label: choice.label,
            value: encodeClusterStateFilterValue(field.key, choice.value),
          });
        }
      });
      return result;
    }, []),
  );

  // 外层值面板的暂存值变化（打开、重置）时同步勾选
  watch(
    () => props.modelValue,
    () => {
      localValueMap.value = _.keyBy(props.modelValue || [], (item) => String(item.value));
    },
    {
      immediate: true,
    },
  );

  // 当前字段：优先第一个已有取值的字段，否则第一个字段
  watch(
    filterFields,
    () => {
      if (filterFields.value.some((item) => item.key === activeFieldKey.value)) {
        return;
      }
      const selectedField = filterFields.value.find((item) => selectedCountMap.value[item.key]);
      activeFieldKey.value = (selectedField || filterFields.value[0])?.key || '';
    },
    {
      immediate: true,
    },
  );

  const handleActiveField = (key: string) => {
    activeFieldKey.value = key;
  };

  const handleToggle = (encodedValue: string) => {
    const latestValueMap = { ...localValueMap.value };
    if (latestValueMap[encodedValue]) {
      delete latestValueMap[encodedValue];
    } else {
      latestValueMap[encodedValue] = {
        label: '',
        value: encodedValue,
      };
    }
    localValueMap.value = latestValueMap;

    // 按字段、取值的配置顺序输出，保证回显顺序稳定
    const result: IValueItem[] = [];
    filterFields.value.forEach((field) => {
      field.choices.forEach((choice) => {
        const value = encodeClusterStateFilterValue(field.key, choice.value);
        if (latestValueMap[value]) {
          result.push({
            label: choice.label,
            value,
          });
        }
      });
    });
    emits('change', result);
  };
</script>
<style lang="less">
  .cluster-state-search-panel {
    padding-bottom: 8px;

    .cluster-state-search-panel-result {
      flex-direction: column;
      overflow-y: auto;
    }

    .cluster-state-search-panel-columns {
      display: flex;
      min-width: max-content;
      overflow: unset;
    }

    .cluster-state-search-panel-fields {
      min-width: 120px;
      overflow-y: auto;
      flex: 0 1 auto;
    }

    .cluster-state-search-panel-values {
      min-width: 160px;
      overflow-y: auto;
      border-left: 1px solid #dcdee5;
      flex: 1;
    }

    .cluster-state-search-panel-field-name {
      flex: 1;
    }

    .cluster-state-search-panel-field-count {
      padding: 0 6px;
      margin-left: 8px;
      line-height: 16px;
      color: #3a84ff;
      background: #e1ecff;
      border-radius: 2px;
    }

    .cluster-state-search-panel-empty {
      padding: 8px 16px;
      color: #63656e;
      text-align: center;
    }
  }
</style>
