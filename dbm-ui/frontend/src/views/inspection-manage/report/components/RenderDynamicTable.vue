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
  </BkLoading>
</template>
<script setup lang="tsx">
  import {
    reactive,
    shallowRef,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getChecksumReport } from '@services/report';

  import DbStatus from '@components/db-status/index.vue';

  import BlockCard from './BlockCard.vue';

  interface Props {
    searchParams?: Record<string, any>,
    service: (params: Record<string, any>) => Promise<ServiceReturnType<typeof getChecksumReport>>
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
          console.log(fieldData);
          const fieldValue = fieldData[titleItem.name];
          if (titleItem.format === 'status') {
            const isSuccess = fieldValue === true;
            return (
              <DbStatus theme={isSuccess ? 'success' : 'danger'}>
                { isSuccess ? t('成功') : t('失败') }
              </DbStatus>
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
