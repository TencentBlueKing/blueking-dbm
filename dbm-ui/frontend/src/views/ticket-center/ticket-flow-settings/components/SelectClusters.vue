<template>
  <div class="target-form-item">
    <BkSelect
      v-model="modelValue"
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
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { queryAllTypeCluster } from '@services/source/dbbase';

  import { DBTypes, queryClusterTypes } from '@common/const';
  import { batchSplitRegex } from '@common/regex';

  import useValidtor from '@components/render-table/hooks/useValidtor';

  interface Props {
    bizId: number;
    dbType: DBTypes;
  }

  type Emits = (e: 'change', value: number[]) => void;

  interface Exposes {
    getValue: () => Promise<number[]>;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<number[]>({
    default: [],
  });

  const { t } = useI18n();

  const rules = [
    {
      message: t('至少选择一个集群'),
      validator: (value: number[]) => value.length > 0,
    },
  ];

  const { message: errorMessage, validator } = useValidtor(rules);

  const { data: clusterList, run: fetchData } = useRequest(queryAllTypeCluster, {
    manual: true,
  });

  // 过滤项
  const filterOption = ref<ServiceReturnType<typeof queryAllTypeCluster>>([]);

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
    validator(value);
    emits('change', value);
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
    display: flex;
    align-items: center;
    gap: 8px;

    .target-select {
      flex: 1;
    }

    .error-icon {
      position: absolute;
      right: 26px;
      display: flex;
      height: 32px;
      font-size: 14px;
      color: #ea3636;
      align-items: center;
    }
  }

  .is-error {
    :deep(.bk-select-tag) {
      background-color: #fff0f1 !important;
    }
  }
</style>
