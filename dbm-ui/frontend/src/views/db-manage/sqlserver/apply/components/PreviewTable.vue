<template>
  <DbOriginalTable
    :cell-class="setCellClass"
    class="preview-table"
    :columns="columns"
    :data="data"
    :max-height="maxHeight"
    v-bind="$attrs" />
</template>

<script setup lang="tsx">
  import type { Table } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  type TableProps = InstanceType<typeof Table>['$props'];

  interface Props {
    data: {
      charset: string;
      deployStructure: string;
      disasterDefence: string;
      domain: string;
      slaveDomain: string;
      version: string;
    }[];
    isShowNodes?: boolean;
    isSingleType?: boolean;
    maxHeight?: number;
    nodeList: {
      bk_cloud_id: number;
      bk_host_id: number;
      ip: string;
    }[];
  }

  const props = withDefaults(defineProps<Props>(), {
    isShowNodes: true,
    isSingleType: false,
    maxHeight: 436,
  });

  const { t } = useI18n();

  const columns = computed(() => {
    if (props.isSingleType) {
      const singleColumns: TableProps['columns'] = [
        {
          field: 'domain',
          label: t('主访问入口'),
          showOverflowTooltip: true,
        },
        {
          field: 'deployStructure',
          label: t('部署架构'),
          showOverflowTooltip: true,
        },
        {
          field: 'version',
          label: t('数据库版本'),
          showOverflowTooltip: true,
        },
        {
          field: 'charset',
          label: t('字符集'),
          showOverflowTooltip: true,
        },
      ];
      if (props.isShowNodes) {
        singleColumns.push({
          field: 'backend',
          label: t('服务器'),
          render: () => {
            const { nodeList } = props;
            return (
              <div class='host-list'>
                <div class='host-list-wrapper'>
                  {nodeList.map((item) => (
                    <div class='host-list-item'>
                      <span class='host-list-tag host-list-tag-master'></span>
                      <span class='host-list-ip'>{item.ip}</span>
                    </div>
                  ))}
                </div>
              </div>
            );
          },
          rowspan: () => props.data.length || 1,
          width: 200,
        });
      }
      return singleColumns;
    }
    const haColumns: TableProps['columns'] = [
      {
        field: 'domain',
        label: t('主访问入口'),
        showOverflowTooltip: true,
      },
      {
        field: 'slaveDomain',
        label: t('从访问入口'),
        showOverflowTooltip: true,
      },
      {
        field: 'deployStructure',
        label: t('部署架构'),
        showOverflowTooltip: true,
      },
      {
        field: 'version',
        label: t('数据库版本'),
        showOverflowTooltip: true,
      },
      {
        field: 'charset',
        label: t('字符集'),
        showOverflowTooltip: true,
      },
    ];
    return haColumns;
  });

  const setCellClass = ({ field }: { field: string }) => ('backend' === field ? 'host-td' : '');
</script>

<style lang="less" scoped>
  .preview-table {
    :deep(.bk-vxe-table) {
      td {
        position: relative;

        &.host-td .vxe-cell {
          height: 100% !important;
          padding: 0;
          line-height: normal !important;
        }
      }

      .host-list {
        height: 100%;
        text-align: center;

        .host-list-wrapper {
          position: relative;
          top: 50%;
          display: inline-block;
          transform: translateY(-50%);
        }

        .host-list-group {
          display: flex;
          align-items: center;
        }

        .host-list-item {
          display: flex;
          align-items: center;
          min-width: 130px;
          line-height: 32px;
        }

        .host-list-tag {
          width: 16px;
          height: 16px;
          margin-right: 4px;
          font-size: @font-size-mini;
          font-weight: bolder;
          line-height: 16px;
          text-align: center;

          .host-list-proxy {
            color: #ff9c01;
            background-color: #ffe8c3;
          }

          .host-list-master {
            color: @primary-color;
            background-color: #cad7eb;
          }

          .host-list-slave {
            color: #2dcb56;
            background-color: #c8e5cd;
          }
        }
      }
    }
  }
</style>
