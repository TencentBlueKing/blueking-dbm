<template>
  <BkLoading
    class="render-dynamic-table"
    :loading="loading">
    <BlockCard>
      <template #title>
        <span>{{ tableName }}</span>
        <span>（{{ pagination.count }}）</span>
      </template>
      <BkTable
        :columns="tableColumns"
        :data="tableData"
        header-row-class-name="dynamic-table-head"
        :pagination="pagination"
        @page-limit-change="pageLimitChange"
        @page-value-change="pageValueChange">
        <template #empty>
          <slot name="empty">
            <BkException
              :description="t('搜索结果为空')"
              scene="part"
              type="empty" />
          </slot>
        </template>
      </BkTable>
    </BlockCard>
    <FailSlaveInstance
      :id="failSlaveInstanceReportId"
      v-model="isShowFailSlaveInstance" />
  </BkLoading>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getReport } from '@services/source/report';

  import { useGlobalBizs } from '@stores';

  import DbStatus from '@components/db-status/index.vue';

  import { utcDisplayTime } from '@utils';

  import BlockCard from './components/BlockCard.vue';
  import FailSlaveInstance from './components/FailSlaveInstance.vue';

  interface Props {
    searchParams?: Record<string, any>,
    isPlatform?: boolean;
    serviceUrl: string;
  }

  interface Exposes {
    getExportExcelSheetData: () => Promise<{
      headerList: string[];
      colWidthList: { wch: number }[];
      fileName: string;
      dataList: string[][];
    }>;
  }

  const props = withDefaults(defineProps<Props>(), {
    searchParams: undefined,
    isPlatform: false,
  });

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();

  const pagination = reactive({
    count: 0,
    current: 1,
    limit: 10,
    remote: true,
  });

  const tableName = ref('');
  const isShowFailSlaveInstance = ref(false);
  const failSlaveInstanceReportId = ref(0);

  const tableColumns = shallowRef<{label: string, render:(data: any) => any }[]>([]);
  const tableData = shallowRef<any[]>([]);

  const bizsMap = computed(() => globalBizsStore.bizs.reduce<Record<number, string>>((results, item) => {
    Object.assign(results, {
      [item.bk_biz_id]: item.name,
    })
    return results;
  }, {}));

  const {
    loading,
    run: fetchInspectionData,
  } = useRequest(getReport, {
    manual: true,
    onSuccess(result) {
      pagination.count = result.count;
      tableName.value = result.name;

      tableColumns.value = result.title.map(titleItem => ({
        label: titleItem.display_name,
        showOverflow: "tooltip",
        render: ({ data: fieldData }: {data:any}) => {
          const fieldValue = fieldData[titleItem.name];
          if (titleItem.format === 'status') {
            const isSuccess = fieldValue === true;
            return (
              <DbStatus theme={isSuccess ? 'success' : 'danger'}>
                { isSuccess ? t('成功') : t('失败') }
              </DbStatus>
            );
          }
          if (titleItem.format === 'fail_slave_instance') {
            return (
              <bk-button
                text
                theme="primary"
                onClick={() => handleShowFailSlaveInstance(fieldData)}>
                {fieldData[titleItem.name]}
              </bk-button>
            );
          }
          if (titleItem.name === 'create_at') {
            return utcDisplayTime(fieldData[titleItem.name]);
          }
          if (titleItem.name === 'bk_biz_id') {
            return bizsMap.value[fieldValue] || fieldValue;
          }
          return fieldData[titleItem.name] || '--';
        },
      }));

      tableData.value = result.results;
    },
  });

  const fetchData = () => {
    fetchInspectionData(props.serviceUrl, {
      offset: (pagination.current - 1) * pagination.limit,
      limit: pagination.limit,
      platform: props.isPlatform,
      ...props.searchParams,
    }, {
      permission: 'page',
    });
  };

  watch(() => props.searchParams, () => {
    fetchData();
  }, {
    immediate: true,
  });

  const handleShowFailSlaveInstance = (data: any) => {
    isShowFailSlaveInstance.value = true;
    failSlaveInstanceReportId.value = data.id;
  };

  const pageLimitChange = (pageLimit: number) => {
    if (pagination.limit === pageLimit){
      return
    }

    pagination.limit = pageLimit;
    pagination.current = 1;
    fetchData();
  };

  const pageValueChange = (pageValue:number) => {
    if (pagination.current === pageValue) {
      return
    }

    pagination.current = pageValue;
    fetchData();
  };

  defineExpose<Exposes>({
    async getExportExcelSheetData() {
      const { results, title, name: fileName } = await getReport(props.serviceUrl, {
        offset: 0,
        limit: -1,
        platform: props.isPlatform,
        ...props.searchParams,
      }, {
        permission: 'page',
      });
      const headerList: string[] = [];
      const columnIds: string[] = [];
      title.forEach(item => {
        headerList.push(item.display_name);
        columnIds.push(item.name);
      });
      const colWidthList = Array(headerList.length).fill(20).map(width => ({ wch: width }));
      const dataList = results.map(item => columnIds.reduce<string[]>((results, columnId) => {
        let value = item[columnId];
        if (columnId === 'bk_biz_id') {
          value = bizsMap.value[Number(value)];
        }
        results.push(value);
        return results
      }, []));
      return {
        headerList,
        colWidthList,
        dataList,
        fileName,
      };
    }
  })
</script>
<style lang="less">
  .render-dynamic-table {
    & ~ .render-dynamic-table {
      margin-top: 16px;
    }
  }

  .dynamic-table-head {
    background-color: #fafbfd;
  }
</style>
