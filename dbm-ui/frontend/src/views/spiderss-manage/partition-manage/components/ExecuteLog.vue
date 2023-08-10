<template>
  <div>
    <BkLoading :loading="isLoading">
      <DbTable :columns="tableColumns" />
    </BkLoading>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type PartitionModel from '@services/model/partition/partition';
  import { queryLog } from '@services/partitionManage';

  import { ClusterTypes } from '@common/const';

  interface Props {
    data: PartitionModel
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableColumns = [
    {
      lable: t('DB 名'),
      field: 'dblikes',
    },
    {
      lable: t('表名'),
      field: 'tblikes',
    },
    {
      lable: t('执行状态'),
      field: 'tblikes',
    },
    {
      lable: t('结果说明'),
      field: 'tblikes',
    },
    {
      lable: t('分区动作'),
      field: 'tblikes',
    },
    {
      lable: t('分区 SQL'),
      field: 'tblikes',
    },
  ];

  const {
    loading: isLoading,
  } = useRequest(queryLog, {
    defaultParams: [
      {
        cluster_type: ClusterTypes.SPIDER,
        config_id: props.data.id,
      },
    ],
    onSuccess(data) {
      console.log('asdad = ', data);
    },
  });
</script>
<style lang="postcss">
  .root {
    display: block
  }
</style>
