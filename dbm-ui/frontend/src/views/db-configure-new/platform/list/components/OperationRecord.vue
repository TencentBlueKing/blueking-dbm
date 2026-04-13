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
      :placeholder="t('搜索操作人_操作时间_配置名称_参数类型_操作类型_参数名')"
      style="width: 500px"
      @change="handleQuickSearchChange" />
    <DbTable
      ref="tableRef"
      :data-source="dataSource"
      fixed-pagination
      row-key="id"
      @clear-search="handleQuickSearchChange">
      <TableColumn
        col-key="updated_at"
        :title="t('操作时间')"
        :width="220">
        <template #default="{ row }">
          {{ row.updated_at || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="op_user"
        :title="t('操作人')"
        :width="140">
        <template #default="{ row }">
          {{ row.op_user || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="conf_type_lc"
        :title="t('配置类型')"
        :width="120">
        <template #default="{ row }">
          <BkTag>
            {{ row.conf_type_lc }}
          </BkTag>
        </template>
      </TableColumn>
      <TableColumn
        col-key="conf_file_lc"
        ellipsis
        :title="t('配置文件')">
        <template #default="{ row }">
          <BkTag>
            {{ row.conf_type_lc }}
          </BkTag>
        </template>
      </TableColumn>
      <TableColumn
        col-key="op_type"
        :title="t('操作类型')"
        :width="120">
        <template #default="{ row }">
          <BkTag :theme="operateTypeThemeMap[row.op_type]?.theme || ''">
            {{ operateTypeThemeMap[row.op_type]?.text || '--' }}
          </BkTag>
        </template>
      </TableColumn>
      <TableColumn
        col-key="conf_name"
        ellipsis
        :title="t('操作参数')">
        <template #default="{ row }">
          {{ row.conf_name || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="operation"
        fixed="right"
        :title="t('操作')"
        :width="120">
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
              <td>{{ t('其他配置') }}</td>
              <td>
                <BkCheckboxGroup
                  disabled
                  :model-value="beforeCheckboxValues">
                  <BkCheckbox label="flag_locked">
                    {{ t('写入配置文件') }}
                  </BkCheckbox>
                  <BkCheckbox label="flag_readonly">
                    {{ t('业务可修改') }}
                  </BkCheckbox>
                  <BkCheckbox label="need_restart">
                    {{ t('重启生效') }}
                  </BkCheckbox>
                  <BkCheckbox label="flag_encrypt">
                    {{ t('值加密') }}
                  </BkCheckbox>
                </BkCheckboxGroup>
              </td>
              <td :class="{ 'is-changed': hasCheckboxChanged }">
                <BkCheckboxGroup
                  disabled
                  :model-value="afterCheckboxValues">
                  <BkCheckbox label="flag_locked">
                    {{ t('写入配置文件') }}
                  </BkCheckbox>
                  <BkCheckbox label="flag_readonly">
                    {{ t('业务可修改') }}
                  </BkCheckbox>
                  <BkCheckbox label="need_restart">
                    {{ t('重启生效') }}
                  </BkCheckbox>
                  <BkCheckbox label="flag_encrypt">
                    {{ t('值加密') }}
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
  import { useI18n } from 'vue-i18n';

  import ConfigNameChangeModel, { type ConfigNameChangeImage } from '@services/model/config/config-name-change';
  import { getConfigNameChanges } from '@services/source/configs';

  import DbTable from '@components/db-table/IndexNew.vue';

  interface Props {
    clusterType: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const searchValue = ref<Record<string, any>>({});

  const isShowDetail = ref(false);
  const detailRow = ref<ConfigNameChangeModel>();

  const quickSearchData = [
    {
      id: 'op_user',
      name: t('操作人'),
      type: 'input' as const,
    },
    {
      id: 'updated_at',
      name: t('操作时间'),
      type: 'input' as const,
    },
    {
      id: 'conf_name',
      name: t('参数名'),
      type: 'input' as const,
    },
    {
      id: 'conf_type',
      name: t('配置类型'),
      type: 'input' as const,
    },
    {
      id: 'op_type',
      name: t('操作类型'),
      type: 'input' as const,
    },
  ];

  type TagTheme = '' | 'danger' | 'info' | 'success' | 'warning';

  const operateTypeThemeMap: Record<string, { text: string; theme: TagTheme }> = {
    add: { text: t('新增参数'), theme: 'success' },
    remove: { text: t('删除参数'), theme: 'danger' },
    update: { text: t('修改参数'), theme: 'warning' },
    upsert: { text: t('新增参数'), theme: 'success' },
  };

  const dataSource = async (params: { limit: number; offset: number }) => {
    if (!props.clusterType) {
      return { count: 0, results: [] };
    }
    const res = await getConfigNameChanges({
      namespace: props.clusterType,
    });

    let filteredData = res.results || [];

    // 默认按时间倒序
    filteredData.sort((a, b) => {
      const timeA = a.updated_at ? String(a.updated_at) : '';
      const timeB = b.updated_at ? String(b.updated_at) : '';
      return timeB.localeCompare(timeA);
    });
    const filters = searchValue.value;
    if (Object.keys(filters).length > 0) {
      filteredData = filteredData.filter((item) =>
        Object.entries(filters).every(([key, val]) => {
          if (!val) return true;
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
    { key: 'value_default', label: t('默认值') },
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
      b.flag_locked !== a.flag_locked ||
      b.flag_readonly !== a.flag_readonly ||
      b.need_restart !== a.need_restart ||
      b.flag_encrypt !== a.flag_encrypt
    );
  });

  watch(
    () => props.clusterType,
    () => {
      nextTick(() => {
        tableRef.value?.fetchData({}, true);
      });
    },
  );
  const checkboxKeys = ['flag_locked', 'flag_readonly', 'need_restart', 'flag_encrypt'] as const;

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
  }
</style>
