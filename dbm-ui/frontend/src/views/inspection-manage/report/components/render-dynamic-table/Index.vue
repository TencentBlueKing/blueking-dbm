<template>
  <BkLoading
    class="render-dynamic-table"
    :loading="loading">
    <BlockCard>
      <template #title>
        <span>{{ tableName }}</span>
      </template>
      <BkTable
        :columns="tableColumns"
        :data="tableData"
        :pagination="pagination"
        @page-limit-change="pageLimitChange"
        @page-value-change="pageValueChange" />
    </BlockCard>
    <FailSlaveInstance
      :id="failSlaveInstanceReportId"
      v-model="isShowFailSlaveInstance" />
  </BkLoading>
</template>
<script setup lang="tsx">
  import {
    reactive,
    shallowRef,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getChecksumReport } from '@services/source/report';

  import DbStatus from '@components/db-status/index.vue';

  import BlockCard from './components/BlockCard.vue';
  import FailSlaveInstance from './components/FailSlaveInstance.vue';

  interface Props {
    searchParams?: Record<string, any>,
    service: typeof getChecksumReport
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const pagination = reactive({
    current: 1,
    limit: 10,
  });

  const tableName = ref('');
  const tableColumns = shallowRef<{label: string, render:(data: any) => any }[]>([]);
  const tableData = shallowRef<any[]>([]);

  const isShowFailSlaveInstance = ref(false);
  const failSlaveInstanceReportId = ref(0);

  const handleShowFailSlaveInstance = (data: any) => {
    isShowFailSlaveInstance.value = true;
    failSlaveInstanceReportId.value = data.id;
  };

  const {
    loading,
    run,
  } = useRequest(props.service, {
    manual: true,
    onSuccess(result) {
      tableName.value = result.name;

      tableColumns.value = result.title.map(titleItem => ({
        label: titleItem.display_name,
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
          return fieldData[titleItem.name] || '--';
        },
      }));

      tableData.value = result.results;
    },
  });

  const fetchData = () => {
    run({
      ...props.searchParams,
      ...pagination,
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
    }, {
      permission: 'page',
    });
  };

  watch(() => props.searchParams, () => {
    fetchData();
  }, {
    immediate: true,
  });

  const pageLimitChange = (pageLimit: number) => {
    pagination.limit = pageLimit;
    fetchData();
  };

  const pageValueChange = (pageValue:number) => {
    pagination.current = pageValue;
    fetchData();
  };
</script>
<style lang="less">
  .render-dynamic-table{
    & ~ .render-dynamic-table{
      margin-top: 16px;
    }
  }
</style>
