<template>
  <PrimaryTable
    class="sub-version-table-main"
    :data="tableData"
    :filter-value="tableFilterValue"
    :loading="tableLoading"
    :max-height="tableMaxHeight"
    resizable
    :row-class-name="rowClassNameFn"
    row-key="uuid"
    :rowspan-and-colspan="rowspanAndColspan"
    @change="handleFilterChange"
    @sort-change="handleSortChange">
    <TableColumn
      class-name="version-name-table-cell"
      col-key="name"
      ellipsis
      :min-width="180"
      resizable
      :resize="{ minWidth: 180, maxWidth: 500 }"
      :title="t('版本名')">
      <template #default="{ row, rowIndex }">
        <TextOverflowLayout
          v-if="!row.versionSeriesInfo"
          class="version-display-column"
          :class="{ 'is-recommend': row.recommend }">
          <template #prepend>
            <RecommendConfig
              :data="row"
              :db-type="dbType"
              :permission="permission"
              @success="fetchTableData" />
          </template>
          <AuthTemplate
            action-id="package_manage"
            :permission="permission"
            :resource="dbType">
            <div
              class="version-display-name"
              @click="() => handleEditDbVersion(row)">
              {{ row.name }}
            </div>
          </AuthTemplate>
          <template #append>
            <span class="tags-main">
              <BkTag
                size="small"
                :theme="stagTagMap[row.phase]?.theme">
                {{ stagTagMap[row.phase]?.label }}
              </BkTag>
              <DbIcon
                v-if="row.description"
                v-bk-tooltips="{
                  content: row.description,
                  placement: 'right',
                  theme: 'light',
                }"
                class="column-describe-tip"
                type="attention" />
            </span>
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
              :db-type="dbType"
              :db-version-list-count="row.versionSeriesInfo.children.length"
              :existed-version-name-list="totalVersionNames"
              :permission="permission"
              @add-new-version="() => emits('addNewVersion', row.versionSeriesInfo.info)"
              @edit-version-series="handleEditVersionSeriesSuccess" />
          </template>
        </CollapseCard>
      </template>
    </TableColumn>
    <TableColumn
      col-key="full_version"
      :filter="tableFilter?.full_version"
      :min-width="180"
      resizable
      :title="t('版本号')">
      <template #default="{ row }"> {{ row.full_version }} </template>
    </TableColumn>
    <TableColumn
      class-name="version-packages-table-cell"
      col-key="packages"
      :min-width="380"
      resizable
      :resize="{ minWidth: 380, maxWidth: 600 }">
      <template #title>
        <span class="version-file-column-title">
          {{ t('版本文件') }}
          <DbIcon
            v-bk-tooltips="{
              content: t('一个版本可能含多个介质文件（不同 OS 适配），列表默认展示首文件，点击 +N 可展开全部'),
              // placement: 'bottom',
              theme: 'light',
            }"
            class="tip-icon"
            type="attention" />
        </span>
      </template>
      <template #default="{ row }">
        <VersionFiles :data="row" />
      </template>
    </TableColumn>
    <TableColumn
      col-key="distribution_snapshot"
      :min-width="100"
      resizable
      :title="t('关联实例')">
      <template #default="{ row }"> {{ row.packages[0]?.instances }} </template>
    </TableColumn>
    <TableColumn
      col-key="enable"
      :filter="tableFilter?.enable"
      :min-width="100"
      resizable>
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
          :db-type="dbType"
          :permission="permission"
          @success="fetchTableData" />
      </template>
    </TableColumn>
    <TableColumn
      col-key="updater"
      :filter="tableFilter?.updator"
      :min-width="120"
      resizable
      :title="t('更新人')">
      <template #default="{ row }"> {{ row.updater }} </template>
    </TableColumn>
    <TableColumn
      col-key="update_at"
      :min-width="200"
      resizable
      sorter
      :title="t('更新时间')">
      <template #default="{ row }"> {{ utcDisplayTime(row.update_at) }} </template>
    </TableColumn>
    <TableColumn
      col-key="id"
      fixed="right"
      :min-width="150"
      :title="t('操作')">
      <template #default="{ row }">
        <AuthButton
          action-id="package_manage"
          :permission="permission"
          :resource="dbType"
          size="small"
          text
          theme="primary"
          @click="() => handleEditDbVersion(row)">
          {{ t('编辑') }}
        </AuthButton>
        <DownloadPackage :data="row" />
        <DeleteVersion
          :data="row"
          :db-type="dbType"
          :permission="permission"
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
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { random, utcDisplayTime } from '@utils';

  import CollapseCard from '@/components/collapse-card/Index.vue';

  import DeleteVersion from './components/DeleteVersion.vue';
  import DownloadPackage from './components/DownloadPackage.vue';
  import EnableConfig from './components/EnableConfig.vue';
  import OperationHeader from './components/OperationHeader.vue';
  import RecommendConfig from './components/RecommendConfig.vue';
  import VersionFiles from './components/VersionFiles.vue';
  import useTableFilter from './hooks/use-table-filter';

  interface Props {
    dbType: string;
    permission: boolean;
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
    (e: 'refreshVersionList'): void;
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

  const totalVersionNames = computed(() => props.versionSeriesList.map((item) => item.name.toLocaleLowerCase()));

  const { loading: tableLoading, run: runGetDbVersionList } = useRequest(getDbVersionList, {
    manual: true,
    onSuccess(data) {
      const versionSeriesMap = props.versionSeriesList.reduce<
        Record<number, { children: DbVersion[] } & VersionSeries[number]>
      >((acc, item) => Object.assign(acc, { [item.id]: { children: [], info: item } }), {});
      data.forEach((item) => {
        const newItem = Object.assign(item, {
          createAtTimestamp: new Date(item.create_at).getTime(),
        });
        versionSeriesMap[item.version_series].children.push(newItem);
      });
      const nameIdList = props.versionSeriesList
        .map((item) => ({ id: item.id, name: item.name }))
        .sort((a, b) => compareName(a.name, b.name));
      const handleList: DbVersion[] = [];
      nameIdList.forEach((nameIdObj) => {
        const childrenList = versionSeriesMap[nameIdObj.id].children.sort((a, b) =>
          compareVersion(a.full_version, b.full_version),
        );
        if (childrenList.length > 0) {
          childrenList.forEach((item, index) => {
            if (index === 0) {
              handleList.push(
                Object.assign({ uuid: random() }, item, { versionSeriesInfo: versionSeriesMap[nameIdObj.id] }),
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
              { versionSeriesInfo: versionSeriesMap[nameIdObj.id] },
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
      // 针对过滤场景下操作后重新获取数据，需要等待数据更新后重新触发过滤
      setTimeout(() => {
        if (Object.keys(tableFilterValue.value).length > 0) {
          handleFilterChange({ filter: tableFilterValue.value });
        }
      });
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

  const parseVersionSegments = (versionStr: string): number[] =>
    versionStr.split('.').map((part) => Number.parseInt(part, 10));

  /** 版本段数值比较，从高到低（段值大者排前） */
  const compareSegmentsDesc = (sa: number[], sb: number[]): number => {
    const len = Math.max(sa.length, sb.length);
    for (let i = 0; i < len; i += 1) {
      const na = sa[i] ?? 0;
      const nb = sb[i] ?? 0;
      if (Number.isNaN(na) || Number.isNaN(nb)) {
        return 0;
      }
      if (na !== nb) {
        return nb - na;
      }
    }
    return 0;
  };

  /** 按版本名排序：同系列内版本号从高到低（如 MySQL-10 → MySQL-8.0 → MySQL-5.7）；支持无中划线（如 MySQL8.0、mysql10） */
  const compareName = (a: string, b: string): number => {
    const parse = (raw: string) => {
      const trimmed = raw.trim();
      const toParsed = (versionStr: string, versionStart: number) => ({
        prefix: trimmed
          .slice(0, versionStart)
          .replace(/[-_.\s]+$/u, '')
          .toLowerCase(),
        raw: trimmed,
        segments: parseVersionSegments(versionStr),
        versionStr,
      });

      // 优先：最后一个 - / _ / 空格 后的纯数字版本（如 dbm-mysql-proxy-0.82.10）
      const lastSepMatch = trimmed.match(/(?:^|[-_\s])(\d+(?:\.\d+)*)\s*$/u);
      if (lastSepMatch?.[1]) {
        const versionStr = lastSepMatch[1];
        return toParsed(versionStr, trimmed.length - versionStr.length);
      }

      // 兼容无分隔符：MySQL8.0、mysql10
      const suffixMatch = trimmed.match(/(\d+(?:\.\d+)*)\s*$/u);
      if (suffixMatch?.[1] && suffixMatch.index !== undefined) {
        return toParsed(suffixMatch[1], suffixMatch.index);
      }

      return {
        prefix: trimmed.toLowerCase(),
        raw: trimmed,
        segments: [] as number[],
        versionStr: '',
      };
    };

    const pa = parse(a);
    const pb = parse(b);
    const prefixCmp = pa.prefix.localeCompare(pb.prefix);
    if (prefixCmp !== 0) {
      return prefixCmp;
    }
    const segCmp = compareSegmentsDesc(pa.segments, pb.segments);
    if (segCmp !== 0) {
      return segCmp;
    }
    if (pa.versionStr && pb.versionStr) {
      const versionCmp = pa.versionStr.localeCompare(pb.versionStr, undefined, {
        numeric: true,
        sensitivity: 'base',
      });
      if (versionCmp !== 0) {
        return versionCmp;
      }
    }
    return pa.raw.localeCompare(pb.raw, undefined, { sensitivity: 'base' });
  };

  const rowClassNameFn = (data: { row: DbVersion }) =>
    data.row.enable ? 'sub-version-table-row' : 'sub-version-table-row-disabled';

  const handleEditVersionSeriesSuccess = () => {
    emits('refreshVersionList');
    emits('refreshReleaseList');
  };

  const handleDeleteVersionSuccess = () => {
    fetchTableData();
    emits('refreshReleaseList');
  };

  const handleClearSearch = () => {
    tableFilterValue.value = {};
    handleFilterChange({ filter: {} });
  };

  // 版本号比较函数：比较 full_version 格式如 1.2.0.0.0.0，按段数值从高到低
  const compareVersion = (versionA: string, versionB: string): number => {
    const segCmp = compareSegmentsDesc(parseVersionSegments(versionA.trim()), parseVersionSegments(versionB.trim()));
    if (segCmp !== 0) {
      return segCmp;
    }
    return versionA.localeCompare(versionB, undefined, { numeric: true, sensitivity: 'base' });
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
        childrenList.sort((a: any, b: any) => compareName(a.name, b.name));
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
    width: 100%;

    .version-name-table-cell {
      max-width: 500px;
      overflow: hidden;
      box-sizing: border-box;

      &[colspan] {
        max-width: none;
      }
    }

    .version-packages-table-cell {
      max-width: 600px;
      overflow: hidden;
      box-sizing: border-box;

      &[colspan] {
        max-width: none;
      }
    }

    .t-table__header {
      th {
        background-color: #f0f1f5 !important;

        &:hover {
          background-color: #dcdee5 !important;
        }
      }

      // .t-table__th-full_version {
      //   padding-left: 32px !important;
      // }

      .version-file-column-title {
        .tip-icon {
          font-size: 14px;
          color: #c4c6cc;
          cursor: pointer;

          &:hover {
            color: #3a84ff;
          }
        }
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
      width: 100%;
      padding-right: 14px;
      padding-left: 14px;
      overflow: hidden;

      &.is-recommend {
        .tags-main {
          visibility: visible !important;
        }
      }

      // 让 .tags-main 与 .set-recommended 在同一格子中堆叠，
      // 列宽始终按更宽的按钮预留，避免 hover 切换时列宽抖动
      &.text-overflow-layout {
        .layout-append {
          display: grid;
          align-items: center;

          > * {
            grid-column: 1;
            grid-row: 1;
          }
        }
      }

      .version-display-name {
        margin-right: 6px;
        overflow: hidden;
        color: #3a84ff;
        text-overflow: ellipsis;
        white-space: nowrap;
        flex: 1;
        cursor: pointer;
      }

      .tags-main {
        display: flex;
        align-items: center;

        .column-describe-tip {
          margin-left: 6px;
          font-size: 14px;
          color: #c4c6cc;
          cursor: pointer;

          &:hover {
            color: #3a84ff;
          }
        }
      }

      .set-recommended {
        cursor: pointer;
        visibility: hidden;

        &.is-recommended {
          color: #ffb400;
          visibility: visible !important;
        }

        &.is-disabled {
          visibility: hidden !important;
        }
      }
    }

    .os-limit-column {
      display: flex;

      & ~ .os-limit-column {
        margin-top: 4px;
      }

      .version-file-name {
        margin-right: 6px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        flex: 1;
      }

      .version-tags {
        .bk-tag {
          cursor: pointer;
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
        .set-recommended {
          visibility: visible;
        }
      }
    }

    .set-recommended {
      cursor: pointer;
    }
  }

  .sub-version-table-row-disabled {
    color: #c4c6cc;
  }
</style>
