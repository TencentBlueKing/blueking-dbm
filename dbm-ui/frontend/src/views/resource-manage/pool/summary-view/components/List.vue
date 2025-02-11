<template>
  <DbCard
    class="summary-view-list"
    :title="t('资源分布统计')">
    <SearchBox @search="fetchListData" />
    <div class="opearte-row">
      <DimensionSelect
        v-model="dimension"
        @change="handleChangeDimension" />
      <Export
        :data="allTableData"
        :dimension="dimension" />
    </div>
    <BkLoading
      ref="loadingRef"
      :loading="loading">
      <BkTable
        ref="tableRef"
        class="summary-view-table"
        :data="tableData"
        :pagination="pagination"
        @page-limit-change="handeChangeLimit"
        @page-value-change="handleChangePage">
        <BkTableColumn
          field="city"
          fixed="left"
          :label="t('地域')"
          :min-width="150">
          <template #default="{ row }">
            {{ row.city || '--' }}
          </template>
        </BkTableColumn>
        <template v-if="isSpec">
          <BkTableColumn
            field="specTypeDisplay"
            :label="t('规格类型')"
            :min-width="150" />
          <BkTableColumn
            field="spec_name"
            :label="t('规格')"
            :width="150" />
        </template>
        <template v-else>
          <BkTableColumn
            field="deviceDisplay"
            :label="t('机型（硬盘）')"
            :min-width="150" />
          <BkTableColumn
            field="cpu_mem_summary"
            :label="t('CPU 内存')"
            :min-width="150" />
        </template>
        <BkTableColumn
          field="sub_zone_detail"
          :label="t('园区分布（台）')"
          :width="400">
          <template #default="{ row }">
            <span
              v-for="(item, subzoneId, index) in row.sub_zone_detail"
              :key="subzoneId">
              <span v-if="item.name">{{ item.name }} : </span>
              <span
                class="cell-num"
                @click="handleClick(row, subzoneId)">
                {{ item.count }}
              </span>
              <span>{{ index === Object.keys(row.sub_zone_detail).length - 1 ? '' : ' , ' }}</span>
            </span>
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="count"
          fixed="right"
          :label="t('总数（台）')"
          :min-width="100"
          :width="100">
          <template #default="{ row }">
            <span
              class="cell-num"
              :class="{
                'cell-num--zero': row.count === 0,
              }"
              @click="handleClick(row)">
              {{ row.count }}
            </span>
          </template>
        </BkTableColumn>
      </BkTable>
    </BkLoading>
  </DbCard>
</template>

<script setup lang="ts">
  import BkLoading from 'bkui-vue/lib/loading';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type SummaryModel from '@services/model/db-resource/summary';
  import { getSummaryList } from '@services/source/dbresourceResource';

  import { useDefaultPagination, useUrlSearch } from '@hooks';

  import DimensionSelect from './DimensionSelect.vue';
  import Export from './Export.vue';
  import SearchBox from './search-box/Index.vue';

  const { t } = useI18n();
  const router = useRouter();
  const { getSearchParams } = useUrlSearch();

  const loadingRef = ref();
  const dimension = ref('spec');
  const tableRef = ref();
  const pagination = ref(useDefaultPagination());
  const isAnomalies = ref(false);
  const allTableData = shallowRef<SummaryModel[]>([]);

  const isSpec = computed(() => dimension.value === 'spec');
  const tableData = computed(() => {
    const { current, limit } = pagination.value;
    const startIndex = (current - 1) * limit;
    const endIndex = startIndex + limit;
    return allTableData.value.slice(startIndex, endIndex);
  });

  const { run: fetchData, loading } = useRequest(getSummaryList, {
    manual: true,
    onSuccess(data) {
      allTableData.value = data.results;
      pagination.value.count = data.count;
      isAnomalies.value = false;
    },
    onError() {
      allTableData.value = [];
      pagination.value.count = 0;
      isAnomalies.value = true;
    },
  });

  const fetchListData = () => {
    fetchData({
      group_by: dimension.value,
      ...getSearchParams(),
    } as ServiceParameters<typeof getSummaryList>);
  };

  const handleChangeDimension = (value: string) => {
    dimension.value = value;
    handleChangePage(1);
    fetchListData();
  };

  const handleChangePage = (value: number) => {
    pagination.value.current = value;
  };

  const handeChangeLimit = (value: number) => {
    pagination.value.limit = value;
    handleChangePage(1);
  };

  const handleClick = (row: SummaryModel, subzoneId?: number) => {
    const params = {
      for_biz: row.dedicated_biz,
      resource_type: getSearchParams().db_type,
      city: row.city,
      subzone_ids: subzoneId || '',
      spec_id: row.spec_id,
      device_class: row.device_class,
      mount_point: row.disk_summary?.[0].mount_point,
      disk: row.disk_summary?.[0].size ? `${row.disk_summary?.[0].size}-` : '',
      disk_type: row.disk_summary?.[0].disk_type,
    };
    router.push({
      name: 'resourcePool',
      params: {
        page: 'host-list',
      },
      query: {
        ...params,
      },
    });
  };
</script>

<style lang="less">
  .summary-view-list {
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
        color: #000;
      }
    }
  }
</style>
