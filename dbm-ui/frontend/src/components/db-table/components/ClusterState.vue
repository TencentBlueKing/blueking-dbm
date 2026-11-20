<!--
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
-->

<!-- 集群列表「运行概况」列筛选：左侧字段单选导航，右侧当前字段取值多选；值形态与搜索栏同一条件一致 -->
<template>
  <div
    class="db-table-filter-type-cluster-state"
    :style="{ 'min-width': contentMinWidth > 0 ? `${contentMinWidth}px` : '' }">
    <div
      ref="searchBox"
      class="t-table__filter-pop-search">
      <Input
        v-model="filterKey"
        borderless
        clearable
        :placeholder="t('请输入关键字')">
        <template #prefix-icon> <SearchIcon /></template>
      </Input>
    </div>
    <BkLoading :loading="loading">
      <div
        ref="layoutWrapper"
        class="layout-wrapper">
        <div
          v-if="isSearching"
          class="search-wrapper">
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
        </div>
        <template v-else>
          <div class="field-wrapper">
            <div
              v-for="field in filterFields"
              :key="field.key"
              class="value-item"
              :class="{ active: field.key === activeFieldKey }"
              @click="() => handleActiveField(field.key)">
              <span class="field-name">{{ field.name }}</span>
              <span
                v-if="selectedCountMap[field.key]"
                class="field-count">
                {{ selectedCountMap[field.key] }}
              </span>
            </div>
          </div>
          <div
            :key="activeFieldKey"
            class="choice-wrapper">
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
        </template>
      </div>
    </BkLoading>
    <div
      v-if="isSearching && searchResultList.length < 1 && !loading"
      class="t-table-filter-empty">
      <BkException
        :description="t('搜索为空')"
        scene="part"
        type="search-empty" />
    </div>
    <!-- 字段定义请求失败或没有可筛选字段 -->
    <div
      v-else-if="!isSearching && filterFields.length < 1 && !loading"
      class="t-table-filter-empty">
      <BkException
        :description="t('暂无数据')"
        scene="part"
        type="empty" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { SearchIcon } from 'tdesign-icons-vue-next';
  import { Input } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';

  import { decodeClusterStateFilterKey, encodeClusterStateFilterValue, useClusterStateSchema } from '@hooks';

  import type { ClusterTypes } from '@common/const';

  import Checkbox from '@components/tdesign-ui/checkbox';

  import { isLabelMatch } from './common/searchKeyword';

  export interface Props {
    clusterType: ClusterTypes;
    // 逗号分隔的编码值：state__{key}#{value}，与搜索栏 cluster_state 条件的值一致
    value?: string;
  }

  type Emits = (e: 'change', value: string) => void;

  // 表头筛选会透传 list 等本组件不使用的属性，不挂到根节点
  defineOptions({
    inheritAttrs: false,
  });

  const props = withDefaults(defineProps<Props>(), {
    value: '',
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const { filterFields, loading } = useClusterStateSchema(props.clusterType);

  const layoutWrapperRef = useTemplateRef('layoutWrapper');
  const searchBoxRef = useTemplateRef('searchBox');
  const contentMinWidth = ref(0);
  const filterKey = ref('');
  const activeFieldKey = ref('');
  // 面板内暂存的勾选，key 为编码后的取值
  const localValueMap = shallowRef<Record<string, boolean>>({});

  const isSearching = computed(() => Boolean(_.trim(filterKey.value)));
  const activeField = computed(() => filterFields.value.find((item) => item.key === activeFieldKey.value));

  // 左侧字段的已选数量
  const selectedCountMap = computed(() =>
    _.countBy(Object.keys(localValueMap.value), (value) => decodeClusterStateFilterKey(value)),
  );

  // 关键字同时匹配字段名与取值：命中字段名时列出该字段全部取值
  const searchResultList = computed(() =>
    filterFields.value.reduce<{ fieldName: string; label: string; value: string }[]>((result, field) => {
      const isFieldMatch = isLabelMatch(field.name, filterKey.value);
      field.choices.forEach((choice) => {
        if (isFieldMatch || isLabelMatch(choice.label, filterKey.value)) {
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

  // 切换字段时右侧宽度会变化，只增不减，避免弹层宽度来回跳动
  const calcPanelWidth = () => {
    nextTick(() => {
      if (!layoutWrapperRef.value) {
        return;
      }
      contentMinWidth.value = Math.max(layoutWrapperRef.value.getBoundingClientRect().width, contentMinWidth.value);
    });
  };

  // 外部值变化（打开、重置、搜索栏回写）时同步勾选
  watch(
    () => props.value,
    () => {
      localValueMap.value = _.filter((props.value || '').split(','), (item) => Boolean(_.trim(item))).reduce<
        Record<string, boolean>
      >((result, item) => Object.assign(result, { [item]: true }), {});
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
      calcPanelWidth();
    },
    {
      immediate: true,
    },
  );

  watch(filterKey, calcPanelWidth);

  const handleActiveField = (key: string) => {
    activeFieldKey.value = key;
    calcPanelWidth();
  };

  const handleToggle = (encodedValue: string) => {
    const latestValueMap = { ...localValueMap.value };
    if (latestValueMap[encodedValue]) {
      delete latestValueMap[encodedValue];
    } else {
      latestValueMap[encodedValue] = true;
    }
    localValueMap.value = latestValueMap;

    // 按字段、取值的配置顺序输出，保证回显顺序稳定
    const result: string[] = [];
    filterFields.value.forEach((field) => {
      field.choices.forEach((choice) => {
        const value = encodeClusterStateFilterValue(field.key, choice.value);
        if (latestValueMap[value]) {
          result.push(value);
        }
      });
    });
    emits('change', result.join(','));
  };

  onMounted(() => {
    calcPanelWidth();
    setTimeout(() => {
      searchBoxRef.value?.querySelector('input')?.focus();
    }, 100);
  });
</script>
<style lang="less">
  .db-table-filter-type-cluster-state {
    .layout-wrapper {
      display: flex;
      max-height: 280px;
      min-width: max-content;
      margin-top: 8px;
      margin-bottom: 8px;
      overflow: hidden;
    }

    .field-wrapper {
      min-width: 120px;
      overflow-y: auto;
      flex: 0 1 auto;
    }

    .choice-wrapper {
      min-width: 160px;
      overflow-y: auto;
      border-left: 1px solid #dcdee5;
      flex: 1;
    }

    .search-wrapper {
      overflow-y: auto;
      flex: 1;
    }

    .value-item {
      display: flex;
      height: 32px;
      padding: 0 10px 0 16px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      cursor: pointer;
      transition: all 0.1s;
      flex: 1 0 32px;
      align-items: center;
      justify-content: flex-start;

      &:hover {
        color: #3a84ff;
        background-color: #eaf3ff;
      }

      &.active {
        color: #3a84ff;
        background: #f4f6fa;
      }
    }

    .field-name {
      flex: 1;
    }

    .field-count {
      padding: 0 6px;
      margin-left: 8px;
      line-height: 16px;
      color: #3a84ff;
      background: #e1ecff;
      border-radius: 2px;
    }
  }
</style>
