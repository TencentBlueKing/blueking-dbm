<template>
  <DbSideslider
    :is-show="modelValue"
    :title="t(`执行前检查`)"
    :width="1000"
    @closed="handleCancel">
    <div class="partition-dry-run">
      <DbSearchSelect
        v-model="searchValues"
        class="mb-16"
        :data="serachData"
        :placeholder="t('请输入 DB 名、表名')"
        style="width: 490px;"
        unique-select />
      <BkLoading :loading="isLoading">
        <BkTable
          class="execute-bable"
          :columns="tableColumns"
          :data="renderTableData" />
      </BkLoading>
    </div>
    <template #footer>
      <BkButton
        :loading="isExecSubmiting"
        theme="primary"
        @click="handleExec">
        {{ t('确认执行') }}
      </BkButton>
      <BkButton
        class="ml-8"
        :disabled="isExecSubmiting"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </DbSideslider>
</template>
<script setup lang="tsx">
  import {
    shallowRef,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type PartitionModel from '@services/model/partition/partition';
  import {
    dryRun,
    execute,
  } from '@services/partitionManage';

  import { useTicketMessage } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import {
    downloadText,
    encodeRegexp,
    execCopy,
    getSearchSelectorParams,
  } from '@utils';

  interface Props {
    data?: PartitionModel
  }

  interface ITableData {
    dblike: string,
    tblike: string,
    action: string[],
    message: string,
    sql: string[],
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<boolean>({
    default: false,
  });
  const { t } = useI18n();
  const ticketMessage = useTicketMessage();

  const isExecSubmiting = ref(false);
  const searchValues = ref([]);
  const tableData = shallowRef<ITableData[]>([]);

  let partitionObjectsMemo: Record<string, unknown>;

  const renderTableData = computed(() => {
    if (searchValues.value.length < 1) {
      return tableData.value;
    }
    const serachParams = getSearchSelectorParams(searchValues.value);

    const serachRegMap = Object.keys(serachParams).reduce((result, key) => Object.assign({}, result, {
      [key]: new RegExp(`${encodeRegexp(serachParams[key])}`, 'i'),
    }), {} as Record<string, RegExp>);

    return tableData.value.filter(tableDataItem => Object.keys(serachParams)
      .every((searchParamKey) => {
        const tableColumnData = tableDataItem[searchParamKey as keyof ITableData];
        const tableColumnValue = Array.isArray(tableColumnData) ? tableColumnData : [tableColumnData];

        return tableColumnValue.every(value => serachRegMap[searchParamKey].test(value));
      }));
  });

  const serachData = [
    {
      name: t('DB 名'),
      id: 'dblike',
    },
    {
      name: t('表名'),
      id: 'tblike',
    },
  ];

  const renderActionColumn = (data: ITableData) => {
    const len = data.action.length;
    const showTag = len > 1;
    // data.action 最多两个值，最少一个值
    return (
      <div class="action-box">
        <bk-tag style="margin-right:0;">{ data.action[0] }</bk-tag>
        {showTag && <bk-popover placement="top" theme="dark">
            {{
              default: () => <bk-tag class="tag-box">{`+${len - 1}`}</bk-tag>,
              content: () => <div>{data.action[1]}</div>,
            }}
        </bk-popover>}
      </div>);
  };

  const tableColumns = [
    {
      label: t('DB 名'),
      field: 'dblike',
    },
    {
      label: t('表名'),
      field: 'tblike',
    },
    {
      label: t('检查状态'),
      field: 'status',
      render: ({ data }: {data: ITableData}) => {
        if (data.message) {
          return (
            <div>
              <db-icon
                style="vertical-align: middle;"
                type='sync-failed'
                svg />
              <span class="ml-4">{t('失败')}</span>
            </div>
          );
        }
        return (
            <div>
              <db-icon
                style="vertical-align: middle;"
                type='sync-success'
                svg />
              <span class="ml-4">{t('成功')}</span>
            </div>
        );
      },
    },
    {
      label: t('结果说明'),
      field: 'message',
      showOverflowTooltip: true,
      render: ({ data }: {data: ITableData}) => <span>{data.message || '--'}</span>,
    },
    {
      label: t('分区动作'),
      field: 'action',
      width: 138,
      showOverflowTooltip: false,
      render: ({ data }: {data: ITableData}) => renderActionColumn(data),
    },
    {
      label: t('分区 SQL'),
      minWidth: 140,
      fixed: 'right',
      render: ({ data }: {data: ITableData}) => (
        <div class="sql-box">
          <db-icon type='sql' />
          <span class="ml-4">testsql</span>
          <bk-button
            v-bk-tooltips={t('复制 SQL')}
            class="copy-btn ml-4"
            text
            theme="primary"
            onClick={() => handleCopySql(data.sql)}>
            <db-icon type='copy' />
          </bk-button>
          <bk-button
            v-bk-tooltips={t('下载 SQL 文件')}
            class="download-btn ml-4"
            text
            theme="primary"
            onClick={() => handleDownloadSql(data.sql)}>
            <db-icon type='import' />
          </bk-button>
        </div>
      ),
    },
  ];

  const {
    loading: isLoading,
    run: fetchDryRun,
  } = useRequest(dryRun, {
    manual: true,
    onSuccess(data) {
      if (Object.values(data).length < 1) {
        return;
      }

      partitionObjectsMemo = data;

      const detailList = Object.values(data)[0];

      tableData.value = detailList.reduce((result, recordItem) => {
        const { message } = recordItem;
        recordItem.execute_objects.forEach((executeItem) => {
          const dataObj = {
            dblike: executeItem.dblike,
            tblike: executeItem.tblike,
            message,
            action: [] as string[],
            sql: [] as string[],
          };
          if (executeItem.init_partition.length > 0) {
            dataObj.action.push(t('初始化分区'));
            dataObj.sql.push(...executeItem.init_partition.map(sqlItem => sqlItem.sql));
          }
          if (executeItem.add_partition.length > 0) {
            dataObj.action.push(t('增加分区'));
            dataObj.sql.push(...executeItem.add_partition);
          }
          if (executeItem.drop_partition.length > 0) {
            dataObj.action.push(t('删除分区'));
            dataObj.sql.push(...executeItem.drop_partition);
          }
          result.push(dataObj);
        });
        return result;
      }, [] as ITableData[]);
    },
  });

  const fetchData = () => {
    if (!props.data) {
      return;
    }
    fetchDryRun({
      config_id: props.data.id,
      cluster_id: props.data.cluster_id,
      cluster_type: ClusterTypes.SPIDER,
    });
  };

  watch(() => props.data, () => {
    fetchData();
  }, {
    immediate: true,
  });

  const handleCopySql = (sqlList: string[]) => {
    execCopy(sqlList.join('\n\n\n'));
  };

  const handleDownloadSql = (sqlList: string[]) => {
    downloadText('testsql.sql', sqlList.join('\n\n\n'));
  };

  const handleExec = () => {
    if (!props.data) {
      return;
    }
    isExecSubmiting.value = true;
    execute({
      cluster_id: props.data.cluster_id,
      partition_objects: partitionObjectsMemo,
    })
      .then((data) => {
        ticketMessage(data.id);
      })
      .finally(() => {
        isExecSubmiting.value = false;
      });
  };

  const handleCancel = () => {
    modelValue.value = false;
  };
</script>
<style lang="less">
.partition-dry-run {
  padding: 16px 24px;

  .bk-table{
    tr{
      &:hover{
        .copy-btn,
        .download-btn{
          display: inline-block;
        }
      }
    }
  }

  .sql-box{
    color: #3A84FF;

    .copy-btn,
    .download-btn{
      display: none;
    }
  }
}

.execute-bable {
  :deep(.action-box) {
    display: flex;
    width: 100%;
    overflow: hidden;
    align-items: center;

    .tag-box{
      padding: 0 6px;
      margin-left: 4px;
      transform: scale(0.83, 0.83);
    }
  }

}
</style>
