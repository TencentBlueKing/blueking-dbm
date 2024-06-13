<template>
  <div class="system-serach-box">
    <div class="result-list">
      <slot>
        <BkException
          v-if="isSearchEmpty"
          :description="t('暂无搜索内容，换个关键词试一试')"
          scene="part"
          style="padding-top: 145px"
          type="search-empty">
          <BkButton
            text
            theme="primary"
            @click="handleClearSearch">
            {{ t('清空输入内容') }}
          </BkButton>
        </BkException>
        <ScrollFaker v-else>
          <div v-if="serachResult">
            <template
              v-for="resultType in serachResultKeyList"
              :key="resultType">
              <div
                v-if="serachResult[resultType].length"
                class="result-type-text">
                {{ resultTypeTextMap[resultType] }}
              </div>
              <RenderResult
                :biz-id-name-map="bizIdNameMap"
                :data="serachResult[resultType as keyof typeof serachResult]"
                :key-word="modelValue"
                :name="resultType" />
            </template>
          </div>
        </ScrollFaker>
      </slot>
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
  import { computed, watch } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { quickSearch } from '@services/source/quickSearch';

  import { useGlobalBizs } from '@stores';

  import { batchSplitRegex } from '@common/regex';

  import FilterOptions from './FilterOptions.vue';
  import useKeyboard from './hooks/use-keyboard';
  import RenderResult from './render-result/Index.vue';

  interface Props {
    showOptions?: boolean;
  }

  interface Expose {
    getFilterOptions: () => typeof formData.value;
  }

  withDefaults(defineProps<Props>(), {
    showOptions: true,
  });
  const modelValue = defineModel<string>({
    default: '',
  });

  const { bizs: bizList } = useGlobalBizs();

  const { t } = useI18n();
  useKeyboard();

  const resultTypeTextMap: Record<string, string> = {
    cluster_domain: t('域名'),
    cluster_name: t('集群名'),
    instance: t('实例'),
    machine: t('主机'),
    task: t('任务ID'),
    ticket: t('单据'),
    resource_pool: t('资源池主机'),
  };

  const isSearchEmpty = ref(false);
  const formData = ref({
    bk_biz_ids: [] as number[],
    db_types: [] as string[],
    resource_types: [] as string[],
    filter_type: 'CONTAINS',
  });

  const bizIdNameMap = computed(() =>
    bizList.reduce((result, item) => Object.assign(result, { [item.bk_biz_id]: item.name }), {}),
  );

  const serachResultKeyList = computed(() => {
    if (!serachResult.value) {
      return [];
    }
    return Object.keys(serachResult.value) as (keyof typeof serachResult.value)[];
  });

  const { data: serachResult, run: handleSerach } = useRequest(quickSearch, {
    manual: true,
    onSuccess(data) {
      isSearchEmpty.value = _.every(Object.values(data), (item) => item.length < 1);
    },
  });

  const handleSerachDebounce = _.debounce(handleSerach, 200);

  watch(
    [modelValue, formData],
    ([newKeyword], [oldKeyword]) => {
      const newKeywordArr = newKeyword.split(batchSplitRegex);
      const oldKeywordArr = (oldKeyword || '').split(batchSplitRegex);
      if (_.isEqual(newKeywordArr, oldKeywordArr)) {
        return;
      }

      serachResult.value = {} as ServiceReturnType<typeof quickSearch>;

      if (!modelValue.value) {
        return;
      }

      handleSerachDebounce({
        ...formData.value,
        keyword: modelValue.value.replace(batchSplitRegex, ' '),
      });
    },
    {
      immediate: true,
      deep: true,
    },
  );

  const handleClearSearch = () => {
    modelValue.value = '';
  };

  defineExpose<Expose>({
    getFilterOptions() {
      return {
        ...formData.value,
        keyword: modelValue.value,
      };
    },
  });
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
        padding: 0 12px 0 24px;
        cursor: pointer;
        align-items: center;

        &:hover,
        &.active {
          background: #f5f7fa;
        }

        .value-text {
          display: flex;
          height: 32px;
          padding: 0 8px;
          cursor: pointer;
          align-items: center;

          &:hover {
            background: #f5f7fa;
          }

          .value-text {
            display: flex;
            overflow: hidden;
            text-overflow: ellipsis;
            word-break: keep-all;
            white-space: nowrap;
            flex: 0 1 auto;

            .intro {
              padding-left: 4px;
              color: #c4c6cc;
            }
          }

          .biz-text {
            flex: 0 0 auto;
            padding-left: 24px;
            margin-left: auto;
            color: #979ba5;
          }
        }
      }
    }
    .filter-wrapper {
      padding: 10px 12px;
      border-left: 1px solid #dcdee5;
      flex: 0 0 170px;
    }
  }
</style>
