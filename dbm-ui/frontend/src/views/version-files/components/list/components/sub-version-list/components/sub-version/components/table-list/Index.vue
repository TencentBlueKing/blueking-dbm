<template>
  <PrimaryTable
    class="sub-version-table-main"
    :data="tableData"
    :loading="tableLoading"
    max-height="500"
    resizable
    row-class-name="sub-version-table-row"
    row-key="uuid"
    :rowspan-and-colspan="rowspanAndColspan"
    @change="handleFilterChange"
    @sort-change="handleSortChange">
    <TableColumn
      col-key="full_version"
      :filter="tableFilter?.full_version"
      resizable
      :title="t('版本号')"
      :width="180">
      <template #default="{ row }">
        <TextOverflowLayout
          class="version-display-column"
          :class="{ 'is-recommend': row.recommend }">
          <span class="display-text">{{ row.full_version }}</span>
          <template #append>
            <span class="tags-main">
              <BkTag
                size="small"
                :theme="stagTagMap[row.phase]?.theme">
                {{ stagTagMap[row.phase]?.label }}
              </BkTag>
              <BkTag
                v-if="row.recommend"
                size="small"
                theme="success">
                {{ t('推荐') }}
              </BkTag>
            </span>
            <RecommendConfig
              v-if="!row.recommend"
              :data="row"
              @success="fetchTableData" />
          </template>
        </TextOverflowLayout>
      </template>
    </TableColumn>
    <TableColumn
      col-key="name"
      ellipsis
      :filter="tableFilter?.name"
      resizable
      :title="t('版本名')"
      :width="150">
      <template #default="{ row }"> {{ row.name }} </template>
    </TableColumn>
    <TableColumn
      col-key="system"
      :filter="tableFilter?.system"
      resizable
      :title="t('操作系统限制')"
      :width="280">
      <template #default="{ row }">
        <div
          v-for="(item, index) in row.packages"
          :key="index"
          class="os-limit-column">
          <div>
            <span>{{ item.permit_os_type }}</span>
            <span class="ml-4 mr-4">:</span>
          </div>
          <div class="version-tags">
            <template v-if="item.permit_os.length > 0">
              <BkTag
                v-for="tag in item.permit_os"
                :key="tag"
                size="small">
                {{ tag }}
              </BkTag>
            </template>
            <template v-else>
              <span>{{ t('全部') }}</span>
            </template>
          </div>
        </div>
      </template>
    </TableColumn>
    <TableColumn
      col-key="version_file"
      ellipsis
      :filter="tableFilter?.version_file"
      resizable
      :title="t('版本文件')"
      :width="260">
      <template #default="{ row }"> {{ row.packages[0]?.name }} </template>
    </TableColumn>
    <TableColumn
      col-key="enable"
      :filter="tableFilter?.enable"
      resizable
      :title="t('是否启用')"
      :width="100">
      <template #title>
        <span
          v-bk-tooltips="enableTips"
          class="table-enable-title">
          {{ t('是否启用') }}
        </span>
      </template>
      <template #default="{ row }">
        <EnableConfig
          :data="row"
          @success="fetchTableData" />
      </template>
    </TableColumn>
    <TableColumn
      col-key="description"
      :filter="tableFilter?.description"
      resizable
      :title="t('描述')"
      :width="120">
      <template #default="{ row }"> {{ row.description }} </template>
    </TableColumn>
    <TableColumn
      col-key="distribution_snapshot"
      resizable
      :title="t('关联实例')"
      :width="100">
      <template #default="{ row }"> {{ row.packages[0]?.instances }} </template>
    </TableColumn>
    <TableColumn
      col-key="updater"
      :filter="tableFilter?.updator"
      resizable
      :title="t('更新人')"
      :width="120">
      <template #default="{ row }"> {{ row.updater }} </template>
    </TableColumn>
    <TableColumn
      col-key="update_at"
      resizable
      sorter
      :title="t('更新时间')"
      :width="200">
      <template #default="{ row }"> {{ utcDisplayTime(row.update_at) }} </template>
    </TableColumn>
    <TableColumn
      col-key="id"
      fixed="right"
      :title="t('操作')"
      :width="100">
      <template #default="{ row }">
        <BkButton
          size="small"
          text
          theme="primary"
          @click="() => handleEditDbVersion(row)">
          {{ t('编辑') }}
        </BkButton>
        <DeleteVersion
          :data="row"
          @success="fetchTableData" />
      </template>
    </TableColumn>
  </PrimaryTable>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { type TableSort } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getDbVersionList } from '@services/source/version';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { random, utcDisplayTime } from '@utils';

  import DeleteVersion from './components/DeleteVersion.vue';
  import EnableConfig from './components/EnableConfig.vue';
  import RecommendConfig from './components/RecommendConfig.vue';
  import useTableFilter from './use-table-filter';

  interface Props {
    seriesId?: number;
  }

  interface Exposes {
    filterSearch: (value: { filter: Record<string, any> }) => void;
    refresh: () => void;
  }

  interface Emits {
    (e: 'editDbVersion', version: DbVersion): void;
    (e: 'listChange', count: number): void;
  }

  type DbVersion = ServiceReturnType<typeof getDbVersionList>[number];

  const props = withDefaults(defineProps<Props>(), {
    seriesId: undefined,
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const tableData = ref<DbVersion[]>([]);

  const { loading: tableLoading, run: runGetDbVersionList } = useRequest(getDbVersionList, {
    manual: true,
    onSuccess(list) {
      localRowTableData = list;
      const handleList = list.reduce<DbVersion[]>((results, item) => {
        if (item.packages.length > 0) {
          const totalInstances = item.packages.reduce((sum, item) => sum + item.instances, 0);
          item.packages.forEach((packageItem) => {
            const newPackageItem = Object.assign(packageItem, { instances: totalInstances });
            results.push(
              Object.assign(
                {
                  uuid: random(),
                },
                item,
                {
                  packages: [newPackageItem],
                },
              ),
            );
          });
        } else {
          results.push(Object.assign({ uuid: random() }, item));
        }
        return results;
      }, []);
      localTableData = _.cloneDeep(handleList);
      updateVersionCountMap(handleList);
      tableData.value = handleList;
      emits('listChange', handleList.length);
    },
  });

  const tableFilter = useTableFilter(tableData);

  const stagTagMap: Record<string, { label: string; theme: 'danger' | 'warning' | 'info' | 'success' }> = {
    alpha: {
      label: 'Alpha',
      theme: 'danger',
    },
    beta: {
      label: 'Beta',
      theme: 'warning',
    },
    rc: {
      label: 'RC',
      theme: 'info',
    },
    release: {
      label: 'Release',
      theme: 'success',
    },
  };
  const enableTips = `${t('启用：所有场景均可使用，如：部署、升级')}\n${t('停用：存量集群替换不受影响，其它场景不可使用。注意：停用将自动清除推荐')}`;

  let localTableData: DbVersion[] = [];
  let localBeforeSortTableData: DbVersion[] = [];
  let localRowTableData: DbVersion[] = [];
  let startRowIndexSpanMap: Record<number, number> = {};
  let filterPaylod: { filter?: Record<string, any> } = { filter: {} };

  const fetchTableData = () => {
    runGetDbVersionList({
      version_series: props.seriesId!,
    });
  };

  watch(
    () => props.seriesId,
    () => {
      if (props.seriesId) {
        fetchTableData();
      }
    },
    {
      immediate: true,
    },
  );

  const updateVersionCountMap = (dataList: DbVersion[]) => {
    startRowIndexSpanMap = {};
    const versionCountMap: Record<
      string,
      {
        count: number;
        startRowIndex: number;
      }
    > = {};
    dataList.forEach((item, index) => {
      if (versionCountMap[item.full_version]) {
        versionCountMap[item.full_version].count++;
      } else {
        versionCountMap[item.full_version] = {
          count: 1,
          startRowIndex: index,
        };
      }
    });
    Object.values(versionCountMap).forEach((item) => {
      startRowIndexSpanMap[item.startRowIndex] = item.count;
    });
  };

  const rowspanAndColspan = ({ colIndex, rowIndex }: { col: any; colIndex: number; rowIndex: number }) => {
    if (colIndex !== 2 && colIndex !== 3) {
      return {
        rowspan: startRowIndexSpanMap[rowIndex],
      };
    }
    return {};
  };

  const handleEditDbVersion = (data: DbVersion) => {
    const activeRawRowData = localRowTableData.find((item) => item.id === data.id)!;
    emits('editDbVersion', activeRawRowData);
  };

  // 前端实现排序
  const handleSortChange = (payload: TableSort) => {
    if (Array.isArray(payload)) {
      return;
    }

    const latestTableData = Object.keys(filterPaylod.filter!).length > 0 ? localBeforeSortTableData : localTableData;
    if (payload) {
      const newTableData = _.cloneDeep(latestTableData);
      newTableData.sort((a: any, b: any) => {
        if (payload.descending) {
          return new Date(a[payload.sortBy]).getTime() - new Date(b[payload.sortBy]).getTime();
        }
        return new Date(b[payload.sortBy]).getTime() - new Date(a[payload.sortBy]).getTime();
      });
      tableData.value = newTableData;
    } else {
      tableData.value = _.cloneDeep(localBeforeSortTableData);
    }
    updateVersionCountMap(tableData.value);
  };

  // 前端实现过滤筛选
  const handleFilterChange = (payload: typeof filterPaylod) => {
    if (payload.filter) {
      filterPaylod = payload;
      const newTableData = _.cloneDeep(localTableData);
      tableData.value = newTableData.filter((item) => {
        return Object.keys(payload.filter!).every((key) => {
          const keyValue = payload.filter![key];
          const itemValue = item[key as keyof typeof item] as any;
          if (Array.isArray(keyValue)) {
            if (key === 'system') {
              return keyValue.some((system: string) =>
                item.packages.some((packageItem: any) => packageItem.permit_os_type === system),
              );
            }
            return keyValue.includes(itemValue);
          }
          if (key === 'system' && keyValue) {
            return keyValue
              .split(',')
              .some((system: string) =>
                item.packages.some((packageItem: any) => packageItem.permit_os_type === system),
              );
          }
          if (keyValue.includes(',')) {
            return keyValue.split(',').some((word: string) => word.includes(itemValue));
          }
          if (key === 'version_file' && keyValue) {
            return item.packages.some((packageItem: any) => packageItem.name.includes(keyValue));
          }

          return keyValue ? itemValue.includes(keyValue) : true;
        });
      });
      localBeforeSortTableData = _.cloneDeep(tableData.value);
      updateVersionCountMap(tableData.value);
    }
  };

  defineExpose<Exposes>({
    filterSearch: handleFilterChange,
    refresh: () => {
      fetchTableData();
    },
  });
</script>
<style lang="less">
  .sub-version-table-main {
    .t-table__header {
      th {
        background-color: #fafbfd !important;

        &:hover {
          background-color: #f0f1f5 !important;
        }
      }
    }

    .version-display-column {
      overflow: hidden;

      &.is-recommend {
        .tags-main {
          display: block !important;
        }
      }

      .display-text {
        margin-right: 5px;
      }

      .tags-main {
        display: flex;
        align-items: center;
      }

      .set-recommended {
        display: none;
      }
    }

    .os-limit-column {
      display: flex;
    }

    .table-enable-title {
      text-decoration: underline dashed #4d4f56 1px;
      text-underline-offset: 4px;
    }
  }

  .sub-version-table-row {
    height: 50px;

    &:hover {
      .version-display-column {
        .tags-main {
          display: none;
        }

        .set-recommended {
          display: block;
        }
      }
    }
  }
</style>
