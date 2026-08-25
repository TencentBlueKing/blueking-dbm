<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div class="platform-operation-record">
    <DbQuickSearch
      v-model="searchValue"
      class="mb-16"
      :data="quickSearchData"
      :placeholder="t('搜索操作时间_操作人_配置类型_配置文件_操作类型_操作参数')"
      style="width: 500px"
      @change="handleQuickSearchChange" />
    <DbTable
      ref="tableRef"
      :custom-sort-method="handleSortChange"
      :data-source="dataSource"
      row-key="id"
      :sort="tableSort"
      @clear-search="handleQuickSearchChange">
      <!-- 1. 操作时间 -->
      <TableColumn
        col-key="updated_at"
        sorter
        :title="t('操作时间')"
        :width="200">
        <template #default="{ row }">
          {{ row.updated_at ? utcDisplayTime(row.updated_at) : '--' }}
        </template>
      </TableColumn>
      <!-- 2. 操作人 -->
      <TableColumn
        col-key="op_user"
        :title="t('操作人')"
        :width="130">
        <template #default="{ row }">
          {{ row.op_user || '--' }}
        </template>
      </TableColumn>
      <!-- 3. 配置类型 -->
      <TableColumn
        col-key="conf_type_lc"
        :title="t('配置类型')"
        :width="110">
        <template #default="{ row }">
          <BkTag>
            {{ row.conf_type_lc }}
          </BkTag>
        </template>
      </TableColumn>
      <!-- 4. 配置文件 -->
      <TableColumn
        col-key="conf_file_lc"
        ellipsis
        :title="t('配置文件')"
        :width="200">
        <template #default="{ row }">
          {{ row.conf_file_lc || '--' }}
        </template>
      </TableColumn>
      <!-- 5. 操作类型 -->
      <TableColumn
        col-key="op_type"
        :title="t('操作类型')"
        :width="110">
        <template #default="{ row }">
          <BkTag :theme="operateTypeThemeMap[row.op_type]?.theme || ''">
            {{ operateTypeThemeMap[row.op_type]?.text || '--' }}
          </BkTag>
        </template>
      </TableColumn>
      <!-- 6. 操作参数 -->
      <TableColumn
        col-key="conf_name"
        ellipsis
        :title="t('操作参数')"
        :width="220">
        <template #default="{ row }">
          {{ row.conf_name || '--' }}
        </template>
      </TableColumn>
      <!-- 7. 操作 -->
      <TableColumn
        col-key="row-operation"
        fixed="right"
        :title="t('操作')"
        :width="100">
        <template #default="{ row }">
          <BkButton
            text
            theme="primary"
            @click="handleViewDetail(row)">
            {{ t('查看详情') }}
          </BkButton>
        </template>
      </TableColumn>
    </DbTable>

    <!-- 查看详情侧滑 -->
    <BkSideslider
      :is-show="isShowDetail"
      quick-close
      :width="960"
      @closed="isShowDetail = false">
      <template #header>
        <div>
          <span>{{ t('查看操作详情') }}</span>
          <span class="detail-slider-subtitle">{{ detailRow?.conf_name || '' }}</span>
          <BkTag :theme="operateTypeThemeMap[detailRow?.op_type || '']?.theme || ''">
            {{ operateTypeThemeMap[detailRow?.op_type || '']?.text || '--' }}
          </BkTag>
        </div>
      </template>
      <div
        v-if="detailRow"
        class="operation-detail-content">
        <!-- 图例 + 仅显示修改项 -->
        <div class="detail-legend">
          <span class="legend-item">
            <span class="legend-color is-changed" />
            {{ t('更新') }}
          </span>
          <span class="legend-item">
            <span class="legend-color is-unchanged" />
            {{ t('无变化') }}
          </span>
          <BkCheckbox
            v-model="onlyShowChanged"
            class="legend-filter">
            {{ t('仅显示修改项') }}
          </BkCheckbox>
        </div>

        <!-- 对比表格 -->
        <table class="detail-compare-table">
          <thead>
            <tr>
              <th>{{ t('配置项') }}</th>
              <th>{{ t('修改前') }}</th>
              <th>{{ t('修改后') }}</th>
            </tr>
          </thead>
          <tbody>
            <template
              v-for="field of compareFields"
              :key="field.key">
              <tr v-if="!onlyShowChanged || isFieldChanged(field.key)">
                <td>{{ field.label }}</td>
                <td>{{ getFieldValue(detailRow.before_image, field.key) }}</td>
                <td :class="{ 'is-changed': isFieldChanged(field.key) }">
                  {{ getFieldValue(detailRow.after_image, field.key) }}
                </td>
              </tr>
            </template>
            <!-- checkbox 类型字段 -->
            <tr v-if="!onlyShowChanged || hasCheckboxChanged">
              <td>{{ t('业务配置规则') }}</td>
              <td>
                <BkCheckboxGroup
                  disabled
                  :model-value="beforeCheckboxValues">
                  <BkCheckbox label="flag_visible">
                    {{ t('业务默认可见') }}
                  </BkCheckbox>
                  <BkCheckbox label="flag_readonly">
                    {{ t('业务可编辑') }}
                  </BkCheckbox>
                  <BkCheckbox label="need_restart">
                    {{ t('重启生效') }}
                  </BkCheckbox>
                  <BkCheckbox label="flag_encrypt">
                    {{ t('加密存储') }}
                  </BkCheckbox>
                </BkCheckboxGroup>
              </td>
              <td :class="{ 'is-changed': hasCheckboxChanged }">
                <BkCheckboxGroup
                  disabled
                  :model-value="afterCheckboxValues">
                  <BkCheckbox label="flag_visible">
                    {{ t('业务默认可见') }}
                  </BkCheckbox>
                  <BkCheckbox label="flag_readonly">
                    {{ t('业务可编辑') }}
                  </BkCheckbox>
                  <BkCheckbox label="need_restart">
                    {{ t('重启生效') }}
                  </BkCheckbox>
                  <BkCheckbox label="flag_encrypt">
                    {{ t('加密存储') }}
                  </BkCheckbox>
                </BkCheckboxGroup>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </BkSideslider>
  </div>
</template>

<script setup lang="ts">
  import dayjs from 'dayjs';
  import type { TableSort } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';

  import ConfigNameChangeModel, { type ConfigNameChangeImage } from '@services/model/config/config-name-change';
  import { getConfigNameChanges } from '@services/source/configs';
  import { getUserList } from '@services/source/user';

  import DbTable from '@components/db-table/IndexNew.vue';

  import { utcDisplayTime } from '@utils';

  interface Props {
    namespace: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const searchValue = ref<Record<string, any>>({});

  // 受控排序状态
  const tableSort = ref<{ descending: boolean; sortBy: string }>({
    descending: true,
    sortBy: 'updated_at',
  });

  /** 配置类型枚举列表（从 getConfigNameChanges 返回数据中提取） */
  const confTypeList = ref<{ label: string; value: string }[]>([]);

  /** 配置文件枚举列表（从 getConfigNameChanges 返回数据中提取） */
  const confFileList = ref<{ label: string; value: string }[]>([]);

  /** 更新枚举列表：从数据中提取值并去重 */
  const updateEnumLists = (data: Record<string, any>[]) => {
    const confTypeSet = new Set<string>();
    const confFileSet = new Set<string>();

    data.forEach((item) => {
      const confTypeLc = item.conf_type_lc ?? '';
      if (confTypeLc) confTypeSet.add(confTypeLc);

      const confFileLc = item.conf_file_lc ?? '';
      if (confFileLc) confFileSet.add(confFileLc);
    });

    confTypeList.value = Array.from(confTypeSet).map((name) => ({
      label: name,
      value: name,
    }));
    confFileList.value = Array.from(confFileSet).map((name) => ({
      label: name,
      value: name,
    }));
  };

  const isShowDetail = ref(false);
  const detailRow = ref<ConfigNameChangeModel>();

  /** 搜索配置：字段顺序与表格列对齐 */
  const quickSearchData = computed(() => [
    // 1. 操作时间
    {
      id: 'updated_at',
      name: t('操作时间'),
      props: {
        shortcuts: [
          {
            text: t('近 1 小时'),
            value: () => [dayjs().subtract(1, 'hour').toDate(), dayjs().toDate()],
          },
          {
            text: t('近 12 小时'),
            value: () => [dayjs().subtract(12, 'hour').toDate(), dayjs().toDate()],
          },
          {
            text: t('今天'),
            value: () => [dayjs().startOf('day').toDate(), dayjs().endOf('day').toDate()],
          },
          {
            text: t('近 7 天'),
            value: () => [dayjs().subtract(6, 'day').startOf('day').toDate(), dayjs().endOf('day').toDate()],
          },
          {
            text: t('近 1 个月'),
            value: () => [dayjs().subtract(1, 'month').startOf('day').toDate(), dayjs().endOf('day').toDate()],
          },
          {
            text: t('近 3 个月'),
            value: () => [dayjs().subtract(3, 'month').startOf('day').toDate(), dayjs().endOf('day').toDate()],
          },
          {
            text: t('近 6 个月'),
            value: () => [dayjs().subtract(6, 'month').startOf('day').toDate(), dayjs().endOf('day').toDate()],
          },
        ],
      },
      type: 'datetime-range' as const,
    },
    // 2. 操作人（人员选择器）
    {
      id: 'op_user',
      name: t('操作人'),
      remoteMethod: (params: { defaultValue?: string; keyword?: string }) => {
        const requestParams: Record<string, string> = {};
        if (params.defaultValue) {
          Object.assign(requestParams, { exact_lookups: params.defaultValue });
        }
        if (params.keyword) {
          Object.assign(requestParams, { fuzzy_lookups: params.keyword });
        }
        return getUserList(requestParams).then((data) =>
          data.results.map((item) => ({
            label: `${item.username} (${item.display_name})`,
            value: item.username,
          })),
        );
      },
      remoteSearch: true,
      type: 'multiple' as const,
    },
    // 3. 配置类型（枚举下拉，从返回数据中动态提取）
    {
      id: 'conf_type_lc',
      list: confTypeList.value,
      name: t('配置类型'),
      type: 'multiple' as const,
    },
    // 4. 配置文件（枚举下拉，从返回数据中动态提取）
    {
      id: 'conf_file_lc',
      list: confFileList.value,
      name: t('配置文件'),
      type: 'multiple' as const,
    },
    // 5. 操作类型（枚举下拉）
    {
      id: 'op_type',
      list: Object.entries(operateTypeThemeMap).map(([value, item]) => ({
        label: item.text,
        value,
      })),
      name: t('操作类型'),
      type: 'multiple' as const,
    },
    // 6. 操作参数（文本输入，支持模糊匹配）
    {
      description: t('支持模糊搜索'),
      id: 'conf_name',
      name: t('操作参数'),
      type: 'input' as const,
    },
  ]);

  type TagTheme = '' | 'danger' | 'info' | 'success' | 'warning';

  /** 操作类型标签主题映射 */
  const operateTypeThemeMap: Record<
    string,
    {
      text: string;
      theme: TagTheme;
    }
  > = {
    add: {
      text: t('新增参数'),
      theme: 'success',
    },
    cancel_render: {
      text: t('取消使用'),
      theme: 'danger',
    },
    recover: {
      text: t('恢复初始值'),
      theme: 'info',
    },
    remove: {
      text: t('删除参数'),
      theme: 'danger',
    },
    update: {
      text: t('修改参数'),
      theme: 'warning',
    },
    // upsert: {
    //   text: t('新增参数'),
    //   theme: 'success',
    // },
  };

  const dataSource = async (params: { limit: number; offset: number }) => {
    if (!props.namespace) {
      return { count: 0, results: [] };
    }
    const res = await getConfigNameChanges(
      {
        namespace: props.namespace,
      },
      {
        permission: 'catch',
      },
    );

    // 更新枚举列表（配置类型、配置文件）
    updateEnumLists(res.results || []);

    let filteredData = res.results || [];

    // 按当前排序状态动态排序
    filteredData.sort((a, b) => {
      const valA = String((a as Record<string, any>)[tableSort.value.sortBy] ?? '');
      const valB = String((b as Record<string, any>)[tableSort.value.sortBy] ?? '');
      return tableSort.value.descending ? valB.localeCompare(valA) : valA.localeCompare(valB);
    });

    const filters = searchValue.value;
    if (Object.keys(filters).length > 0) {
      filteredData = filteredData.filter((item) =>
        Object.entries(filters).every(([key, val]) => {
          if (!val || (Array.isArray(val) && val.length === 0)) return true;

          // multiple 类型：值是数组
          if (Array.isArray(val)) {
            // datetime-range：值是 [Date, Date]
            if (key === 'updated_at') {
              const [start, end] = val as Date[];
              const itemDate = new Date((item as Record<string, any>)[key]);
              return itemDate >= start && itemDate <= end;
            }
            // multiple 枚举：值是字符串数组，判断数据中对应字段是否包含在数组中
            const fieldValue = String((item as Record<string, any>)[key] ?? '');
            return val.includes(fieldValue);
          }

          // input 类型：字符串模糊匹配
          const search = String(val).toLowerCase();
          const fieldValue = String((item as Record<string, any>)[key] ?? '').toLowerCase();
          return fieldValue.includes(search);
        }),
      );
    }

    const start = params.offset;
    const end = start + params.limit;
    return {
      count: filteredData.length,
      results: filteredData.slice(start, end),
    };
  };

  const handleQuickSearchChange = () => {
    tableRef.value?.fetchData({}, true);
  };

  /** 排序变化：更新受控状态并重新拉取数据 */
  const handleSortChange = (sort: TableSort) => {
    if (!Array.isArray(sort) && sort?.sortBy) {
      tableSort.value = { descending: sort.descending, sortBy: sort.sortBy };
    }
    tableRef.value?.fetchData({}, true);
  };

  const handleViewDetail = (row: ConfigNameChangeModel) => {
    detailRow.value = row;
    onlyShowChanged.value = true;
    isShowDetail.value = true;
  };

  // 对比字段定义
  const compareFields = [
    { key: 'conf_name', label: t('参数名') },
    { key: 'conf_name_lc', label: t('参数显示名') },
    { key: 'value_type', label: t('数据类型') },
    { key: 'value_type_sub', label: t('约束类型') },
    { key: 'value_allowed', label: t('允许值') },
    { key: 'value_default', label: t('平台默认值') },
    { key: 'description', label: t('描述') },
  ];

  const onlyShowChanged = ref(true);

  const getFieldValue = (image: ConfigNameChangeImage | undefined, key: string) => {
    if (!image) return '--';
    return String((image as Record<string, any>)[key] ?? '--');
  };

  const isFieldChanged = (key: string) => {
    if (!detailRow.value) return false;
    const before = getFieldValue(detailRow.value.before_image, key);
    const after = getFieldValue(detailRow.value.after_image, key);
    return before !== after;
  };

  const hasCheckboxChanged = computed(() => {
    if (!detailRow.value) return false;
    const b = detailRow.value.before_image;
    const a = detailRow.value.after_image;
    if (!b || !a) return true;
    return (
      b.flag_visible !== a.flag_visible ||
      b.flag_readonly !== a.flag_readonly ||
      b.need_restart !== a.need_restart ||
      b.flag_encrypt !== a.flag_encrypt
    );
  });

  watch(
    () => props.namespace,
    () => {
      nextTick(() => {
        tableRef.value?.fetchData({}, true);
      });
    },
  );

  const checkboxKeys = ['flag_visible', 'flag_readonly', 'need_restart', 'flag_encrypt'] as const;

  const getCheckboxValues = (image: ConfigNameChangeImage | undefined) => {
    if (!image) return [];
    return checkboxKeys.filter((key) => {
      if (key === 'flag_readonly') return !image[key];
      return !!image[key];
    });
  };

  const beforeCheckboxValues = computed(() => getCheckboxValues(detailRow.value?.before_image));
  const afterCheckboxValues = computed(() => getCheckboxValues(detailRow.value?.after_image));
</script>

<style lang="less" scoped>
  .platform-operation-record {
    padding: 0 16px;
  }

  .detail-slider-header {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .detail-slider-subtitle {
    position: relative;
    padding: 0 8px;
    margin-left: 8px;
    font-size: 14px;
    line-height: 22px;
    color: #979ba5;

    &::before {
      position: absolute;
      top: 50%;
      left: 0;
      width: 1px;
      height: 16px;
      content: '';
      background: #dcdee5;
      transform: translateY(-50%);
    }
  }

  .operation-detail-content {
    padding: 18px 24px;
  }

  .detail-legend {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 16px;

    .legend-item {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 12px;
      color: #63656e;
    }

    .legend-color {
      width: 16px;
      height: 16px;
      border-radius: 2px;

      &.is-changed {
        border: 1px solid var(--Warning-2, #f59500);
        background: var(--Warning-7, #fdf4e8);
      }

      &.is-unchanged {
        border: 1px solid #dcdee5;
        background: #fff;
      }
    }

    .legend-filter {
      margin-left: auto;
    }
  }

  .detail-compare-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 12px;

    th,
    td {
      padding: 10px 16px;
      text-align: left;
      border: 1px solid #dcdee5;
    }

    th {
      font-weight: normal;
      color: #313238;
      background: #f0f1f5;
    }

    td {
      color: #63656e;
    }

    td.is-changed {
      background: #fdf4e8;
    }

    :deep(.bk-checkbox-group) {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    :deep(.bk-checkbox ~ .bk-checkbox) {
      margin-left: 0;
    }

    :deep(.bk-checkbox.is-disabled) {
      color: inherit;
    }
  }
</style>
