<template>
  <div class="partition-dry-run">
    <DbSearchSelect
      v-model="searchValues"
      class="mb-16"
      :data="serachData"
      :placeholder="t('请输入 DB 名、表名')"
      style="width: 490px;"
      unique-select
      @change="handleSearch" />
    <BkLoading :loading="isLoading">
      <BkTable
        :columns="tableColumns"
        :data="tableData" />
    </BkLoading>
  </div>
</template>
<script setup lang="ts">
  import {
    shallowRef,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type PartitionModel from '@services/model/partition/partition';
  import { dryRun } from '@services/partitionManage';

  import { ClusterTypes } from '@common/const';

  import {
    getSearchSelectorParams,
  } from '@utils';

  interface Props {
    data: PartitionModel
  }

  interface ITableData {
    dblike: string,
    tblike: string,
    action: string,
    sql: string[],
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const searchValues = ref([]);
  const tableData = shallowRef<ITableData[]>([]);

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

  const tableColumns = [
    {
      label: t('DB 名'),
      field: 'dblikes',
    },
    {
      label: t('表名'),
      field: 'tblikes',
    },
    {
      label: t('执行状态'),
      field: 'tblikes',
    },
    {
      label: t('结果说明'),
      field: 'tblikes',
    },
    {
      label: t('分区动作'),
      field: 'action',
    },
    {
      label: t('分区 SQL'),
      field: 'tblikes',
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
      const executeObjectList = Object.values(data)[0].map(item => item.execute_objects[0]);

      tableData.value = executeObjectList.reduce((result, item) => {
        const dataObj = {
          dblike: item.dblike,
          tblike: item.tblike,
          action: '',
          sql: [],
        };
        if (item.init_partition.length > 0) {
          Object.assign(dataObj, {
            sql: item.init_partition.map(sqlItem => sqlItem.sql),
            action: t('初始化分区'),
          });
        }
        if (item.add_partition.length > 0) {
          Object.assign(dataObj, {
            sql: item.add_partition.map(sqlItem => sqlItem.sql),
            action: t('增加分区'),
          });
        }
        if (item.drop_partition.length > 0) {
          Object.assign(dataObj, {
            sql: item.drop_partition.map(sqlItem => sqlItem.sql),
            action: t('删除分区'),
          });
        }
        result.push(dataObj);
        return result;
      }, [] as ITableData[]);
    },
  });

  const fetchData = () => {
    fetchDryRun({
      config_id: props.data.id,
      cluster_id: props.data.cluster_id,
      cluster_type: ClusterTypes.SPIDER,
    });
  };

  watch(() => props.data, () => {
    if (props.data) {
      fetchData();
    }
  }, {
    immediate: true,
  });

  const handleSearch = () => {
    console.log('getSearchSelectorParams = ', getSearchSelectorParams(searchValues.value));
  };
</script>
<style lang="less">
  .partition-dry-run {
    padding: 16px 24px;
  }
</style>
