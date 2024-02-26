<template>
  <div class="system-serach-box">
    <div class="result-list">
      <slot>
        <BkException
          v-if="isSearchEmpty"
          :description="t('暂无搜索内容，换个关键词试一试')"
          scene="part"
          style="padding-top: 145px;"
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
              v-for="resultType in Object.keys(serachResult)"
              :key="resultType">
              <RenderResult
                :biz-id-name-map="bizIdNameMap"
                :data="(serachResult[resultType as keyof typeof serachResult])"
                :key-word="modelValue"
                :name="resultType" />
            </template>
          </div>
        </ScrollFaker>
      </slot>
    </div>
    <div class="filter-wrapper">
      <FilterOptions
        v-model="formData"
        :biz-list="bizList" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import {
    computed,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { quickSearch } from '@services/source/quickSearch';

  import {
    useGlobalBizs,
  } from '@stores';

  import FilterOptions from './FilterOptions.vue';
  import useKeyboard from './hooks/use-keyboard';
  import RenderResult from './render-result/Index.vue';

  interface Expose {
    getFilterOptions: () => typeof formData.value
  }

  const modelValue = defineModel<string>({
    default: '',
  });

  const {
    bizs: bizList,
  } = useGlobalBizs();

  const { t } = useI18n();
  useKeyboard();


  const isSearchEmpty = ref(false);
  const formData = ref({
    bk_biz_ids: [] as number[],
    db_types: [] as string[],
    resource_types: [] as string[],
    filter_type: 'CONTAINS',
  });

  const bizIdNameMap = computed(() => bizList
    .reduce((result, item) => Object.assign(result, { [item.bk_biz_id]: item.name }), {}));

  const {
    data: serachResult,
    run: handleSerach,
  } = useRequest(quickSearch, {
    manual: true,
    onSuccess(data) {
      isSearchEmpty.value = _.every(Object.values(data), item => item.length < 1);
    },
  });

  watch([modelValue, formData], () => {
    if (!modelValue.value) {
      serachResult.value = {} as ServiceReturnType<typeof quickSearch>;
      return;
    }
    handleSerach({
      ...formData.value,
      keyword: modelValue.value,
    });
  }, {
    immediate: true,
    deep: true,
  });

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
  background: #FFF;

  .result-list{
    max-height: 505px;
    padding: 8px 0;
    overflow: hidden;
    color: #63656E;
    flex: 1;

    .result-item{
      display: flex;
      height: 32px;
      padding: 0 8px;
      cursor: pointer;
      align-items: center;

      &:hover{
        background: #F5F7FA;
      }

      .value-text{
        display: flex;
        overflow: hidden;
        text-overflow: ellipsis;
        word-break: keep-all;
        white-space: nowrap;
        flex: 0 1 auto;

        .intro{
          padding-left: 4px;
          color: #C4C6CC;
        }
      }

      .biz-text{
        flex: 0 0 auto;
        padding-left: 24px;
        margin-left: auto;
        color: #979BA5;
      }
    }
  }

  .filter-wrapper{
    padding: 10px 12px;
    border-left: 1px solid #DCDEE5;
    flex: 0 0 170px;
  }
}
</style>
