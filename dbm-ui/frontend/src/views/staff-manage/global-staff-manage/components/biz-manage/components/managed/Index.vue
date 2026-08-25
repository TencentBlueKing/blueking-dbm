<template>
  <div class="global-staff-managed-biz">
    <div>
      <DbQuickSearch
        v-model="searchValue"
        :data="quickSearchData"
        parse-url
        :placeholder="t('搜索业务 ID、业务名称、业务代号、标签')"
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
          :title="t('业务代号')">
          <template #default="{ row }: { row: BizItem }">
            {{ row.english_name || '--' }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="tags"
          :title="t('标签')">
          <template #default="{ row }: { row: BizItem }">
            <EditableCell
              :data="row"
              :edit-id="curEditId"
              :tag-list="tagData?.results"
              @change="handleTagChange"
              @edit="handleTagEdit" />
          </template>
        </TableColumn>
        <TableColumn
          col-key="managed_time"
          :title="t('纳管时间')">
          <template #default="{ row }: { row: BizItem }">
            {{ utcDisplayTime(row.managed_time) || '--' }}
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
              @click="() => handleCancelManage(row)">
              {{ t('取消纳管') }}
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
  </div>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import ResourceTagModel from '@services/model/db-resource/ResourceTag';
  import { cancelManageBiz, updateAppTag } from '@services/source/dbadmin';
  import { queryClusterInstanceCount } from '@services/source/dbbase';
  import { listTag } from '@services/source/tag';
  import type { BizItem } from '@services/types';

  import { useUrlSearch } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { DBAOperateTypes } from '@common/const';

  import { usePagination } from '@views/staff-manage/common/use-pagination.ts';

  import { getOffset, messageSuccess, messageWarn, utcDisplayTime } from '@utils';

  import EditableCell from './components/EditableCell.vue';
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

  const curEditId = ref(-1);

  const { data: tagData } = useRequest(listTag, {
    defaultParams: [
      {
        limit: -1,
        offset: 0,
        type: 'app',
      },
    ],
  });

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
      bizList.value = bizStore.bizs.filter((item) => item.status === 'managed');
      handleQuickSearchChange();
    },
    {
      immediate: true,
    },
  );

  const handleCancelManage = (row: BizItem) => {
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('取消纳管'),
      contentAlign: 'left',
      onConfirm: async () => {
        const countData = await queryClusterInstanceCount({
          bk_biz_id: row.bk_biz_id,
        });
        if (Object.values(countData).some((countItem) => countItem.cluster_count > 0)) {
          messageWarn('存在非 已下架/已销毁 状态的集群');
        } else {
          await cancelManageBiz({
            bk_biz_id: row.bk_biz_id,
          });
          messageSuccess(t('操作成功'));
          bizStore.fetchBizs();
        }
      },
      subTitle: (
        <div class='global-staff-manage-cancel-manage'>
          <div class='biz-name'>
            {t('业务名称')}：{row.name}
          </div>
          <div class='info-box mt-16'>
            <div>• {t('取消后，将清除该业务在全部组件下的 DBA 配置，业务将回到未纳管状态。')}</div>
            <div class='mt-8'>• {t('注意：此操作不可撤销。如需重新纳管，需再次配置全部组件的 DBA。')}</div>
          </div>
        </div>
      ),
      title: t('确认取消纳管该业务？'),
      type: 'warning',
    });
  };

  const handleTagEdit = (data: BizItem) => {
    curEditId.value = data.bk_biz_id;
  };

  const handleTagChange = (row: BizItem, tags: ResourceTagModel[]) => {
    const tagIds = tags.map((item) => item.id);
    const tagValues = tags.map((item) => item.value);

    if (
      !_.isEqual(
        tagIds,
        row.tags.map((item) => item.id),
      )
    ) {
      updateAppTag({
        bk_biz_id: row.bk_biz_id,
        operate: {
          after: tagValues.join(','),
          before: row.tags?.map((item) => item.value).join(',') || '',
          bk_biz_id: row.bk_biz_id,
          type: DBAOperateTypes.TAG_CHANGE,
        },
        tags: tagIds,
      })
        .then(() => {
          curEditId.value = -1;
          bizStore.fetchBizs();
          messageSuccess(t('操作成功'));
        })
        .finally(() => {
          curEditId.value = -1;
        });
    } else {
      curEditId.value = -1;
    }
  };

  onMounted(() => {
    nextTick(() => {
      tableMaxHeight.value = tableMaxHeight.value =
        window.innerHeight - getOffset(rootRef.value as HTMLElement).top - 60 - 20 - 20;
    });
  });
</script>

<style lang="less">
  .global-staff-managed-biz {
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
