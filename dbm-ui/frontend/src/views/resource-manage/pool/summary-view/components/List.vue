<template>
  <DbCard
    class="summary-view-list"
    mode="collapse"
    :title="t('分布情况')">
    <SearchBox
      ref="searchRef"
      v-model:model-value="currentDbType"
      @change="handleChangeDbType"
      @search="fetchListData" />
    <div class="opearte-row">
      <DimensionSelect
        v-model:model-value="currentDimension"
        @change="handleChangeDimension" />
      <Export
        :data="tableData"
        :db-type="currentDbType"
        :dimension="currentDimension" />
    </div>
    <BkLoading :loading="loading">
      <BkTable
        class="summary-view-table"
        :data="tableData"
        :height="275"
        show-overflow-tooltip>
        <BkTableColumn
          :label="t('专用业务')"
          prop="for_biz_name"
          :width="100" />
        <BkTableColumn
          :label="t('地域')"
          prop="city" />
        <BkTableColumn
          v-if="isSpec"
          :label="t('规格类型')"
          prop="spec_machine_display">
          <template #default="{ row }">
            {{ row.spec_machine_display ? `${DBTypeInfos[currentDbType].name} - ${row.spec_machine_display}` : '--' }}
          </template>
        </BkTableColumn>
        <BkTableColumn
          v-if="isSpec"
          :label="t('规格')"
          prop="spec_name" />
        <BkTableColumn
          v-if="!isSpec"
          :label="t('机型（硬盘）')"
          prop="device_display" />
        <BkTableColumn
          v-if="!isSpec"
          :label="t('CPU 内存')"
          prop="cpu_mem_summary" />
        <BkTableColumn
          :label="t('园区分布（台）')"
          prop="sub_zone_detail">
          <template #default="{ row }">
            <span
              v-for="(value, key, index) in row.sub_zone_detail"
              :key="key">
              <span>{{ key }} : </span>
              <span class="cell-num">{{ value }}</span>
              <span>{{ index === Object.keys(row.sub_zone_detail).length - 1 ? ' ;' : ' , ' }}</span>
            </span>
          </template>
        </BkTableColumn>
        <BkTableColumn
          :label="t('总数（台）')"
          prop="count"
          :width="100">
          <template #default="{ row }">
            <span
              class="cell-num cursor-pointer"
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

  import { DBTypeInfos, DBTypes } from '@common/const';

  import DimensionSelect from './DimensionSelect.vue';
  import Export from './Export.vue';
  import SearchBox from './search-box/Index.vue';

  const { t } = useI18n();
  const router = useRouter();

  const searchRef = ref<InstanceType<typeof SearchBox>>();
  const currentDbType = ref(DBTypes.MYSQL);
  const currentDimension = ref('spec');
  const isSpec = computed(() => currentDimension.value === 'spec');

  const {
    run: fetchData,
    data: tableData,
    loading,
  } = useRequest(getSummaryList, {
    manual: true,
  });

  const fetchListData = async () => {
    const params = await searchRef.value?.getValue();
    fetchData({
      group_by: currentDimension.value,
      ...params,
    } as ServiceParameters<typeof getSummaryList>);
  };

  const handleChangeDbType = (dbType: DBTypes) => {
    currentDbType.value = dbType;
    fetchListData();
  };

  const handleChangeDimension = (value: string) => {
    currentDimension.value = value;
    fetchListData();
  };

  const handleClick = (row: SummaryModel) => {
    const params = {
      for_biz: row.dedicated_biz,
      resource_type: currentDbType.value,
      city: row.city,
      sub_zones: Object.keys(row.sub_zone_detail),
      spec_id: row.spec_id,
    };
    router.push({
      name: 'resourcePool',
      query: {
        tab: 'host-list',
        ...params,
        timestamp: new Date().getTime(), // 添加时间戳以确保每次跳转的 URL 都是唯一的
      },
    });
  };

  onMounted(() => {
    fetchListData();
  });
</script>

<style lang="less" scoped>
  .summary-view-list {
    :deep(.db-card__content) {
      padding: 14px 22px;
    }

    .opearte-row {
      display: flex;
      align-items: center;
    }

    .summary-view-table {
      :deep(.cell) {
        .cell-num {
          font-weight: bold;
          color: #3a84ff;
        }

        .cell-num--zero {
          color: #000;
        }

        .cursor-pointer {
          cursor: pointer;
        }
      }
    }
  }
</style>
