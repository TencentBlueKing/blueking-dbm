<template>
  <FlowCollapse
    v-if="abstractList.length"
    :title="t('交付结果')">
    <template #header>
      <span class="table-title">{{ t('交付结果') }}</span>
      <!-- header 整块是折叠触发区，点导出不能顺带折叠面板 -->
      <BkButton
        v-if="exportableList.length"
        class="ml-8"
        size="small"
        @click.stop="handleExport">
        {{ t('导出') }}
      </BkButton>
    </template>
    <div class="flow-abstract-main">
      <BkCollapse
        v-for="(item, index) in abstractList"
        :key="index"
        v-model="activeIndex"
        class="table-collapse-main">
        <BkCollapsePanel :name="String(index)">
          <template #header>
            <div class="collapse-panel-header">
              <span class="panel-title">
                {{ item.table_display_name || item.table_name }}
              </span>
              <DbIcon
                :class="{ 'active-icon': !activeIndex.includes(String(index)) }"
                type="down-big" />
            </div>
          </template>
          <template #content>
            <TicketInfoTable
              :data="item.values"
              header-row-class-name="abstract-table-header-row"
              :row-key="item.titles[0].field">
              <TicketInfoTableColumn
                v-for="titleItem in item.titles"
                :key="titleItem.field"
                :col-key="titleItem.field"
                :get-copy-value="titleItem.field === 'ip' ? (row) => row.ip : undefined"
                :title="titleItem.label">
                <template #default="{ row }">
                  <a
                    v-if="titleItem.type === 'url' && isHttpUrl(row[titleItem.field])"
                    :href="row[titleItem.field]"
                    target="_blank">
                    {{ titleItem.label }}
                  </a>
                  <span v-else-if="titleItem.type === 'url'"> -- </span>
                  <span v-else>
                    {{ row[titleItem.field] || '--' }}
                  </span>
                </template>
              </TicketInfoTableColumn>
            </TicketInfoTable>
            <div
              v-if="item.remark"
              class="mt-4">
              {{ item.remark }}
            </div>
          </template>
        </BkCollapsePanel>
      </BkCollapse>
    </div>
  </FlowCollapse>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';
  import * as XLSX from 'xlsx';

  import FlowMode from '@services/model/ticket/flow';
  import TicketModel from '@services/model/ticket/ticket';

  import {
    createWorkSheet as createBaseWorkSheet,
    downloadWorkBook,
  } from '@views/ticket-center/common/ticket-detail/components/flow-info/utils/exportWorkBook';

  import { isHttpUrl } from '@utils';

  import FlowCollapse from '../FlowCollapse.vue';

  interface Props {
    data: FlowMode<unknown, any>;
    ticketDetail?: TicketModel<unknown>;
  }

  type OutputTable = FlowMode['output_data'][number];

  const props = defineProps<Props>();

  const { t } = useI18n();

  // Excel 对 Sheet 名的限制：最长 31 个字符，不能包含 : \ / ? * [ ]
  const SHEET_NAME_MAX_LENGTH = 31;
  const SHEET_NAME_ILLEGAL_REG = /[:\\/?*[\]]/g;

  const activeIndex = ref<string[]>([]);

  const abstractList = computed(() => {
    if (!props.data.output_data.length) {
      return [];
    }

    return props.data.output_data
      .filter((item) => !item.hidden)
      .map((item) => {
        return {
          ...item,
          titles: item.titles.map((item) => ({
            field: item.id,
            label: item.display_name,
            type: item.type,
          })),
        };
      });
  });

  // 可导出的表：可见且有数据，顺序与页面一致；为空时不展示导出按钮
  const exportableList = computed(() =>
    props.data.output_data.filter(
      (item) => !item.hidden && Array.isArray(item.titles) && Array.isArray(item.values) && item.values.length > 0,
    ),
  );

  // 单元格写完整原始值，空值留空单元格（不沿用页面的 -- 占位），对象类值序列化输出
  const getCellValue = (value: unknown) => {
    if (value === null || value === undefined || value === '') {
      return null;
    }
    if (typeof value === 'object') {
      return JSON.stringify(value);
    }
    return value;
  };

  // 拼 Sheet 名：重名时追加（n），截断基础名保证总长不超过 Excel 上限
  const buildSheetName = (baseName: string, index: number) => {
    const suffix = index > 1 ? `（${index}）` : '';
    return `${baseName.slice(0, SHEET_NAME_MAX_LENGTH - suffix.length)}${suffix}`;
  };

  const getSheetNames = (list: OutputTable[]) => {
    // Excel 判断 Sheet 重名不区分大小写，按小写记录已用名称
    const usedNames = new Set<string>();
    const nameCountMap = new Map<string, number>();
    return list.map((item) => {
      const baseName = (item.table_display_name || item.table_name || 'Sheet').replace(SHEET_NAME_ILLEGAL_REG, '_');
      const count = (nameCountMap.get(baseName) || 0) + 1;
      nameCountMap.set(baseName, count);
      // 截断后可能和其他表撞名，继续递增序号直到唯一
      let index = count;
      let sheetName = buildSheetName(baseName, index);
      while (usedNames.has(sheetName.toLowerCase())) {
        index += 1;
        sheetName = buildSheetName(baseName, index);
      }
      usedNames.add(sheetName.toLowerCase());
      return sheetName;
    });
  };

  const createWorkSheet = (table: OutputTable) => {
    const header = table.titles.map((title) => title.display_name);
    const rows = table.values.map((row) =>
      table.titles.map((title) => {
        const value = row[title.id];
        // url 列与页面一致：有效地址显示列名，链接在生成 sheet 后补上；无效地址留空
        if (title.type === 'url') {
          return isHttpUrl(value) ? title.display_name : null;
        }
        return getCellValue(value);
      }),
    );
    const workSheet = createBaseWorkSheet([header, ...rows]);

    table.values.forEach((row, rowIndex) => {
      table.titles.forEach((title, colIndex) => {
        const value = row[title.id];
        if (title.type !== 'url' || !isHttpUrl(value)) {
          return;
        }
        // 首行是表头，数据行从第 2 行开始
        const cell = workSheet[XLSX.utils.encode_cell({ c: colIndex, r: rowIndex + 1 })];
        if (cell) {
          cell.l = { Target: value };
        }
      });
    });

    return workSheet;
  };

  const handleExport = () => {
    const list = exportableList.value;
    const sheetNames = getSheetNames(list);
    const workBook = XLSX.utils.book_new();
    list.forEach((table, index) => {
      XLSX.utils.book_append_sheet(workBook, createWorkSheet(table), sheetNames[index]);
    });

    const ticketTypeName = props.ticketDetail?.ticket_type_display || props.data.ticket_type;
    const ticketId = props.ticketDetail?.id || props.data.ticket;
    const fileName = `${ticketTypeName}_${ticketId}_${t('交付结果')}_${dayjs().format('YYYYMMDD')}.xlsx`;

    downloadWorkBook(workBook, fileName);
  };

  watch(
    abstractList,
    (list) => {
      activeIndex.value = list.map((_, index) => String(index));
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less">
  .flow-abstract-main {
    display: flex;
    width: 100%;
    padding-left: 16px;
    background: #f5f7fa;
    flex-direction: column;
    gap: 16px;

    .table-collapse-main {
      .collapse-panel-header {
        position: relative;
        display: flex;
        height: 28px;
        padding: 0 12px 0 16px;
        color: #313238;
        cursor: pointer;
        background: #f0f1f5;
        align-items: center;
        justify-content: space-between;

        .db-icon-down-shape {
          color: #979ba5;
          transform: rotateZ(0deg);
          transition: all 0.5s;
        }

        .panel-title {
          font-size: 12px;
          font-weight: 700;
        }

        .active-icon {
          transform: rotateZ(-90deg);
          transition: all 0.5s;
        }
      }

      .bk-collapse-content {
        padding: 0;
      }
    }

    .item-main {
      width: 100%;

      .title-main {
        font-size: 14px;
        font-weight: 700;
        color: #313238;
      }

      .table-main {
        padding: 12px 10px 0;
      }
    }
  }

  .abstract-table-header-row {
    background-color: #fafbfd;
  }
</style>
