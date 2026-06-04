<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
-->

<template>
  <BkLoading :loading="loading">
    <!-- 过滤胶囊 + 搜索 -->
    <div class="param-operations mb-16">
      <div class="param-operations-left">
        <span
          v-show="counts.custom > 0"
          class="filter-pill chip-custom"
          :class="{ active: activeFilter === 'custom' }"
          @click="handleCapsuleFilterChange('custom')">
          {{ t('自定义') }}
          <span class="pill-count custom">{{ counts.custom }}</span>
        </span>
        <span
          v-show="counts.changed > 0"
          class="filter-pill chip-default"
          :class="{ active: activeFilter === 'changed' }"
          @click="handleCapsuleFilterChange('changed')">
          {{ t('参数值变化') }}
          <span class="pill-count changed">{{ counts.changed }}</span>
        </span>
        <span
          v-show="counts.removed > 0"
          class="filter-pill chip-deprecated"
          @click="handleShowDeprecated">
          {{ t('已废弃') }}
          <span class="pill-count removed">{{ counts.removed }}</span>
        </span>
      </div>
      <div class="param-operations-right">
        <DbQuickSearch
          v-model="searchValue"
          :data="quickSearchData"
          parse-url
          :placeholder="t('搜索参数名_当前值_允许值_重启生效')"
          style="width: 500px"
          @change="refreshData" />
      </div>
    </div>
    <DbTable
      ref="tableRef"
      :data-source="filteredDataSource"
      :default-limit="100"
      :filter-value="searchValue"
      :fixed-pagination="false"
      row-key="conf_name"
      @clear-search="refreshData"
      @filter-change="handleColumnFilterChange"
      @request-success="initDescriptionTippy">
      <TableColumn
        col-key="conf_name"
        fixed="left"
        :min-width="300"
        :title="t('参数名')"
        :width="300">
        <template #default="{ row }">
          <span>{{ row.conf_name }}</span>
          <DbIcon
            v-if="row.description"
            class="param-desc-icon ml-4"
            :data-conf-name="row.conf_name"
            :data-description="row.description"
            type="bk-dbm-icon db-icon-attention" />
          <BkTag
            v-if="row.diff_type === 'new'"
            class="ml-8"
            size="small"
            theme="success">
            NEW
          </BkTag>
        </template>
      </TableColumn>
      <TableColumn
        col-key="conf_value"
        ellipsis
        :title="t('参数值')"
        :width="300">
        <template #default="{ row }">
          <span
            v-bk-tooltips="{
              content: row.flag_encrypt === 1 ? '******' : (row.conf_value ?? '--'),
              disabled: !row.conf_value || !overflowStates[row.conf_name],
              extCls: 'param-table-value-tooltip',
            }"
            class="value-cell-text"
            @mouseenter="handleCellMouseEnter($event, row)">
            {{ row.flag_encrypt === 1 ? '******' : (row.conf_value ?? '--') }}
          </span>
          <!-- 新增标注 -->
          <span
            v-if="row.diff_type === 'new'"
            class="value-tag">
            ({{ t('新增') }})
          </span>
          <!-- 值变化：源值对比 -->
          <span
            v-if="row.diff_type === 'changed' && row.source_conf_value !== undefined"
            class="value-tag">
            ({{ t('源值') }}: {{ row.flag_encrypt === 1 ? '******' : (row.source_conf_value ?? '--') }})
          </span>
          <!-- 自定义标注 -->
          <BkTag
            v-if="row.value_source === 'custom'"
            class="ml-8"
            size="small"
            theme="warning">
            {{ t('自定义') }}
          </BkTag>
        </template>
      </TableColumn>
      <TableColumn
        col-key="value_allowed"
        ellipsis
        :title="t('允许值')"
        :width="300">
        <template #default="{ row }">
          <template v-if="row.value_type_sub && row.value_type_sub !== 'STRING'">
            <BkTag>{{ row.value_type_sub }}</BkTag>
            <span class="ml-4">{{ row.value_allowed || '--' }}</span>
          </template>
          <span
            v-else
            class="no-constraint-text">
            {{ t('无约束') }}
          </span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="need_restart"
        :filter="needRestartFilter"
        :title="t('重启生效')"
        :width="100">
        <template #default="{ row }">
          {{ row.need_restart === 1 ? t('是') : t('否') }}
        </template>
      </TableColumn>
    </DbTable>
  </BkLoading>
</template>

<script setup lang="ts">
  import type { Instance } from 'tippy.js';
  import { computed, markRaw, nextTick, onUnmounted, ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { CloneConfItem } from '@services/source/configs';

  import { dbTippy } from '@common/tippy';

  import MultipleSelect from '@components/db-table/components/MultipleSelect.vue';
  import DbTable from '@components/db-table/IndexNew.vue';

  interface Props {
    /** 废弃参数数量 */
    deprecatedCount?: number;
  }

  defineOptions({
    name: 'CloneModuleParamTable',
  });

  const props = withDefaults(defineProps<Props>(), {
    deprecatedCount: 0,
  });

  const emit = defineEmits<(e: 'deprecatedClick') => void>();

  const { t } = useI18n();

  // ====== 响应式状态 ======
  const allItems = ref<CloneConfItem[]>([]);
  const tableRef = ref<InstanceType<typeof DbTable>>();
  const tippyInstances: Instance[] = [];
  const loading = ref(false);
  /** 记录单元格文本是否溢出 */
  const overflowStates = ref<Record<string, boolean>>({});
  /** 内部过滤状态 */
  const activeFilter = ref<'all' | 'custom' | 'changed' | 'removed'>('all');
  // 搜索
  const searchValue = ref<Record<string, any>>({});
  const quickSearchData = [
    { id: 'conf_name', name: t('参数名'), type: 'input' as const },
    { id: 'conf_value', name: t('参数值'), type: 'input' as const },
    { id: 'value_allowed', name: t('允许值'), type: 'input' as const },
    {
      id: 'need_restart',
      list: [
        { label: t('是'), value: '1' },
        { label: t('否'), value: '0' },
      ],
      name: t('重启生效'),
      type: 'multiple' as const,
    },
  ];

  // ====== 计算属性 ======

  /** 重启生效列筛选配置 */
  const needRestartFilter = {
    component: markRaw(MultipleSelect),
    name: t('重启生效'),
    props: {
      list: [
        { label: t('是'), value: '1' },
        { label: t('否'), value: '0' },
      ],
    },
    showConfirmAndReset: true,
  };

  /** 各类数量统计（当前 Tab 下） */
  const counts = computed(() => ({
    changed: allItems.value.filter((i) => i.diff_type === 'changed' || i.diff_type === 'new').length,
    custom: allItems.value.filter((i) => i.value_source === 'custom').length,
    removed: props.deprecatedCount ?? 0,
  }));

  // ====== 方法 ======
  /** 刷新表格 */
  const refreshData = () => {
    tableRef.value?.fetchData({}, true);
  };

  /** 切换过滤类型（胶囊） */
  const handleCapsuleFilterChange = (type: 'custom' | 'changed') => {
    activeFilter.value = activeFilter.value === type ? 'all' : type;
    refreshData();
  };

  /** 列筛选值变化（表头筛选） */
  const handleColumnFilterChange = (filterValue: Record<string, string>) => {
    searchValue.value = filterValue;
  };

  /** 初始化描述 tippy 提示 */
  const initDescriptionTippy = () => {
    tippyInstances.forEach((inst) => inst.destroy());
    tippyInstances.length = 0;

    nextTick(() => {
      const icons = document.querySelectorAll('.clone-module-page .param-desc-icon');
      icons.forEach((el) => {
        const iconEl = el as HTMLElement;
        const confName = iconEl.dataset.confName || '';
        const description = iconEl.dataset.description || '';
        if (!description) return;

        const content = document.createElement('div');
        content.className = 'description-tippy-content';
        content.innerHTML = `<div class="desc-title">${confName}</div><div class="desc-text">${description}</div>`;

        tippyInstances.push(
          dbTippy(iconEl, {
            allowHTML: true,
            appendTo: () => document.body,
            arrow: true,
            content,
            hideOnClick: false,
            interactive: false,
            placement: 'top',
            theme: 'light',
            trigger: 'mouseenter focus',
            zIndex: 9999,
          }),
        );
      });
    });
  };

  /** 过滤后的数据源 */
  const filteredDataSource = (params: { limit: number; offset: number }) => {
    let data = [...allItems.value];

    if (activeFilter.value === 'custom') {
      data = data.filter((i) => i.value_source === 'custom');
    } else if (activeFilter.value === 'changed') {
      data = data.filter((i) => i.diff_type === 'changed' || i.diff_type === 'new');
    }

    // 搜索 + 列筛选统一过滤
    const filters = searchValue.value;
    if (Object.keys(filters).length > 0) {
      data = data.filter((item) =>
        Object.entries(filters).every(([key, val]) => {
          if (!val) return true;
          if (key === 'need_restart') {
            return val.split(',').includes(String(item.need_restart));
          }
          const search = String(val).toLowerCase();
          const fieldValue = String((item as Record<string, any>)[key] ?? '').toLowerCase();
          return fieldValue.includes(search);
        }),
      );
    }

    const start = params.offset;
    const end = start + params.limit;
    const result = {
      count: data.length,
      results: data.slice(start, end),
    };

    return Promise.resolve(result);
  };

  /** 显示废弃参数侧滑 */
  const handleShowDeprecated = () => {
    emit('deprecatedClick');
  };

  /** 检测单元格文本是否溢出 */
  const handleCellMouseEnter = (e: MouseEvent, row: CloneConfItem) => {
    const el = e.target as HTMLElement;
    overflowStates.value[row.conf_name] = el.scrollWidth > el.clientWidth;
  };

  /** 设置数据（由父组件调用） */
  const setData = (items: CloneConfItem[]) => {
    allItems.value = items;
    nextTick(() => refreshData());
  };

  // ====== 生命周期 ======
  onUnmounted(() => {
    tippyInstances.forEach((inst) => inst.destroy());
    tippyInstances.length = 0;
  });

  defineExpose({ counts, refreshData, setData });
</script>

<style lang="less" scoped>
  .param-operations {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .param-operations-left {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .param-operations-right {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .filter-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    border-radius: 14px;
    border: 1px solid transparent;
    background: #f5f7fa;
    color: #63656e;
    font-size: 13px;
    line-height: 20px;
    cursor: pointer;
    user-select: none;
    transition:
      background 0.15s,
      border-color 0.15s,
      color 0.15s;

    &:hover {
      background: #ebeef5;
      color: #313238;
    }

    &.chip-default {
      .pill-count {
        background: #3a84ff;
      }

      &.active {
        border-color: #3a84ff;
        background: #e1ecff;
        color: #1768ef;
      }
    }

    &.chip-custom {
      .pill-count {
        background: #e5a829;
      }

      &.active {
        border-color: #e5a829;
        background: #fff4d6;
        color: #b8801f;
      }
    }

    &.chip-deprecated {
      background: #fff4ec;
      color: #d97706;

      &:hover {
        background: #ffe0c2;
        color: #b45309;
      }

      &::after {
        content: '\203A';
        font-size: 14px;
        line-height: 1;
        opacity: 0.7;
        margin-left: 2px;
      }

      .pill-count {
        background: #ea3636;
      }
    }
  }

  .pill-count {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 18px;
    height: 18px;
    padding: 0 6px;
    font-size: 12px;
    font-weight: 700;
    line-height: 18px;
    color: #fff;
    border-radius: 9px;
  }

  .pill-count.custom {
    background: #f59500;
  }

  .pill-count.changed {
    background: #3a84ff;
  }

  .pill-count.removed {
    background: #ea3636;
  }

  .value-cell-text {
    max-width: 300px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .value-tag {
    margin-left: 4px;
    font-size: 12px;
    line-height: 18px;
    white-space: nowrap;
    color: #979ba5;
  }

  .param-desc-icon {
    font-size: 14px;
    cursor: pointer;
    color: #c4c6cc;

    &:hover {
      color: #3a84ff;
    }
  }

  .no-constraint-text {
    color: #c4c6cc;
  }
</style>

<style lang="less">
  .param-table-value-tooltip {
    max-width: 400px;
    word-break: break-word;
  }

  .description-tippy-content {
    max-width: 320px;
    padding: 12px 16px;

    .desc-title {
      margin-bottom: 8px;
      font-size: 12px;
      font-weight: 600;
      color: #313238;
      word-break: break-all;
    }

    .desc-text {
      font-size: 12px;
      line-height: 22px;
      color: #63656e;
      word-break: break-word;
    }
  }
</style>
