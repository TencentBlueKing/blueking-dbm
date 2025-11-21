<template>
  <div class="recommend-architecture-table">
    <div class="table-head">
      <span>{{ t('架构对比的描述文案') }}</span>
      <div class="color-tip">
        <div class="color-tip-item color-tip-item-advantage">
          <i class="color-tip-item-square" />
          <span class="color-tip-item-name">{{ t('新增') }}</span>
        </div>
        <div class="color-tip-item color-tip-item-disadvantage">
          <i class="color-tip-item-square" />
          <span class="color-tip-item-name">{{ t('更新') }}</span>
        </div>
        <!-- <div class="color-tip-item color-tip-item-developing">
          <i class="color-tip-item-square" />
          <span class="color-tip-item-name">{{ t('开发中') }}</span>
        </div> -->
      </div>
    </div>
    <PrimaryTable
      :data="tableData"
      row-key="attribute"
      :rowspan-and-colspan="rowspanAndColspan">
      <TableColumn
        :class-name="getColumnClassName"
        col-key="attribute"
        :title="t('Tendis 架构')"
        :width="120">
      </TableColumn>
      <TableColumn
        :class-name="getColumnClassName"
        :col-key="ClusterTypes.TWEMPROXY_REDIS_INSTANCE"
        :title="t('TendisCache 集群')">
        <template #title>
          <div>
            <span>{{ t('TendisCache 集群') }}</span>
            <div
              v-if="recommendArchitectrue === ClusterTypes.TWEMPROXY_REDIS_INSTANCE"
              class="recommend-head-tip">
              <div class="tip-text">{{ t('推荐') }}</div>
            </div>
          </div>
        </template>
        <template #default="{ row }: {row: RowData}">
          {{ row.value[ClusterTypes.TWEMPROXY_REDIS_INSTANCE].text }}
        </template>
      </TableColumn>
      <TableColumn
        :class-name="getColumnClassName"
        :col-key="ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE"
        :title="t('TendisSSD 集群')">
        <template #title>
          <div>
            <span>{{ t('TendisSSD 集群') }}</span>
            <div
              v-if="recommendArchitectrue === ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE"
              class="recommend-head-tip">
              <div class="tip-text">{{ t('推荐') }}</div>
            </div>
          </div>
        </template>
        <template #default="{ row }: {row: RowData}">
          {{ row.value[ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE].text }}
        </template>
      </TableColumn>
      <TableColumn
        :class-name="getColumnClassName"
        :col-key="ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER"
        :title="t('Tendisplus 集群')">
        <template #title>
          <div>
            <span>{{ t('Tendisplus 集群') }}</span>
            <div
              v-if="recommendArchitectrue === ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER"
              class="recommend-head-tip">
              <div class="tip-text">{{ t('推荐') }}</div>
            </div>
          </div>
        </template>
        <template #default="{ row }: {row: RowData}">
          {{ row.value[ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER].text }}
        </template>
      </TableColumn>
      <TableColumn
        :class-name="getColumnClassName"
        :col-key="ClusterTypes.PREDIXY_REDIS_CLUSTER"
        :title="t('原生 Redis Cluster')">
        <template #title>
          <div>
            <span>{{ t('原生 Redis Cluster') }}</span>
            <div
              v-if="recommendArchitectrue === ClusterTypes.PREDIXY_REDIS_CLUSTER"
              class="recommend-head-tip">
              <div class="tip-text">{{ t('推荐') }}</div>
            </div>
          </div>
        </template>
        <template #default="{ row }: {row: RowData}">
          {{ row.value[ClusterTypes.PREDIXY_REDIS_CLUSTER].text }}
        </template>
      </TableColumn>
    </PrimaryTable>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { BaseTableCol } from '@blueking/tdesign-ui';

  import { ClusterTypes } from '@common/const';

  import { type RowData, tableData } from './common/tabelData';

  interface Props {
    recommendArchitectrue: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const getColumnClassName = ({
    col,
    colIndex,
    row,
    rowIndex,
  }: {
    col: BaseTableCol<RowData>;
    colIndex: number;
    row: RowData;
    rowIndex: number;
  }) => {
    if (!row.value) {
      return props.recommendArchitectrue === col.colKey ? ['head-cell'] : [];
    }

    const classList: string[] = [];

    if (col.colKey === 'attribute') {
      classList.push('attribute-cell');
    } else if (row.value[col.colKey as string].type) {
      classList.push(`${row.value[col.colKey as string].type}-cell`);
    }

    if (props.recommendArchitectrue === (col.colKey as string) && rowIndex !== tableData.length - 1) {
      classList.push('recommend-cell');
      if (rowIndex === tableData.length - 2) {
        classList.push('recommend-cell-last-row');
      }
    }

    if (rowIndex === tableData.length - 1 && colIndex > 1) {
      classList.push('colspan-row');
    }

    classList.push('text-line-feed');

    return classList;
  };

  const rowspanAndColspan = ({ colIndex, rowIndex }: { colIndex: number; rowIndex: number }) => {
    if (rowIndex === tableData.length - 1 && colIndex === 1) {
      return {
        colspan: 4,
        rowspan: 1,
      };
    }
    return {};
  };
</script>

<style lang="less">
  .recommend-architecture-table {
    .table-head {
      display: flex;
      margin-bottom: 16px;
      font-size: 12px;
      color: #63656e;
      align-items: center;

      .color-tip {
        display: flex;
        align-items: center;
        margin-left: auto;

        .color-tip-item {
          display: flex;
          align-items: center;
          margin-left: 24px;
        }

        .color-tip-item-square {
          width: 12px;
          height: 12px;
          border: 1px solid transparent;
        }

        .color-tip-item-name {
          padding: 0 4px;
        }

        .color-tip-item-advantage {
          .color-tip-item-square {
            background-color: #f2fff4;
            border-color: #b3ffc1;
          }
        }

        .color-tip-item-disadvantage {
          .color-tip-item-square {
            background-color: #fee;
            border-color: #ff5656;
          }
        }

        .color-tip-item-developing {
          .color-tip-item-square {
            background-color: #fff4e2;
            border-color: #ffdfac;
          }
        }
      }
    }

    .head-cell {
      border: solid 2px #1cab88;
      border-bottom: none;
    }

    .attribute-cell {
      color: #313238 !important;
      background-color: #f5f7fa;
    }

    .advantage-cell {
      background-color: #f2fff4;
    }

    .disadvantage-cell {
      background-color: #fee;
    }

    .developing-cell {
      background-color: #fff4e2;
    }

    .recommend-cell {
      border-right: solid 2px #1cab88;
      border-left: solid 2px #1cab88;
    }

    .recommend-cell-last-row {
      border-bottom: solid 2px #1cab88;
    }

    .recommend-head {
      border: solid 2px #1cab88;
      border-bottom: none;
    }

    .recommend-head-tip {
      position: absolute;
      top: 0;
      right: 0;
      width: 30%;

      .tip-text {
        height: 28px;
        padding: 0 4px;
        line-height: 28px;
        color: #fff;
        text-align: center;
        background: #1cab88;
        // border-radius: 4px 4px 0 0;
      }
    }

    .text-line-feed {
      white-space: pre-line;
    }
  }
</style>
