<template>
  <BkFormItem
    class="target-form-item"
    :class="{
      'is-error': Boolean(errorMessage),
    }"
    :label="t('集群')"
    property="cluster_ids"
    required>
    <BkSelect
      v-model="selectedIds"
      class="target-select"
      :class="{
        'is-error': Boolean(errorMessage),
      }"
      :clearable="false"
      collapse-tags
      :filter-option="handleSearch"
      filterable
      :input-search="false"
      multiple
      multiple-mode="tag"
      :search-placeholder="t('输入域名（多域名以换行、空格、竖线、; 分隔，回车完成输入）')"
      @change="handleChange"
      @search-change="handleSearchChange">
      <BkOption
        v-for="item in clusterList"
        :key="item.id"
        :label="item.immute_domain"
        :value="item.id" />
    </BkSelect>
    <div
      v-if="errorMessage"
      class="error-icon">
      <DbIcon
        v-bk-tooltips="errorMessage"
        type="exclamation-fill" />
    </div>
    <p class="target-form-tip">{{ t('按集群子策略之间集群不可重叠') }}</p>
  </BkFormItem>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { queryAllTypeCluster } from '@services/source/dbbase';

  import { DBTypes, queryClusterTypes } from '@common/const';
  import { batchSplitRegex } from '@common/regex';

  import useValidtor from '@components/render-table/hooks/useValidtor';

  // 按集群子策略的集群元素
  export interface SelectedCluster {
    id: number;
    immute_domain: string;
  }

  interface Props {
    bizId: number;
    dbType: DBTypes;
  }

  type Emits = (e: 'change', value: SelectedCluster[]) => void;

  interface Exposes {
    getValue: () => Promise<SelectedCluster[]>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  // 对外暴露对象数组；内部用原始 id 数组驱动 BkSelect 多选
  const modelValue = defineModel<SelectedCluster[]>({
    default: [],
  });

  const { t } = useI18n();

  const rules = [
    {
      message: t('至少选择一个集群'),
      validator: (value: SelectedCluster[]) => value.length > 0,
    },
  ];

  const { message: errorMessage, validator } = useValidtor(rules);

  const { data: clusterList, run: fetchData } = useRequest(queryAllTypeCluster, {
    manual: true,
  });

  // 过滤项
  const filterOption = ref<ServiceReturnType<typeof queryAllTypeCluster>>([]);

  // 内部选中的原始 id 列表（驱动 BkSelect）
  const selectedIds = computed<number[]>({
    get: () => modelValue.value.map((item) => item.id),
    set: (ids: number[]) => {
      const map = new Map((clusterList.value || []).map((item) => [item.id, item]));
      modelValue.value = ids
        .map((id) => {
          const cluster = map.get(id);
          if (cluster) {
            return { id: cluster.id, immute_domain: cluster.immute_domain };
          }
          // 回填场景：clusterList 尚未加载但 modelValue 已有值，保留原对象
          const existing = modelValue.value.find((item) => item.id === id);
          return existing;
        })
        .filter((item): item is SelectedCluster => !!item);
    },
  });

  watch(
    () => props.bizId,
    () => {
      if (props.bizId) {
        fetchData({
          bk_biz_id: props.bizId,
          cluster_types: queryClusterTypes[props.dbType as keyof typeof queryClusterTypes].join(','),
          limit: -1,
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleChange = (value: number[]) => {
    // Enter 提交场景下 v-model 未更新，需手动赋值触发 setter
    selectedIds.value = value;
    // 等待 modelValue 更新完成后再校验，避免读到旧值导致误报
    nextTick(() => {
      validator(modelValue.value);
      emits('change', modelValue.value);
    });
  };

  const matchKeywords = (keywords: string[], target: string) =>
    keywords.some((kw) => target.toLowerCase().includes(kw.toLowerCase()));

  const handleSearch = (keyword: string, data: { label: string }) => {
    const keywords = keyword.split(batchSplitRegex).filter(Boolean);
    return matchKeywords(keywords, data.label);
  };

  const handleSearchChange = (keyword: string) => {
    const keywords = keyword.split(batchSplitRegex).filter(Boolean);
    filterOption.value = (clusterList.value || []).filter((item) => matchKeywords(keywords, item.immute_domain));
  };

  // Enter 触发提交
  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.isComposing) {
      // 跳过输入法复合事件
      return;
    }
    if (event.code === 'Enter') {
      handleChange(filterOption.value.map((item) => item.id));
    }
  };

  onMounted(() => {
    window.addEventListener('keydown', handleKeyDown);
  });

  onBeforeUnmount(() => {
    window.removeEventListener('keydown', handleKeyDown);
  });

  defineExpose<Exposes>({
    getValue() {
      return validator(modelValue.value).then(() => Promise.resolve(modelValue.value));
    },
  });
</script>

<style lang="less" scoped>
  .target-form-item {
    position: relative;

    :deep(.bk-form-control) {
      .target-select {
        flex: 1;
      }
    }

    .error-icon {
      position: absolute;
      right: 26px;
      top: 0;
      display: flex;
      height: 32px;
      font-size: 14px;
      color: #ea3636;
      align-items: center;
      z-index: 1;
    }
  }

  .is-error {
    :deep(.bk-select-tag) {
      background-color: #fff0f1 !important;
    }
  }

  .target-form-tip {
    margin-top: 6px;
    font-size: 12px;
    line-height: 16px;
    color: #979ba5;
  }
</style>
