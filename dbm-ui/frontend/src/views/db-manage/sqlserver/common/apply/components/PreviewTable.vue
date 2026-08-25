<template>
  <PrimaryTable
    class="preview-table"
    :columns="columns"
    :data="data"
    :max-height="maxHeight"
    row-key="domain"
    :rowspan-and-colspan="rowspanAndColspan"
    v-bind="$attrs" />
</template>

<script setup lang="tsx">
  import type { PrimaryTableCol, PrimaryTableProps } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';

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
      const singleColumns: PrimaryTableCol[] = [
        {
          colKey: 'domain',
          ellipsis: true,
          title: t('主访问入口'),
        },
        {
          colKey: 'deployStructure',
          ellipsis: true,
          title: t('部署架构'),
        },
        {
          colKey: 'version',
          ellipsis: true,
          title: t('数据库版本'),
        },
        {
          colKey: 'charset',
          ellipsis: true,
          title: t('字符集'),
        },
      ];
      if (props.isShowNodes) {
        singleColumns.push({
          cell: () => {
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
          className: 'host-td',
          colKey: 'backend',
          title: t('服务器'),
          width: 200,
        });
      }
      return singleColumns;
    }
    const haColumns: PrimaryTableCol[] = [
      {
        colKey: 'domain',
        ellipsis: true,
        title: t('主访问入口'),
      },
      {
        colKey: 'slaveDomain',
        ellipsis: true,
        title: t('从访问入口'),
      },
      {
        colKey: 'deployStructure',
        ellipsis: true,
        title: t('部署架构'),
      },
      {
        colKey: 'version',
        ellipsis: true,
        title: t('数据库版本'),
      },
      {
        colKey: 'charset',
        ellipsis: true,
        title: t('字符集'),
      },
    ];
    return haColumns;
  });

  const rowspanAndColspan: PrimaryTableProps['rowspanAndColspan'] = ({ col, rowIndex }) => {
    if (col.colKey === 'backend' && rowIndex === 0) {
      return {
        rowspan: props.data.length || 1,
      };
    }
    return {};
  };
</script>

<style lang="less" scoped>
  .preview-table {
    :deep(.t-table) {
      td {
        position: relative;

        &.host-td {
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
