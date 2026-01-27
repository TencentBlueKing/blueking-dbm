<template>
  <PrimaryTable
    class="sub-version-table-main"
    :data="tableData"
    :filter-value="tableFilterValue"
    :loading="tableLoading"
    :max-height="tableMaxHeight"
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
      <template #default="{ row, rowIndex }">
        <TextOverflowLayout
          v-if="!row.versionSeriesInfo"
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
        <CollapseCard
          v-else
          class="version-series-collapse-header"
          :model-value="!collapseIdSet.has(row.versionSeriesInfo.info.id)"
          @toggle="(value) => handleVersionSeriesToggle(value, rowIndex)">
          <template #title>
            <OperationHeader
              :data="row.versionSeriesInfo.info"
              :db-version-list-count="row.versionSeriesInfo.children.length"
              @add-new-version="() => emits('addNewVersion', row.versionSeriesInfo.info)"
              @delete-version-series="() => emits('refreshReleaseList')" />
          </template>
        </CollapseCard>
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
      col-key="packages"
      resizable
      :title="t('版本文件（适配系统）')"
      :width="380">
      <template #default="{ row }">
        <div
          v-for="(item, index) in row.packages"
          :key="index"
          class="os-limit-column">
          <div
            v-overflow-tips
            class="version-file-name">
            {{ item.name }}
          </div>
          <span class="ml-4 mr-4">(</span>
          <div>
            <span>{{ item.permit_os_type }}</span>
            <span class="ml-4 mr-4">:</span>
          </div>
          <div class="version-tags">
            <template v-if="item.permit_os.length > 0">
              <TagBlock
                :data="item.permit_os"
                size="small" />
            </template>
            <template v-else>
              <span class="all-text">{{ t('全部') }}</span>
            </template>
          </div>
        </div>
      </template>
    </TableColumn>
    <TableColumn
      col-key="distribution_snapshot"
      resizable
      :title="t('关联实例')"
      :width="100">
      <template #default="{ row }"> {{ row.packages[0]?.instances }} </template>
    </TableColumn>
    <TableColumn
      col-key="enable"
      :filter="tableFilter?.enable"
      resizable
      :width="100">
      <template #title>
        <span
          v-bk-tooltips="enableTips"
          class="table-enable-title">
          {{ t('启停') }}
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
          @success="handleDeleteVersionSuccess" />
      </template>
    </TableColumn>
  </PrimaryTable>
  <EmptyStatus
    v-if="!tableData.length"
    :is-anomalies="false"
    :is-searching="isSearching"
    @clear-search="handleClearSearch"
    @refresh="fetchTableData" />
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import _ from 'lodash';
  import { type TableSort } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import DbVersionModel from '@services/model/version-file/db-version';
  import { getDbVersionList, getVersionSeriesList } from '@services/source/version';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';
  import TagBlock from '@components/tag-block/Index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { random, utcDisplayTime } from '@utils';

  import CollapseCard from '@/components/collapse-card/Index.vue';

  import DeleteVersion from './components/DeleteVersion.vue';
  import EnableConfig from './components/EnableConfig.vue';
  import OperationHeader from './components/OperationHeader.vue';
  import RecommendConfig from './components/RecommendConfig.vue';
  import useTableFilter from './hooks/use-table-filter';

  interface Props {
    versionSeriesList?: VersionSeries;
  }

  interface Exposes {
    clearFilter: () => void;
    filterSearch: (value: { filter: Record<string, any> }) => void;
    refresh: () => void;
    setFilterValue: (value: Record<string, any>) => void;
  }

  interface Emits {
    (e: 'editDbVersion', version: DbVersion): void;
    (e: 'listChange', count: number): void;
    (e: 'addNewVersion', versionSeries: VersionSeries[number]): void;
    (e: 'editDbVersion', version: DbVersionModel): void;
    (e: 'refreshReleaseList'): void;
    (e: 'filterValueChange', value: Record<string, any>): void;
  }

  type VersionSeries = ServiceReturnType<typeof getVersionSeriesList>;
  type DbVersion = {
    createAtTimestamp: number;
    totalInstance?: number;
    versionSeriesInfo?: {
      children: DbVersion[];
      info: VersionSeries[number];
    };
  } & ServiceReturnType<typeof getDbVersionList>[number];

  const props = withDefaults(defineProps<Props>(), {
    versionSeriesList: () => [],
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const tableData = ref<DbVersion[]>([]);
  const tableMaxHeight = ref(0);
  const collapseIdSet = ref<Set<number>>(new Set());
  const tableFilterValue = ref<Record<string, any>>({});
  const isSearching = ref(true);

  const { loading: tableLoading, run: runGetDbVersionList } = useRequest(getDbVersionList, {
    manual: true,
    onSuccess(list) {
      const versionSeriesMap = props.versionSeriesList.reduce<
        Record<number, { children: DbVersion[] } & VersionSeries[number]>
      >((acc, item) => Object.assign(acc, { [item.id]: { children: [], info: item } }), {});
      list.forEach((item) => {
        const newItem = Object.assign(item, {
          createAtTimestamp: new Date(item.create_at).getTime(),
        });
        versionSeriesMap[item.version_series].children.push(newItem);
      });

      const handleList: DbVersion[] = [];
      Object.keys(versionSeriesMap).forEach((key) => {
        const childrenList = versionSeriesMap[Number(key)].children.sort((a, b) =>
          compareVersion(a.full_version, b.full_version),
        );
        if (childrenList.length > 0) {
          childrenList.forEach((item, index) => {
            if (index === 0) {
              handleList.push(
                Object.assign({ uuid: random() }, item, { versionSeriesInfo: versionSeriesMap[Number(key)] }),
              );
            }
            if (item.packages.length > 0) {
              const totalInstance = item.packages.reduce((sum, item) => sum + item.instances, 0);
              Object.assign(item, { totalInstance });
            }
            handleList.push(Object.assign({ uuid: random() }, item));
          });
        } else {
          handleList.push(
            Object.assign(
              { uuid: random() },
              { versionSeriesInfo: versionSeriesMap[Number(key)] },
            ) as unknown as DbVersion,
          );
        }
      });

      localTableData = _.cloneDeep(handleList);
      localBeforeSortTableData = localTableData;
      if (collapseIdSet.value.size > 0) {
        tableData.value = handleList.filter(
          (item) =>
            item.versionSeriesInfo || (!item.versionSeriesInfo && !collapseIdSet.value.has(item.version_series)),
        );
      } else {
        tableData.value = handleList;
      }
      emits('listChange', handleList.filter((item) => !item.versionSeriesInfo).length);
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
  let filterPaylod: { filter?: Record<string, any> } = { filter: {} };

  const fetchTableData = () => {
    runGetDbVersionList({
      version_series__in: props.versionSeriesList.map((item) => item.id).join(','),
    });
  };

  watch(
    () => props.versionSeriesList,
    () => {
      if (props.versionSeriesList.length > 0) {
        fetchTableData();
      }
    },
    {
      immediate: true,
    },
  );

  const handleDeleteVersionSuccess = () => {
    fetchTableData();
    emits('refreshReleaseList');
  };

  const handleClearSearch = () => {
    tableFilterValue.value = {};
    handleFilterChange({ filter: {} });
  };

  // 版本号比较函数：比较 full_version 格式如 1.2.0.0.0.0
  const compareVersion = (versionA: string, versionB: string): number => {
    const partsA = versionA.split('.');
    const partsB = versionB.split('.');
    const maxLength = Math.max(partsA.length, partsB.length);

    for (let i = 0; i < maxLength; i++) {
      let partA = partsA[i];
      let partB = partsB[i];
      if (partA.length < partB.length) {
        partA = partA.padEnd(partB.length, '0');
      }
      if (partA.length > partB.length) {
        partB = partB.padEnd(partA.length, '0');
      }
      if (Number(partB) > Number(partA)) return 1;
      if (Number(partB) < Number(partA)) return -1;
    }
    return 0;
  };

  const handleVersionSeriesToggle = (toggle: boolean, rowIndex: number) => {
    const childrenList = tableData.value[rowIndex].versionSeriesInfo?.children ?? [];
    const versionSeriesId = tableData.value[rowIndex].versionSeriesInfo!.info.id;
    childrenList.forEach((item) => Object.assign(item, { uuid: random() }));
    if (toggle) {
      // 展开
      collapseIdSet.value.delete(versionSeriesId);
      if (childrenList.length > 0) {
        tableData.value.splice(rowIndex + 1, 0, ...childrenList);
      }
      return;
    }
    // 收起
    collapseIdSet.value.add(versionSeriesId);
    tableData.value.splice(rowIndex + 1, childrenList.length);
  };

  const rowspanAndColspan = ({ colIndex, rowIndex }: { col: any; colIndex: number; rowIndex: number }) => {
    if (tableData.value[rowIndex].versionSeriesInfo && colIndex === 0) {
      return {
        colspan: 9,
      };
    }
    return {};
  };

  const handleEditDbVersion = (data: DbVersion) => {
    const activeRawRowData = tableData.value.find((item) => item.id === data.id)!;
    emits('editDbVersion', activeRawRowData);
  };

  // 前端实现排序
  const handleSortChange = (payload: TableSort) => {
    if (Array.isArray(payload)) {
      return;
    }

    const sortChildList = (childrenList: DbVersion[]) => {
      if (payload) {
        childrenList.sort((a: any, b: any) => {
          if (payload.descending) {
            return dayjs(a[payload.sortBy]).unix() - dayjs(b[payload.sortBy]).unix();
          }
          return dayjs(b[payload.sortBy]).unix() - dayjs(a[payload.sortBy]).unix();
        });
      } else {
        childrenList.sort((a: any, b: any) => compareVersion(a.full_version, b.full_version));
      }
    };

    const latestTableData = Object.keys(filterPaylod.filter!).length > 0 ? localBeforeSortTableData : tableData.value;
    const newTableData = _.cloneDeep(latestTableData);
    for (let i = 0; i < newTableData.length; i++) {
      const item = newTableData[i];
      if (item.versionSeriesInfo) {
        if (collapseIdSet.value.has(item.versionSeriesInfo.info.id)) {
          sortChildList(item.versionSeriesInfo.children);
          continue;
        }

        if (item.versionSeriesInfo.children.length > 1) {
          const childrenList = newTableData.slice(i + 1, i + item.versionSeriesInfo.children.length + 1);
          sortChildList(childrenList);
          newTableData.splice(i + 1, childrenList.length, ...childrenList);
          i += childrenList.length;
        }
      }
    }
    tableData.value = newTableData;
  };

  // 前端实现过滤筛选
  const handleFilterChange = (payload: typeof filterPaylod) => {
    const newPayload = _.cloneDeep(payload);
    if (newPayload.filter) {
      const checkFilterValue = (keyValue: string | string[], value: any) => {
        const itemValue = value.toString();
        if (Array.isArray(keyValue)) {
          if (keyValue.length === 0) {
            return true;
          }

          const keyValueStrList = keyValue.map((item) => item.toString());
          return keyValueStrList.includes(itemValue);
        }

        if (keyValue.includes(',')) {
          return keyValue.split(',').some((word: string) => word.includes(itemValue));
        }

        return keyValue ? itemValue.includes(keyValue) : true;
      };
      emits('filterValueChange', newPayload.filter);
      if (newPayload.filter.enable === '') {
        newPayload.filter.enable = [];
      }
      tableFilterValue.value = newPayload.filter;
      filterPaylod = newPayload;
      const newTableData = _.cloneDeep(localTableData);
      tableData.value = newTableData.filter((item) => {
        const filterKeys = Object.keys(newPayload.filter!);
        if (filterKeys.length > 0) {
          return filterKeys.every((key) => {
            const keyValue = newPayload.filter![key];
            const itemValue = item[key as keyof typeof item] as any;
            if (item.versionSeriesInfo) {
              // eslint-disable-next-line no-param-reassign
              item.versionSeriesInfo.children = item.versionSeriesInfo.children.filter((child) => {
                const childItemValue = child[key as keyof typeof child] as any;
                return checkFilterValue(keyValue, childItemValue);
              });
              return item.versionSeriesInfo.children.length > 0;
            }
            return !collapseIdSet.value.has(item.version_series) && checkFilterValue(keyValue, itemValue);
          });
        } else {
          return item.versionSeriesInfo || (!item.versionSeriesInfo && !collapseIdSet.value.has(item.version_series));
        }
      });
      localBeforeSortTableData = _.cloneDeep(tableData.value);
    }
  };

  const calcTableMaxHeight = () => {
    tableMaxHeight.value = window.innerHeight - 330;
  };

  onMounted(() => {
    calcTableMaxHeight();
    window.addEventListener('resize', calcTableMaxHeight);
  });

  onBeforeUnmount(() => {
    window.removeEventListener('resize', calcTableMaxHeight);
  });

  defineExpose<Exposes>({
    clearFilter: handleClearSearch,
    filterSearch: handleFilterChange,
    refresh: () => {
      fetchTableData();
    },
    setFilterValue: (value: Record<string, any>) => {
      tableFilterValue.value = value;
      handleFilterChange({ filter: value });
    },
  });
</script>
<style lang="less">
  .sub-version-table-main {
    .t-table__header {
      th {
        background-color: #f0f1f5 !important;

        &:hover {
          background-color: #dcdee5 !important;
        }
      }

      .t-table__th-full_version {
        padding-left: 32px !important;
      }
    }

    .t-table__first-full-row {
      display: none;
    }

    .t-table__td-first-col {
      padding: 0 !important;

      .version-series-collapse-header {
        padding: 7px 12px;
        background: #fafbfd;
        border-radius: 2px;

        .card-content {
          display: none;
        }

        .card-toggle-flag {
          font-size: 12px;
        }

        .title-main {
          font-size: 12px;
        }
      }
    }

    .version-display-column {
      padding-left: 32px;
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

      .version-file-name {
        max-width: 100px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }

      .version-tags {
        flex: 1;

        .bk-tag {
          max-width: 100px;
        }

        .dbm-tag-block,
        .all-text {
          &::after {
            margin-left: 4px;
            content: ')';
          }
        }
      }
    }

    .table-enable-title {
      text-decoration: underline dashed #4d4f56 1px;
      text-underline-offset: 4px;
    }
  }

  .sub-version-table-row {
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
