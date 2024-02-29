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
  import { useI18n } from 'vue-i18n';

  import type { TableProps } from '@/types/bkui-vue';

  interface Props {
    data: {
      domain:string,
      slaveDomain:string,
      disasterDefence:string,
      deployStructure:string,
      version:string,
      charset:string,
    }[],
    nodes:{
      backend: {
        ip: string,
        bk_host_id: number,
        bk_cloud_id: number
      }[]
    }
    isShowNodes?: boolean,
    isSingleType?: boolean,
    maxHeight?: number
  }

  const props = withDefaults(defineProps<Props>(), {
    data: () => [],
    nodes: () => ({
      backend: [],
    }),
    isShowNodes: true,
    isSingleType: false,
    maxHeight: 436,
  });

  const { t } = useI18n();

  const columns = computed(() => {
    if (props.isSingleType) {
      const singleColumns: TableProps['columns'] = [
        {
          label: t('主访问入口'),
          field: 'domain',
          showOverflowTooltip: true,
        },
        {
          label: t('部署架构'),
          field: 'deployStructure',
          showOverflowTooltip: true,
        },
        {
          label: t('数据库版本'),
          field: 'version',
          showOverflowTooltip: true,
        },
        {
          label: t('字符集'),
          field: 'charset',
          showOverflowTooltip: true,
        },
      ];
      if (props.isShowNodes) {
        singleColumns.push({
          label: t('服务器'),
          field: 'backend',
          width: 200,
          rowspan: () => props.data.length || 1,
          render: () => {
            const hosts = props.nodes.backend;
            return (
              <div class="host-list">
                <div class="host-list-wrapper">
                  {
                    hosts.map(item => (
                      <div class="host-list-item">
                        <span class='host-list-tag host-list-tag-master'></span>
                        <span class="host-list-ip">{ item.ip }</span>
                      </div>
                    ))
                  }
                </div>
              </div>
            );
          },
        });
      }
      return singleColumns;
    }
    const haColumns: TableProps['columns'] = [
      {
        label: t('主访问入口'),
        field: 'domain',
        showOverflowTooltip: true,
      },
      {
        label: t('从访问入口'),
        field: 'slaveDomain',
        showOverflowTooltip: true,
      },
      {
        label: t('部署架构'),
        field: 'deployStructure',
        showOverflowTooltip: true,
      },
      {
        label: t('数据库版本'),
        field: 'version',
        showOverflowTooltip: true,
      },
      {
        label: t('字符集'),
        field: 'charset',
        showOverflowTooltip: true,
      },
    ];
    return haColumns;
  });

  const setCellClass = ({ field }: { field: string }) => ('backend' === field ? 'host-td' : '');

</script>

<style lang="less" scoped>
.preview-table {
  :deep(.bk-table-body) {
    td {
      position: relative;

      &.host-td .cell {
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
