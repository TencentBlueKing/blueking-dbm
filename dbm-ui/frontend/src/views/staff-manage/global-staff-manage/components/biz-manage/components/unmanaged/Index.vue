<template>
  <div class="global-staff-unmanaged-biz">
    <BkAlert :title="t('以下业务已在 CMDB 登记但尚未纳入 DBM 管理范围。纳管后方可部署数据库集群。')" />
    <div class="mt-16">
      <DbQuickSearch
        v-model="searchValue"
        :data="quickSearchData"
        parse-url
        :placeholder="t('搜索业务 ID、业务名称、业务代号')"
        style="width: 500px"
        @change="handleQuickSearchChange" />
    </div>
    <div
      ref="tableWrapper"
      class="mt-16">
      <PrimaryTable
        class="list-table"
        :data="currentPageDataList"
        :max-height="tableMaxHeight"
        :outer-border="false"
        row-key="bk_biz_id">
        <TableColumn
          col-key="bk_biz_id"
          :title="t('业务 ID')" />
        <TableColumn
          col-key="name"
          :title="t('业务名称')" />
        <TableColumn
          col-key="english_name"
          :min-width="160"
          :title="t('业务代号')">
          <template #default="{ row }: { row: BizItem }">
            {{ row.english_name || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="row-operation"
          :title="t('操作')"
          width="120">
          <template #default="{ row }: { row: BizItem }">
            <AuthButton
              action-id="global_dba_admin_edit"
              text
              theme="primary"
              @click="() => handleManage(row)">
              {{ t('纳管') }}
            </AuthButton>
          </template>
        </TableColumn>
      </PrimaryTable>
      <div class="table-footer">
        <BkPagination
          v-bind="pagination"
          :layout="['total', 'limit', 'list']"
          @change="handlePageValueChange"
          @limit-change="handlePageLimitChange">
        </BkPagination>
      </div>
    </div>
    <ManagedSidesider
      v-if="currentData"
      v-model="isManageShow"
      :data="currentData"
      @success="handleSuccess" />
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { BizItem } from '@services/types';

  import { useUrlSearch } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { usePagination } from '@views/staff-manage/common/use-pagination.ts';

  import { getOffset } from '@utils';

  import ManagedSidesider from './components/ManagedSidesider.vue';
  import { useQuickSearch } from './useQuickSearch';

  const router = useRouter();
  const { t } = useI18n();
  const bizStore = useGlobalBizs();
  const { getSearchParams, replaceSearchParams } = useUrlSearch();
  const { handleFilterList, handleMergeSearchParams, quickSearchData, searchValue } = useQuickSearch();

  const rootRef = useTemplateRef('tableWrapper');

  const tableMaxHeight = ref<number | 'auto'>('auto');

  const bizList = ref<BizItem[]>([]);
  const tableFilterData = ref<BizItem[]>([]);
  const {
    currentPageDataList,
    onChange: handlePageValueChange,
    onLimitChange: handlePageLimitChange,
    pagination,
  } = usePagination<BizItem>(tableFilterData);

  const isManageShow = ref(false);
  const currentData = ref<BizItem>();

  const handleQuickSearchChange = () => {
    const filterList = handleFilterList(bizList.value || []);
    router.replace({
      query: replaceSearchParams(handleMergeSearchParams(getSearchParams()), false),
    });
    tableFilterData.value = filterList;
  };

  watch(
    () => bizStore.bizs,
    () => {
      bizList.value = bizStore.bizs.filter((item) => item.status === 'unmanaged');
      handleQuickSearchChange();
    },
    {
      immediate: true,
    },
  );

  const handleManage = (row: BizItem) => {
    currentData.value = row;
    isManageShow.value = true;
  };

  const handleSuccess = () => {
    bizStore.fetchBizs();
  };

  onMounted(() => {
    nextTick(() => {
      tableMaxHeight.value = tableMaxHeight.value =
        window.innerHeight - getOffset(rootRef.value as HTMLElement).top - 60 - 20 - 20;
    });
  });
</script>

<style lang="less">
  .global-staff-unmanaged-biz {
    padding: 0 24px;

    .table-footer {
      position: relative;
      z-index: 1;
      display: flex;
      height: 60px;
      padding: 0 16px;
      margin-top: -1px;
      background: #fff;
      border-top: 1px solid var(--td-component-border);
      align-items: center;

      .bk-pagination {
        width: 100%;

        // & > .is-last {
        //   margin-left: auto;
        // }
      }
    }
  }

  .global-staff-manage-cancel-manage {
    .biz-name {
      color: #313238;
    }

    .info-box {
      padding: 12px 16px;
      background: #f5f7fa;
    }
  }
</style>
