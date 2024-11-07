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
    <BkTable
      :cell-class="setCellClass"
      class="table-content"
      :columns="columns"
      :data="tableData"
      height="100%"
      row-hover="auto"
      show-overflow-tooltip>
    </BkTable>
  </div>
</template>

<script setup lang="tsx">
  import type { Column } from 'bkui-vue/lib/table/props';
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes } from '@common/const';

  import { type RowData, tableData } from './common/tabelData';

  interface Props {
    recommendArchitectrue: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const columns = [
    {
      label: t('Tendis 架构'),
      field: 'attribute',
      resizable: false,
    },
    {
      field: ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
      className: (row: RowData) => !row && props.recommendArchitectrue === ClusterTypes.TWEMPROXY_REDIS_INSTANCE ? 'recommend-head' : '',
      renderHead: () => (
        <>
          <span>{t('TendisCache 集群')}</span>
          {
            props.recommendArchitectrue === ClusterTypes.TWEMPROXY_REDIS_INSTANCE && (
              <div class="recommend-head-tip">
                <div class="tip-text">{t('推荐')}</div>
              </div>
            )
          }
        </>
      ),
      colspan: ({ rowIndex}: { rowIndex: number }) => rowIndex === tableData.length - 1 ? 4 : 1,
      render: ({ data }: { data: RowData }) => data.value[ClusterTypes.TWEMPROXY_REDIS_INSTANCE].text,
    },
    {
      field: ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
      className: (row: RowData) => !row && props.recommendArchitectrue === ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE ? 'recommend-head' : '',
      renderHead: () => (
        <>
          <span>{t('TendisSSD 集群')}</span>
          {
            props.recommendArchitectrue === ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE && (
              <div class="recommend-head-tip">
                <div class="tip-text">{t('推荐')}</div>
              </div>
            )
          }
        </>
      ),
      render: ({ data }: { data: RowData }) => data.value[ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE].text,
    },
    {
      field: ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
      className: (row: RowData) => !row && props.recommendArchitectrue === ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER ? 'recommend-head' : '',
      renderHead: () => (
        <>
          <span>{t('Tendisplus 集群')}</span>
          {
            props.recommendArchitectrue === ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER && (
              <div class="recommend-head-tip">
                <div class="tip-text">{t('推荐')}</div>
              </div>
            )
          }
        </>
      ),
      render: ({ data }: { data: RowData }) => data.value[ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER].text,
    },
    {
      field: ClusterTypes.PREDIXY_REDIS_CLUSTER,
      className: (row: RowData) => !row && props.recommendArchitectrue === ClusterTypes.PREDIXY_REDIS_CLUSTER ? 'recommend-head' : '',
      renderHead: () => (
        <>
          <span>{t('原生 Redis Cluster')}</span>
          {
            props.recommendArchitectrue === ClusterTypes.PREDIXY_REDIS_CLUSTER && (
              <div class="recommend-head-tip">
                <div class="tip-text">{t('推荐')}</div>
              </div>
            )
          }
        </>
      ),
      render: ({ data }: { data: RowData }) => data.value[ClusterTypes.PREDIXY_REDIS_CLUSTER].text,
    },
  ];

  const setCellClass = (column: Column, colIndex: number, row: RowData, rowIndex: number) => {
    const classList = [];

    if (column.field === 'attribute') {
      classList.push('attribute-cell');
    } else if (row.value[column.field as string].type) {
      classList.push(`${row.value[column.field as string].type}-cell`);
    }

    if (props.recommendArchitectrue === column.field as string && rowIndex !== tableData.length - 1) {
      classList.push('recommend-cell');
      if (rowIndex === tableData.length - 2) {
        classList.push('recommend-cell-last-row')
      }
    }

    if (rowIndex === tableData.length - 1 && colIndex > 1 ) {
      classList.push('colspan-row')
    }

    return classList;
  };
</script>

<style lang="less" scoped>
  .recommend-architecture-table {
    .table-head {
      display: flex;
      align-items: center;
      font-size: 12px;
      color: #63656e;
      margin-bottom: 16px;

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
            background-color: #ffeeee;
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

    :deep(.attribute-cell) {
      background-color: #f5f7fa;
      color: #313238 !important;
    }

    :deep(.advantage-cell) {
      background-color: #f2fff4;
    }

    :deep(.disadvantage-cell) {
      background-color: #ffeeee;
    }

    :deep(.developing-cell) {
      background-color: #fff4e2;
    }

    :deep(.recommend-cell) {
      border-left: solid 2px #1cab88;
      border-right: solid 2px #1cab88;
    }

    :deep(.recommend-cell-last-row) {
      border-bottom: solid 2px #1cab88;
    }

    :deep(.recommend-head) {
      border: solid 2px #1cab88;
      border-bottom: none;
    }

    :deep(.recommend-head-tip) {
      position: absolute;
      right: 0;
      top: 0;
      width: 30%;

      .tip-text {
        color: #ffffff;
        height: 28px;
        padding: 0 4px;
        text-align: center;
        line-height: 28px;
        background: #1cab88;
        // border-radius: 4px 4px 0 0;
      }
    }

    :deep(.colspan-row) {
      display: none;
    }

    :deep(.bk-table) {
      .vxe-cell {
        white-space: break-spaces;
        line-height: 20px;
        padding: 8px 16px;
      }
    }
  }
</style>
