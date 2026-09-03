<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <PrimaryTable
    class="sub-version-table-main"
    :data="tableData"
    :filter-value="tableFilterValue"
    :loading="loading"
    :max-height="tableMaxHeight"
    resizable
    :row-class-name="rowClassNameFn"
    row-key="uuid"
    :rowspan-and-colspan="rowspanAndColspan"
    @change="handleFilterChange"
    @sort-change="handleSortChange">
    <TableColumn
      col-key="name"
      ellipsis
      :filter="tableFilter?.name"
      resizable
      :title="t('版本名')"
      :width="280">
      <template #default="{ row }: { row: TableRow }">
        <div
          v-if="row.rowType === 'series'"
          class="version-series-header"
          @click="() => handleVersionSeriesToggle(row.series.id)">
          <DbIcon
            class="collapse-icon"
            :class="{ 'is-collapse': collapseIdSet.has(row.series.id) }"
            type="down-shape" />
          <OperationHeader
            :data="row.series"
            :db-type="dbType"
            :db-version-list-count="row.versionCount"
            :existed-version-name-list="totalVersionNames"
            :permission="permission"
            @add-new-version="() => emits('addNewVersion', row.series)"
            @edit-version-series="handleEditVersionSeriesSuccess" />
        </div>
        <TextOverflowLayout
          v-else
          class="version-display-column"
          :class="{ 'is-recommend': row.recommend }">
          <template #prepend>
            <RecommendConfig
              :data="row"
              :db-type="dbType"
              :permission="permission"
              @success="() => emits('refreshDbVersionList')" />
          </template>
          <AuthButton
            action-id="package_manage"
            :permission="permission"
            :resource="dbType"
            text
            theme="primary"
            @click="() => emits('editDbVersion', row)">
            {{ row.name || '--' }}
          </AuthButton>
          <template #append>
            <span class="tags-main">
              <BkTag
                size="small"
                :theme="versionStageMap[row.phase]?.theme">
                {{ versionStageMap[row.phase]?.label }}
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
      </template>
    </TableColumn>
    <TableColumn
      col-key="full_version"
      :filter="tableFilter?.full_version"
      resizable
      :title="t('版本号')"
      :width="180">
      <template #default="{ row }: { row: VersionRow }"> {{ row.full_version }} </template>
    </TableColumn>
    <TableColumn
      col-key="packages"
      resizable
      :width="380">
      <template #title>
        <span class="version-file-column-title">
          {{ t('版本文件') }}
          <DbIcon
            v-bk-tooltips="{
              content: t('一个版本可能含多个介质文件（不同 OS 适配），列表默认展示首文件，点击 +N 可展开全部'),
              theme: 'light',
            }"
            class="tip-icon"
            type="attention" />
        </span>
      </template>
      <template #default="{ row }: { row: VersionRow }">
        <PackageFileCell :data="row" />
      </template>
    </TableColumn>
    <TableColumn
      col-key="distribution_snapshot"
      resizable
      :title="t('关联实例')"
      :width="100">
      <template #default="{ row }: { row: VersionRow }"> {{ row.totalInstance }} </template>
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
      <template #default="{ row }: { row: VersionRow }">
        <EnableConfig
          :data="row"
          :db-type="dbType"
          :permission="permission"
          @success="() => emits('refreshDbVersionList')" />
      </template>
    </TableColumn>
    <TableColumn
      col-key="updater"
      :filter="tableFilter?.updater"
      resizable
      :title="t('更新人')"
      :width="120">
      <template #default="{ row }: { row: VersionRow }"> {{ row.updater || '--' }} </template>
    </TableColumn>
    <TableColumn
      col-key="update_at"
      resizable
      sorter
      :title="t('更新时间')"
      :width="200">
      <template #default="{ row }: { row: VersionRow }"> {{ utcDisplayTime(row.update_at) }} </template>
    </TableColumn>
    <TableColumn
      col-key="id"
      fixed="right"
      :title="t('操作')"
      :width="150">
      <template #default="{ row }: { row: VersionRow }">
        <AuthButton
          action-id="package_manage"
          :permission="permission"
          :resource="dbType"
          size="small"
          text
          theme="primary"
          @click="() => emits('editDbVersion', row)">
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
    @refresh="() => emits('refreshDbVersionList')" />
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import _ from 'lodash';
  import { type TableRowData, type TableSort } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';

  import { getDbVersionList, getVersionSeriesList } from '@services/source/version';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { versionStageMap } from '@views/version-files/v2/common';

  import { utcDisplayTime } from '@utils';

  import useVersionFilter from '../../hooks/useVersionFilter';

  import DeleteVersion from './components/DeleteVersion.vue';
  import DownloadPackage from './components/DownloadPackage.vue';
  import EnableConfig from './components/EnableConfig.vue';
  import OperationHeader from './components/OperationHeader.vue';
  import PackageFileCell from './components/PackageFileCell.vue';
  import RecommendConfig from './components/RecommendConfig.vue';

  interface Props {
    dbType: string;
    dbVersionList?: DbVersion[];
    loading?: boolean;
    permission: boolean;
    versionSeriesList?: VersionSeries;
  }

  interface Exposes {
    clearFilter: () => void;
    setFilterValue: (value: Record<string, string>) => void;
  }

  interface Emits {
    (e: 'editDbVersion', version: DbVersion): void;
    (e: 'addNewVersion', versionSeries: VersionSeries[number]): void;
    (e: 'refreshDbVersionList'): void;
    (e: 'refreshReleaseList'): void;
    (e: 'refreshVersionList'): void;
    (e: 'filterValueChange', value: Record<string, string>): void;
  }

  type VersionSeries = ServiceReturnType<typeof getVersionSeriesList>;
  type DbVersion = ServiceReturnType<typeof getDbVersionList>[number];
  // 版本行：接口返回的版本对象 + 表格需要的派生字段
  type VersionRow = {
    rowType: 'version';
    totalInstance: number;
    uuid: string;
  } & DbVersion;
  // 系列行：展开时在它下面 append 所属的版本行
  type SeriesRow = {
    rowType: 'series';
    series: VersionSeries[number];
    uuid: string;
    versionCount: number;
  };
  type TableRow = SeriesRow | VersionRow;
  // 表格只支持单列排序
  type SingleSort = Exclude<TableSort, unknown[]>;
  // 可筛选的列都是标量字段
  type FilterFieldValue = boolean | number | string;

  const props = withDefaults(defineProps<Props>(), {
    dbVersionList: () => [],
    loading: false,
    versionSeriesList: () => [],
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const tableMaxHeight = ref(0);
  const collapseIdSet = ref<Set<number>>(new Set());
  const tableFilterValue = ref<Record<string, string>>({});
  const tableSortValue = ref<SingleSort>();

  const totalVersionNames = computed(() => props.versionSeriesList.map((item) => item.name.toLocaleLowerCase()));
  const isSearching = computed(() => hasActiveFilter(tableFilterValue.value));
  // 在接口返回的版本对象之上补出表格行需要的派生字段，不回写 props 数据
  const versionRowList = computed<VersionRow[]>(() =>
    props.dbVersionList.map((item) => ({
      ...item,
      rowType: 'version' as const,
      totalInstance: (item.packages || []).reduce((sum, pkg) => sum + pkg.instances, 0),
      uuid: `version-${item.id}`,
    })),
  );
  // 系列下的版本总数，不受筛选影响：系列名后的计数与「删除系列」的前置校验都用它
  const versionCountMap = computed(() => _.countBy(versionRowList.value, 'version_series'));

  // 表格的唯一数据源：系列 → 版本的树，表格行由它按「筛选 → 排序 → 拍平」派生
  const versionSeriesTree = computed(() => {
    const versionGroup = _.groupBy(versionRowList.value, 'version_series');
    return props.versionSeriesList.map((series) => ({
      children: versionGroup[series.id] || [],
      series,
    }));
  });

  const filteredSeriesTree = computed(() => {
    if (!isSearching.value) {
      return versionSeriesTree.value;
    }
    const filterKeys = Object.keys(tableFilterValue.value);
    return (
      versionSeriesTree.value
        .map((item) => ({
          children: item.children.filter((version) =>
            filterKeys.every((key) =>
              checkFilterValue(tableFilterValue.value[key], version[key as keyof VersionRow] as FilterFieldValue),
            ),
          ),
          series: item.series,
        }))
        // 筛选态下不展示没有命中版本的系列
        .filter((item) => item.children.length > 0)
    );
  });

  const sortedSeriesTree = computed(() => {
    const sortValue = tableSortValue.value;
    const sortDirection = sortValue?.descending ? -1 : 1;
    // 目前只有更新时间列可排序，值都是时间字符串
    const getSortTime = (item: VersionRow) =>
      sortValue ? dayjs(item[sortValue.sortBy as keyof VersionRow] as string).unix() : 0;
    const sortVersionList = (versionList: VersionRow[]) =>
      sortValue
        ? [...versionList].sort((a, b) => sortDirection * (getSortTime(a) - getSortTime(b)))
        : // 未排序时回到接口数据的默认顺序：同系列内版本号从高到低
          [...versionList].sort((a, b) => compareVersion(a.full_version, b.full_version));

    return filteredSeriesTree.value
      .map((item) => ({
        children: sortVersionList(item.children),
        series: item.series,
      }))
      .sort((itemA, itemB) => {
        // 没有版本的系列永远垫底，与是否排序无关
        const emptyDiff = Number(!itemA.children.length) - Number(!itemB.children.length);
        if (emptyDiff !== 0) {
          return emptyDiff;
        }
        // 未排序、或两个系列都没有版本时，系列间按版本名排
        if (!sortValue || !itemA.children.length) {
          return compareName(itemA.series.name, itemB.series.name);
        }
        // 系列间按各自最新的一条排
        return (
          sortDirection * (Math.max(...itemA.children.map(getSortTime)) - Math.max(...itemB.children.map(getSortTime)))
        );
      });
  });

  // 系列行与版本行共存于同一份表格数据，uuid 用不同前缀保证 row-key 稳定且不冲突
  const tableData = computed<TableRow[]>(() =>
    sortedSeriesTree.value.flatMap((item) => {
      const seriesRow: SeriesRow = {
        rowType: 'series',
        series: item.series,
        uuid: `series-${item.series.id}`,
        versionCount: versionCountMap.value[item.series.id] || 0,
      };
      return collapseIdSet.value.has(item.series.id) ? [seriesRow] : [seriesRow, ...item.children];
    }),
  );

  const { tableColumnFilter: tableFilter } = useVersionFilter(computed(() => props.dbVersionList));

  const enableTips = `${t('启用：所有场景均可使用，如：部署、升级')}\n${t('停用：存量集群替换不受影响，其它场景不可使用。注意：停用将自动清除推荐')}`;

  // 筛选值本来就是搜索栏给过来的时候不再回写搜索栏，否则两边会互相触发
  let skipSearchSync = false;

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

  const rowClassNameFn = ({ row }: { row: TableRow }) =>
    row.rowType === 'series' || row.enable ? 'sub-version-table-row' : 'sub-version-table-row-disabled';

  const hasActiveFilter = (filter: Record<string, string>) => Object.values(filter).some(Boolean);

  // 多值（筛选面板勾选多项）按枚举精确命中，单值（搜索栏输入）按包含匹配
  const checkFilterValue = (keyValue: string, value: FilterFieldValue) => {
    if (!keyValue) {
      return true;
    }
    const itemValue = value.toString();
    if (keyValue.includes(',')) {
      return keyValue.split(',').some((word: string) => word.includes(itemValue));
    }

    return itemValue.includes(keyValue);
  };

  const handleEditVersionSeriesSuccess = () => {
    emits('refreshVersionList');
    emits('refreshReleaseList');
  };

  const handleDeleteVersionSuccess = () => {
    emits('refreshDbVersionList');
    emits('refreshReleaseList');
  };

  const handleClearSearch = () => {
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

  const handleVersionSeriesToggle = (versionSeriesId: number) => {
    if (collapseIdSet.value.has(versionSeriesId)) {
      collapseIdSet.value.delete(versionSeriesId);
      return;
    }
    collapseIdSet.value.add(versionSeriesId);
  };

  // 系列行占满整行
  const rowspanAndColspan = ({ colIndex, row }: { colIndex: number; row: TableRowData }) => {
    if (row.rowType === 'series' && colIndex === 0) {
      return {
        colspan: 8,
      };
    }
    return {};
  };

  const handleSortChange = (payload: TableSort) => {
    if (Array.isArray(payload)) {
      return;
    }
    tableSortValue.value = payload;
  };

  const handleFilterChange = (payload: { filter?: Record<string, unknown> }) => {
    if (!payload.filter) {
      return;
    }
    // 筛选面板与搜索栏都按逗号分隔字符串取值，表格重置多选列时会给回数组，统一归一
    const newFilter = _.mapValues(payload.filter, (value) =>
      Array.isArray(value) ? value.join(',') : String(value ?? ''),
    );
    if (skipSearchSync) {
      skipSearchSync = false;
    } else {
      emits('filterValueChange', newFilter);
    }
    const isFilterChanged = !_.isEqual(tableFilterValue.value, newFilter);
    tableFilterValue.value = newFilter;
    // 命中的版本可能落在已收起的系列里，筛选条件变化时把命中的系列展开
    if (isFilterChanged && isSearching.value) {
      filteredSeriesTree.value.forEach((item) => collapseIdSet.value.delete(item.series.id));
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
    setFilterValue: (value: Record<string, string>) => {
      skipSearchSync = true;
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

      .version-series-header {
        display: flex;
        align-items: center;
        padding: 7px 12px;
        cursor: pointer;
        background: #fafbfd;
        border-radius: 2px;

        .collapse-icon {
          margin-right: 8px;
          font-size: 12px;
          transition: transform 0.3s;

          &.is-collapse {
            transform: rotate(-90deg);
          }
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

      .tags-main {
        display: flex;
        align-items: center;
        margin-left: 8px;

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
