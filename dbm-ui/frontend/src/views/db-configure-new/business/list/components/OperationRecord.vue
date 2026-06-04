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
  <div class="operation-record">
    <DbQuickSearch
      v-model="searchValue"
      class="mb-16"
      :data="quickSearchData"
      parse-url
      :placeholder="t('搜索操作时间_操作人_配置类型_配置文件_操作类型_操作参数')"
      style="width: 500px"
      @change="refreshTable" />
    <DbTable
      ref="tableRef"
      :custom-sort-method="handleCustomSort"
      :data-source="dataSource"
      row-key="id"
      :sort="tableSort"
      @clear-search="refreshTable"
      @request-success="initChangeTippy">
      <!-- 1. 操作时间 -->
      <TableColumn
        col-key="updated_at"
        sorter
        :title="t('操作时间')"
        :width="180">
        <template #default="{ row }">
          {{ row.updated_at || '--' }}
        </template>
      </TableColumn>
      <!-- 2. 操作人 -->
      <TableColumn
        col-key="op_user"
        :title="t('操作人')"
        :width="120">
        <template #default="{ row }">
          {{ row.op_user || '--' }}
        </template>
      </TableColumn>
      <!-- 3. 配置类型 -->
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
      <!-- 4. 配置文件 -->
      <TableColumn
        col-key="conf_file_lc"
        ellipsis
        :title="t('配置文件')"
        :width="140">
        <template #default="{ row }">
          {{ row.conf_file_lc || '--' }}
        </template>
      </TableColumn>
      <!-- 5. 操作类型 -->
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
      <!-- 6. 操作参数 -->
      <TableColumn
        col-key="conf_name"
        ellipsis
        :title="t('操作参数')"
        :width="200">
        <template #default="{ row }">
          {{ row.conf_name || '--' }}
        </template>
      </TableColumn>
      <!-- 7. 操作明细（自适应占满剩余空间） -->
      <TableColumn
        col-key="conf_value"
        :min-width="200"
        :title="t('操作明细')">
        <template #default="{ row }">
          <!-- 取消使用 -->
          <template v-if="row.op_type === 'cancel_render'"> -- </template>
          <!-- 新增参数：显示完整值 -->
          <span
            v-else-if="isAddType(row.op_type)"
            class="config-change-value is-add"
            :data-tool-tip="JSON.stringify({ type: 'add', after: row.after_image?.conf_value ?? '' })">
            <span class="config-change-value-text">{{ row.after_image?.conf_value || t('无') }}</span>
          </span>
          <!-- 修改参数/恢复默认/删除参数 -->
          <span
            v-else
            class="config-change-value"
            :data-tool-tip="
              JSON.stringify({
                type: 'change',
                before: row.before_image?.conf_value ?? '',
                after: row.after_image?.conf_value ?? '',
              })
            ">
            <span class="config-change-value-before">{{ row.before_image?.conf_value ?? '' }}</span>
            <span class="config-change-value-icon">
              <DbIcon
                size="small"
                type="bk-dbm-icon db-icon-arrow-right" />
            </span>
            <span class="config-change-value-after">{{ row.after_image?.conf_value ?? '' }}</span>
          </span>
        </template>
      </TableColumn>
    </DbTable>
  </div>
</template>

<script setup lang="ts">
  import dayjs from 'dayjs';
  import type { TableSort } from 'tdesign-vue-next';
  import type { Instance } from 'tippy.js';
  import { computed, inject, nextTick, onUnmounted, type Ref, ref, watch } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { getConfigItemChanges } from '@services/source/configs';
  import { getUserList } from '@services/source/user';

  import { dbTippy } from '@common/tippy';

  import DbTable from '@components/db-table/IndexNew.vue';

  interface Props {
    clusterType?: string;
    confFile?: string;
    confType?: string;
    levelName?: string;
    levelValue?: number | string;
  }

  const props = withDefaults(defineProps<Props>(), {
    clusterType: '',
    confFile: '',
    confType: '',
    levelName: '',
    levelValue: '',
  });

  const { t } = useI18n();
  const activeClusterType = inject<Ref<string>>('activeClusterType');
  const confTabs = inject<Ref<{ conf_file: string; conf_type: string; name: string }[]>>('confTabs');

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const searchValue = ref<Record<string, any>>({});

  // 受控排序状态
  const tableSort = ref<{ descending: boolean; sortBy: string }>({
    descending: true,
    sortBy: 'updated_at',
  });

  /** 配置类型枚举列表（从 getConfigItemChanges 返回数据中提取） */
  const confTypeList = ref<{ label: string; value: string }[]>([]);

  /** 配置文件枚举列表（从 getConfigItemChanges 返回数据中提取） */
  const confFileList = ref<{ label: string; value: string }[]>([]);

  /** tippy 实例管理 */
  const tippyInstances: Instance[] = [];

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
      text: t('恢复默认'),
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
  };

  /** 是否为新增类型 */
  const isAddType = (opType: string): boolean => opType === 'add' || opType === 'upsert';

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

  /** 初始化操作明细列的 tippy */
  const initChangeTippy = () => {
    tippyInstances.forEach((inst) => inst.destroy());
    tippyInstances.length = 0;

    nextTick(() => {
      const cells = document.querySelectorAll('.config-change-value');
      cells.forEach((el) => {
        const cellEl = el as HTMLElement;
        const rawData = cellEl.dataset.toolTip;
        if (!rawData) return;

        // 解析 JSON 数据
        let data: { after?: string; before?: string; type: string };
        try {
          data = JSON.parse(rawData);
        } catch {
          return;
        }

        // 检查实际文本元素是否溢出（触发了 ellipsis）
        let isOverflow = false;
        if (data.type === 'add') {
          const textEl = cellEl.querySelector('.config-change-value-text') as HTMLElement;
          if (textEl) {
            isOverflow = textEl.scrollWidth > textEl.clientWidth;
          }
        } else if (data.type === 'change') {
          const beforeEl = cellEl.querySelector('.config-change-value-before') as HTMLElement;
          const afterEl = cellEl.querySelector('.config-change-value-after') as HTMLElement;
          const beforeOverflow = beforeEl ? beforeEl.scrollWidth > beforeEl.clientWidth : false;
          const afterOverflow = afterEl ? afterEl.scrollWidth > afterEl.clientWidth : false;
          isOverflow = beforeOverflow || afterOverflow;
        }

        if (!isOverflow) return; // 内容未溢出，不创建 tippy

        if (data.type === 'add') {
          // 新增类型：显示新增的值
          const text = data.after ?? '--';

          const contentEl = document.createElement('div');
          contentEl.className = 'change-tippy-content';

          const titleDiv = document.createElement('div');
          titleDiv.className = 'change-title';
          titleDiv.textContent = `${t('新增：')}`;
          contentEl.appendChild(titleDiv);

          const textDiv = document.createElement('div');
          textDiv.className = 'change-text';
          textDiv.textContent = text;
          contentEl.appendChild(textDiv);

          const instance = dbTippy(cellEl, {
            allowHTML: true,
            appendTo: () => document.body,
            arrow: true,
            content: contentEl,
            hideOnClick: false,
            interactive: false,
            placement: 'top',
            theme: 'light',
            trigger: 'mouseenter focus',
            zIndex: 9999,
          });
          tippyInstances.push(instance);
        } else if (data.type === 'change') {
          // 修改类型：显示 修改前 / 修改后
          const beforeText = data.before ?? '--';
          const afterText = data.after ?? '--';

          const contentEl = document.createElement('div');
          contentEl.className = 'change-tippy-content';

          // 修改前
          const beforeTitleDiv = document.createElement('div');
          beforeTitleDiv.className = 'change-title';
          beforeTitleDiv.textContent = t('修改前：');
          contentEl.appendChild(beforeTitleDiv);

          const beforeTextDiv = document.createElement('div');
          beforeTextDiv.className = 'change-text';
          beforeTextDiv.textContent = beforeText;
          contentEl.appendChild(beforeTextDiv);

          // 修改后（与修改前之间增加间距）
          const afterTitleDiv = document.createElement('div');
          afterTitleDiv.className = 'change-title';
          afterTitleDiv.style.marginTop = '8px';
          afterTitleDiv.textContent = t('修改后：');
          contentEl.appendChild(afterTitleDiv);

          const afterTextDiv = document.createElement('div');
          afterTextDiv.className = 'change-text';
          afterTextDiv.textContent = afterText;
          contentEl.appendChild(afterTextDiv);

          const instance = dbTippy(cellEl, {
            allowHTML: true,
            appendTo: () => document.body,
            arrow: true,
            content: contentEl,
            hideOnClick: false,
            interactive: false,
            placement: 'top',
            theme: 'light',
            trigger: 'mouseenter focus',
            zIndex: 9999,
          });
          tippyInstances.push(instance);
        }
      });
    });
  };

  /** 数据源函数 - 适配 DbTable 组件 */
  const dataSource = async (params: { limit: number; offset: number }) => {
    const defaultConfType = [...new Set(confTabs?.value.map((item) => item.conf_type))].join(',');
    const res = await getConfigItemChanges({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      conf_file: props.confFile || undefined,
      conf_type: props.confType || defaultConfType || undefined,
      level_name: props.levelName || undefined,
      level_value: props.levelValue || undefined,
      namespace: props.clusterType || (activeClusterType?.value as string),
    });

    // 更新枚举列表（配置类型、配置文件）
    updateEnumLists(res.results || []);

    // 前端过滤
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

    // 前端分页
    const start = params.offset;
    const end = start + params.limit;
    const result = {
      count: filteredData.length,
      results: filteredData.slice(start, end),
    };

    return result;
  };

  /** 刷新表格 */
  const refreshTable = () => {
    tableRef.value?.fetchData({}, true);
  };

  /** 自定义排序方法：更新排序状态并重新拉取数据 */
  const handleCustomSort = (sort: TableSort) => {
    if (!Array.isArray(sort) && sort?.sortBy) {
      tableSort.value = { descending: sort.descending, sortBy: sort.sortBy };
    }
    refreshTable();
  };

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

  watch(
    () => confTabs?.value,
    () => {
      refreshTable();
    },
  );

  onUnmounted(() => {
    tippyInstances.forEach((inst) => inst.destroy());
    tippyInstances.length = 0;
  });

  defineExpose({
    fetchData: refreshTable,
  });
</script>

<style lang="less" scoped>
  .operation-record {
    padding: 0 16px;
  }

  .config-change-value {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    position: relative;
    max-width: 100%;
    overflow: hidden;
    vertical-align: middle;

    &.is-add {
      color: #2caf5e;
    }

    &-text {
      display: block;
      flex: 1 1 0;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    &-before,
    &-after {
      flex: 0 1 auto;
      min-width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    &-before {
      color: #f59500;
    }

    &-icon {
      color: #979ba5;
      display: flex;
      flex-shrink: 0;
      width: 14px;
      height: 14px;
      padding: 2px;
      justify-content: center;
      align-items: center;
      gap: 10px;
      aspect-ratio: 1 / 1;
      border-radius: 999px;
      background: var(--neutral-8, #f0f1f5);
    }

    &-after {
      color: #2caf5e;
    }
  }
</style>

<!-- 全局样式：tippy tooltip 内容样式（非 scoped，因为 tippy 挂载到 body） -->
<style lang="less">
  .change-tippy-content {
    max-width: 320px;
    padding: 12px 16px;
    font-size: 12px;
    line-height: 22px;
    color: #63656e;
    word-break: break-word;

    .change-title {
      margin-bottom: 4px;
      font-size: 12px;
      font-weight: 600;
      color: #313238;
      word-break: break-all;
    }

    .change-text {
      font-size: 12px;
      line-height: 22px;
      color: #63656e;
      word-break: break-word;
    }
  }
</style>
