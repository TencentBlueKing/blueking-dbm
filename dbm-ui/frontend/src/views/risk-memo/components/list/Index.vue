<template>
  <div class="risk-list-main">
    <div class="operate-main">
      <AuthButton
        v-if="!isPlatformPage && !isTodoPage"
        action-id="risk_memo_create"
        :biz-id="bizId"
        theme="primary"
        @click="handleAddRisk">
        {{ isSpecial ? t('新建要求') : t('新建风险') }}
      </AuthButton>
      <DbQuickSearch
        :key="renderSearchKey"
        v-model="searchValue"
        :data="searchSelectData"
        :placeholder="t('请选择条件搜索')"
        style="flex: 1"
        unique-select
        value-split-code="," />
    </div>
    <div
      v-bk-loading="{ loading: listLoading }"
      class="list-main">
      <ScrollFaker v-if="riskList.length > 0">
        <RiskItem
          v-for="item in riskList"
          :key="item.id"
          :data="item"
          :db-id-name-map="dbIdNameMap"
          :effect-biz-label-map="effectBizLabelMap"
          :is-active="item.id === currentRiskId"
          :is-special="isSpecial"
          :show-biz="isTodoPage || isPlatformPage"
          @click="() => handleChooseRiskMemoItem(item.id)" />
      </ScrollFaker>
      <template v-else>
        <BkException
          v-if="isSearching"
          class="mt-20"
          scene="part"
          type="search-empty">
          <span>{{ t('搜索为空') }}</span>
        </BkException>
        <BkException
          v-else
          class="mt-20"
          scene="part"
          type="empty">
          <span>{{ isSpecial ? t('暂无要求') : t('暂无风险') }}</span>
          <template v-if="!isPlatformPage && !isTodoPage">
            <span class="ml-4 mr-4">,</span>
            <BkButton
              size="small"
              text
              theme="primary"
              @click="handleAddRisk">
              {{ t('立即新建') }}
            </BkButton>
          </template>
        </BkException>
      </template>
    </div>
    <BkPagination
      v-model="pagination.current"
      class="pagination-main"
      :count="pagination.count"
      :limit="pagination.limit"
      :limit-list="[pagination.limit]"
      :show-total-count="false"
      small
      @change="handlePaginationChange" />
  </div>
  <CreateRisk
    v-model:is-show="isShowCreateRisk"
    :effect-biz-labels="effectBizLabels"
    :is-special="isSpecial"
    @success="handleCreateRiskSucess" />
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRoute, useRouter } from 'vue-router';

  import { getBizInpactList, getRiskMemoList } from '@services/source/riskMemo';

  import { DBTypeInfos } from '@common/const';

  import CreateRisk from './components/CreateRisk.vue';
  import RiskItem from './components/RiskItem.vue';
  import useSearch from './hooks/useSearch';

  export type RiskMemoItem = ServiceReturnType<typeof getRiskMemoList>['results'][number];

  interface Props {
    isSpecial?: boolean;
  }

  type Emits = (e: 'chooseItem', value: number) => void;

  interface Exposes {
    refresh: () => void;
  }

  const props = withDefaults(defineProps<Props>(), {
    effectBizLabels: () => [],
    isSpecial: false,
  });

  const emits = defineEmits<Emits>();

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();

  const currentRiskId = ref(0);
  const riskList = ref<RiskMemoItem[]>([]);
  const isShowCreateRisk = ref(false);
  const pagination = ref({
    count: 0,
    current: 1,
    limit: 15,
  });
  const renderSearchKey = ref(0);

  const isPlatformPage = computed(() => route.name === 'RiskMemoGlobal');
  const isTodoPage = computed(() => route.name === 'RiskMemoTodos');
  const effectBizLabelMap = computed(() =>
    effectBizLabels.value?.reduce<Record<string, string>>(
      (dataMap, item) =>
        Object.assign(dataMap, {
          [item.value]: item.label,
        }),
      {},
    ),
  );
  const excludeSearchIds = computed(() => {
    const excludes: string[] = [];
    if (!isPlatformPage.value && !isTodoPage.value) {
      excludes.push('bk_biz_id');
    }
    if (props.isSpecial) {
      excludes.push('biz_inpact__icontains');
    }
    if (isTodoPage.value) {
      excludes.push('status');
    }

    return excludes;
  });
  const isSearching = computed(() => Object.keys(searchValue.value).length > 0);

  const dbIdNameMap = Object.values(DBTypeInfos).reduce<Record<string, string>>(
    (dataMap, item) =>
      Object.assign(dataMap, {
        [item.id]: item.name,
      }),
    {},
  );
  const bizId = window.PROJECT_CONFIG.BIZ_ID;

  let searchParams: Record<string, string> = {};

  const { data: effectBizLabels } = useRequest(getBizInpactList);

  const { loading: listLoading, run: runGetRiskMemoList } = useRequest(getRiskMemoList, {
    manual: true,
    onSuccess: (data) => {
      riskList.value = data.results;
      pagination.value.count = data.count;
      if (data.results.length) {
        if (currentRiskId.value) {
          const index = data.results.findIndex((item) => item.id === currentRiskId.value);
          if (index !== -1) {
            currentRiskId.value = data.results[index].id;
          } else {
            currentRiskId.value = data.results[0].id;
          }
        } else {
          currentRiskId.value = data.results[0].id;
        }
        emits('chooseItem', currentRiskId.value);
        handleChooseRiskMemoItem(currentRiskId.value);
      } else {
        if (isSearching.value) {
          emits('chooseItem', -1);
        } else {
          emits('chooseItem', 0);
        }
      }
    },
  });

  const { searchSelectData, searchValue } = useSearch(props, effectBizLabels, excludeSearchIds);

  watch(
    searchValue,
    () => {
      searchParams = Object.entries(searchValue.value).reduce<Record<string, string>>(
        (dataMap, [key, value]) =>
          Object.assign(dataMap, {
            [key]: typeof value === 'string' ? value : value.join(','),
          }),
        {},
      );
      const query = {
        ...route.query,
        ...searchParams,
      };
      const searchKeys = [
        'bk_biz_id',
        'name__icontains',
        'db_type',
        'biz_inpact__icontains',
        'description__icontains',
        'creator',
        'id',
        'follow_user',
        'status',
      ];
      searchKeys.forEach((key) => {
        if (!searchParams[key]) {
          delete query[key];
        }
      });
      router.replace({ query });
      handleSearch(searchParams);
    },
    {
      deep: true,
    },
  );

  const handleGetRiskMemoList = () => {
    const params: { tab?: string } & ServiceParameters<typeof getRiskMemoList> = {
      ...searchParams,
      is_special: props.isSpecial,
      limit: pagination.value.limit,
      offset: (pagination.value.current - 1) * pagination.value.limit,
    };
    delete params.tab;
    if (isPlatformPage.value) {
      Object.assign(params, {
        platform: true,
      });
    } else if (isTodoPage.value) {
      Object.assign(params, {
        is_assist: route.query.is_assist === 'true',
        status: 'backlog',
      });
    } else {
      Object.assign(params, {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      });
    }
    runGetRiskMemoList(params, {
      permission: 'page',
    });
  };

  watch(
    () => props.isSpecial,
    () => {
      searchParams = {};
      currentRiskId.value = 0;
      searchValue.value = {
        status: 'backlog',
      };
      renderSearchKey.value++;
    },
  );

  watch(currentRiskId, () => {
    if (currentRiskId.value) {
      emits('chooseItem', currentRiskId.value);
    }
  });

  const handleSearch = (value: Record<string, string>) => {
    searchParams = value;
    handleGetRiskMemoList();
  };

  const handleChooseRiskMemoItem = (id: number) => {
    currentRiskId.value = id;
    const query = _.cloneDeep(route.query);
    query.id = `${id}`;
    router.replace({ query });
  };

  const handleAddRisk = () => {
    isShowCreateRisk.value = true;
  };

  const handleCreateRiskSucess = () => {
    pagination.value.current = 1;
    handleGetRiskMemoList();
  };

  const handlePaginationChange = (currentPage: number) => {
    pagination.value.current = currentPage;
    handleGetRiskMemoList();
  };

  onMounted(() => {
    if (Object.keys(route.query).length > 0) {
      searchValue.value = {
        ...route.query,
      };
    } else {
      searchValue.value = {
        status: 'backlog',
      };
    }
  });

  defineExpose<Exposes>({
    refresh: handleGetRiskMemoList,
  });
</script>
<style lang="less">
  .risk-list-main {
    display: flex;
    width: 100%;
    height: 100%;
    padding: 12px 16px 16px 24px;
    flex-direction: column;

    .operate-main {
      display: flex;
      gap: 8px;
      margin-bottom: 12px;
    }

    .list-main {
      flex: 1;
      overflow-y: auto;
      font-size: 12px;
      color: #4d4f56;
      background: #fff;
      box-shadow: 0 2px 4px 0 #1919290d;
    }

    .pagination-main {
      margin-top: 16px;
      justify-content: center;

      .bk-pagination-limit {
        display: none;
      }
    }
  }
</style>
