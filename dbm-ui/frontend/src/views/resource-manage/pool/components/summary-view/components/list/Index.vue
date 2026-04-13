<template>
  <DbCard
    class="summary-view-list"
    :title="t('资源分布统计')">
    <SearchBox @search="fetchListData" />
    <div class="opearte-row">
      <DimensionSelect
        v-model="dimension"
        @change="handleChangeDimension"
        @change-spec-enable="handleChangeSpecEnable" />
      <div
        class="text-button mr-8"
        @click="fetchListData">
        <DbIcon
          class="mr-4"
          type="refresh" />
        <span class="ml-2">{{ t('刷新数据') }}</span>
      </div>
      <Export
        :data="allTableData"
        :dimension="dimension" />
    </div>
    <BkLoading :loading="loading">
      <NoSpecIpList
        v-if="isNoSpecListShow"
        class="mb-12"
        :ip-list="noSpecIpList" />
      <div ref="tableWrapper">
        <PrimaryTable
          ref="tableRef"
          class="summary-view-table"
          :data="tableData"
          :max-height="tableMaxHeight">
          <TableColumn
            col-key="city"
            fixed="left"
            :min-width="150"
            :title="t('地域')">
            <template #default="{ row }">
              {{ row.cityValue || '--' }}
            </template>
          </TableColumn>
          <template v-if="isSpec">
            <TableColumn
              col-key="specTypeDisplay"
              :min-width="150"
              :title="t('规格类型')" />
            <TableColumn
              col-key="spec_name"
              :width="150" />
          </template>
          <template v-else>
            <TableColumn
              col-key="deviceDisplay"
              :min-width="150"
              :title="t('机型（硬盘）')" />
            <TableColumn
              col-key="cpu_mem_summary"
              :min-width="150"
              :title="t('CPU 内存')" />
          </template>
          <TableColumn
            col-key="sub_zone_detail"
            :title="t('园区分布（台）')"
            :width="400">
            <template #default="{ row }: { row: SummaryModel }">
              <template v-if="Object.keys(row.sub_zone_detail).length > 0">
                <span
                  v-for="(item, subzoneId, index) in row.sub_zone_detail"
                  :key="subzoneId">
                  <span v-if="item.name">{{ item.name }} : </span>
                  <span
                    class="cell-num"
                    @click="handleClick(row, Number(subzoneId))">
                    {{ item.count }}
                  </span>
                  <span>{{ index === Object.keys(row.sub_zone_detail).length - 1 ? '' : ' , ' }}</span>
                </span>
              </template>
              <span v-else>--</span>
            </template>
          </TableColumn>
          <TableColumn
            col-key="count"
            fixed="right"
            :min-width="100"
            :title="t('总数（台）')"
            :width="100">
            <template #default="{ row }">
              <span
                v-if="row.count > 0"
                class="cell-num"
                @click="handleClick(row)">
                {{ row.count }}
              </span>
              <span
                v-else
                class="cell-num--zero">
                0
              </span>
            </template>
          </TableColumn>
        </PrimaryTable>
        <div class="table-footer">
          <BkPagination
            v-bind="pagination"
            :layout="['total', 'limit', 'list']"
            @change="handleChangePage"
            @limit-change="handeChangeLimit" />
        </div>
      </div>
    </BkLoading>
  </DbCard>
</template>

<script setup lang="ts">
  import BkLoading from 'bkui-vue/lib/loading';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import SummaryModel from '@services/model/db-resource/summary';
  import { getSummaryList } from '@services/source/dbresourceResource';

  import { useDefaultPagination, useUrlSearch } from '@hooks';

  import { getOffset } from '@utils';

  import DimensionSelect from './components/DimensionSelect.vue';
  import Export from './components/Export.vue';
  import NoSpecIpList from './components/no-spec-ip-list/Index.vue';
  import SearchBox from './components/search-box/Index.vue';

  const { t } = useI18n();
  const router = useRouter();
  const { getSearchParams } = useUrlSearch();

  const rootRef = useTemplateRef('tableWrapper');
  const tableRef = useTemplateRef('tableRef');

  const dimension = ref('spec');
  const isSpecEnable = ref(true);
  const pagination = ref(useDefaultPagination());
  const isAnomalies = ref(false);
  const tableMaxHeight = ref<number | 'auto'>('auto');

  const allTableData = shallowRef<SummaryModel[]>([]);
  const noSpecIpList = shallowRef<string[]>([]);

  const isSpec = computed(() => dimension.value === 'spec');
  const isNoSpecListShow = computed(() => isSpec.value && noSpecIpList.value.length > 0);

  const tableData = computed(() => {
    const { current, limit } = pagination.value;
    const startIndex = (current - 1) * limit;
    const endIndex = startIndex + limit;
    return allTableData.value.slice(startIndex, endIndex);
  });

  const { loading, run: fetchData } = useRequest(getSummaryList, {
    manual: true,
    onError() {
      allTableData.value = [];
      noSpecIpList.value = [];
      pagination.value.count = 0;
      isAnomalies.value = true;
    },
    onSuccess(data) {
      allTableData.value = data.results.summary_data;
      noSpecIpList.value = data.results.no_spec_ip_list;
      pagination.value.count = data.count;
      isAnomalies.value = false;
    },
  });

  watch(isNoSpecListShow, () => {
    setTableMaxHeight();
  });

  const fetchListData = () => {
    fetchData({
      enable_spec: isSpecEnable.value,
      group_by: dimension.value,
      ...getSearchParams(),
    } as ServiceParameters<typeof getSummaryList>);
  };

  const handleChangeDimension = (value: string) => {
    dimension.value = value;
    handleChangePage(1);
    fetchListData();
  };

  const handleChangeSpecEnable = (value: boolean) => {
    isSpecEnable.value = value;
    handleChangePage(1);
    fetchListData();
  };

  const handleChangePage = (value: number) => {
    pagination.value.current = value;
    tableRef.value!.scrollToElement({ index: 0, top: 44 });
  };

  const handeChangeLimit = (value: number) => {
    pagination.value.limit = value;
    handleChangePage(1);
  };

  const handleClick = (row: SummaryModel, subzoneId?: number) => {
    const params = {
      city: row.cityValue,
      device_class: row.device_class,
      disk: row.disk_summary?.[0].size ? `${row.disk_summary?.[0].size}-` : '',
      disk_type: row.disk_summary?.[0].disk_type,
      for_biz: row.dedicated_biz,
      mount_point: row.disk_summary?.[0].mount_point,
      resource_type: getSearchParams().db_type,
      spec_id: row.spec_id,
      subzone_ids: subzoneId || '',
    };
    const routerInfo = router.resolve({
      name: 'resourcePool',
      params: {
        page: 'host-list',
      },
      query: {
        ...params,
      },
    });
    window.open(routerInfo.href, '_blank');
  };

  const setTableMaxHeight = () => {
    tableMaxHeight.value = window.innerHeight - getOffset(rootRef.value as HTMLElement).top - 62 - 60;
  };

  onMounted(() => {
    setTableMaxHeight();
  });
</script>

<style lang="less">
  .summary-view-list {
    .text-button {
      display: flex;
      font-size: 12px;
      color: #3a84ff;
      align-items: center;
      cursor: pointer;
    }

    .db-card__content {
      padding: 14px 22px;
    }

    .opearte-row {
      display: flex;
      align-items: center;
    }

    .summary-view-table {
      .cell-num {
        font-weight: bold;
        color: #3a84ff;
        cursor: pointer;
      }

      .cell-num--zero {
        font-weight: bold;
        color: #000;
      }
    }

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

        & > .is-last {
          margin-left: auto;
        }
      }
    }
  }
</style>
