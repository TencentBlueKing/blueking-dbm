<template>
  <div class="system-serach-box">
    <div class="result-list">
      <BkLoading
        :loading="quickSearchLoading"
        style="height: 100%">
        <slot>
          <!-- <BkAlert
            v-if="showAlert"
            closable
            style="margin: 0 12px"
            theme="info">
            <template #title>
              <span>{{ t('每个分类最多显示 10 条记录，点击搜索可查看全部记录。') }}</span>
              <BkButton
                text
                theme="primary"
                @click="handleUnsubscribe">
                {{ t('不再提示') }}
              </BkButton>
            </template>
          </BkAlert> -->
          <BkException
            v-if="isSearchEmpty"
            :description="t('暂无搜索内容，换个关键词试一试')"
            scene="part"
            style="padding-top: 100px"
            type="search-empty">
            <BkButton
              text
              theme="primary"
              @click="handleClearSearch">
              {{ t('清空输入内容') }}
            </BkButton>
          </BkException>
          <ScrollFaker
            v-else
            style="height: calc(100% - 32px)">
            <div v-if="serachResult">
              <template
                v-for="resultType in serachResultKeyList"
                :key="resultType">
                <div
                  v-if="serachResult[resultType].length"
                  class="result-type-text">
                  {{ resultTypeTextMap[resultType] }}
                  （{{ serachResult.count[resultType] }}）
                </div>
                <RenderResult
                  :biz-id-name-map="bizIdNameMap"
                  :count="serachResult.count[resultType]"
                  :data="serachResult[resultType as keyof typeof serachResult]"
                  :key-word="modelValue"
                  :name="resultType"
                  @to-result="handleToResult" />
              </template>
            </div>
          </ScrollFaker>
        </slot>
      </BkLoading>
    </div>
    <div
      v-if="showOptions"
      class="filter-wrapper">
      <FilterOptions
        v-model="formData"
        :biz-list="bizList" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { storeToRefs } from 'pinia';
  import { computed, type UnwrapRef, watch } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { quickSearch } from '@services/source/quickSearch';

  import { useGlobalBizs, useSystemSearchStore } from '@stores';

  import { batchSplitRegex } from '@common/regex';

  import FilterOptions from './FilterOptions.vue';
  import useKeyboard from './hooks/use-keyboard';
  import RenderResult from './render-result/Index.vue';

  type ResultKeys = keyof Omit<ServiceReturnType<typeof quickSearch>, 'keyword' | 'short_code' | 'count'>;

  interface Props {
    // eslint-disable-next-line vue/require-default-prop
    getSearchOptions?: () => UnwrapRef<typeof formData>;
    showOptions?: boolean;
  }

  type Emits = (e: 'to-result', resourceType: string) => void;

  const props = withDefaults(defineProps<Props>(), {
    showOptions: true,
  });
  const emits = defineEmits<Emits>();
  const modelValue = defineModel<string>({
    default: '',
  });

  const { bizs: bizList } = useGlobalBizs();
  const systemSearchStore = useSystemSearchStore();
  const { formData } = storeToRefs(systemSearchStore);

  const { t } = useI18n();
  useKeyboard();

  // const QUICK_SEARCH_NO_LONGER_PROMPT = 'QUICK_SEARCH_NO_LONGER_PROMPT';

  const resultTypeTextMap: Record<ResultKeys, string> = {
    cluster: t('集群'),
    instance: t('实例'),
    machine: t('主机'),
    task: t('任务'),
    ticket: t('单据'),
  };

  const isSearchEmpty = ref(false);
  // const showUnsubscribeButton = ref(localStorage.getItem(QUICK_SEARCH_NO_LONGER_PROMPT) !== 'true');
  const firstSearch = ref(true);

  const bizIdNameMap = computed(() =>
    bizList.reduce((result, item) => Object.assign(result, { [item.bk_biz_id]: item.name }), {}),
  );

  const serachResultKeyList = computed(() => {
    if (!serachResult.value) {
      return [];
    }
    return Object.keys(serachResult.value).filter(
      (keyItem) => !['count', 'keyword', 'short_code'].includes(keyItem),
    ) as ResultKeys[];
  });

  // const showAlert = computed(() => showUnsubscribeButton.value && !firstSearch.value && !isDataEmpty.value);

  // const isDataEmpty = computed(() => {
  //   const dataItemList = Object.values(serachResult.value || {}).filter((item) => Array.isArray(item));
  //   return _.every(Object.values(dataItemList), (item) => item.length < 1);
  // });

  const {
    data: serachResult,
    loading: quickSearchLoading,
    run: runQuickSearch,
  } = useRequest(quickSearch, {
    manual: true,
    onSuccess(data) {
      const dataItemList = Object.values(data).filter((item) => Array.isArray(item));
      isSearchEmpty.value = _.every(dataItemList, (item) => item.length < 1);
      if (firstSearch.value) {
        firstSearch.value = false;
      }
    },
  });

  const handleSerachDebounce = _.debounce(runQuickSearch, 300);

  const handleSearch = () => {
    serachResult.value = {} as ServiceReturnType<typeof quickSearch>;
    if (!modelValue.value) {
      return;
    }

    if (props.getSearchOptions) {
      handleSerachDebounce({
        ...props.getSearchOptions(),
        keyword: modelValue.value.replace(batchSplitRegex, ' '),
      });
    } else {
      handleSerachDebounce({
        ...formData.value,
        keyword: modelValue.value.replace(batchSplitRegex, ' '),
      });
    }
  };

  watch(
    modelValue,
    (newKeyword, oldKeyword) => {
      console.log('from watch = ', modelValue.value);
      const newKeywordArr = newKeyword.split(batchSplitRegex);
      const oldKeywordArr = (oldKeyword || '').split(batchSplitRegex);
      if (_.isEqual(newKeywordArr, oldKeywordArr)) {
        return;
      }

      handleSearch();
    },
    {
      immediate: true,
    },
  );

  watch(
    formData,
    () => {
      handleSearch();
    },
    {
      deep: true,
      immediate: true,
    },
  );

  const handleClearSearch = () => {
    modelValue.value = '';
  };

  // const handleUnsubscribe = () => {
  //   localStorage.setItem(QUICK_SEARCH_NO_LONGER_PROMPT, 'true');
  //   showUnsubscribeButton.value = false;
  // };

  const handleToResult = (resourceType: string) => {
    emits('to-result', resourceType);
  };
</script>
<style lang="less">
  .system-serach-box {
    display: flex;
    font-size: 12px;
    background: #fff;

    .result-list {
      max-height: 540px;
      padding: 8px 0;
      overflow: hidden;
      color: #63656e;
      flex: 1;

      .result-type-text {
        padding-left: 12px;
        line-height: 32px;
        color: #979ba5;
      }

      .result-item {
        display: flex;
        height: 32px;
        padding: 0 12px;
        line-height: 32px;
        cursor: pointer;
        align-items: center;
        justify-content: space-between;

        &:hover,
        &.active {
          background: #f5f7fa;
        }

        .value-text {
          overflow: hidden;
          text-overflow: ellipsis;
          word-break: keep-all;
          white-space: nowrap;
          cursor: pointer;
          align-items: center;
          flex: 0 1 auto;

          .intro {
            padding-left: 4px;
            color: #c4c6cc;
          }

          &:hover {
            background: #f5f7fa;
          }

          .keyword-highlight {
            display: inline;
            width: fit-content;
            overflow: unset;
          }

          * {
            display: inline;
          }
        }

        .biz-text {
          flex: 0 0 auto;
          padding-left: 12px;
          margin-left: auto;
          color: #979ba5;
        }
      }
    }

    .filter-wrapper {
      padding: 10px 12px;
      border-left: 1px solid #dcdee5;
      flex: 0 0 240px;
    }
  }
</style>
