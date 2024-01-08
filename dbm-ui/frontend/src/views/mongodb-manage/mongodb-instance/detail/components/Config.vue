<template>
  <div
    v-bkloading="{ loading: isLoading }"
    class="config-info">
    <DbOriginalTable
      :columns="columns"
      :data="data"
      height="100%" />
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MongodbInstanceDetailModel from '@services/model/mongodb/mongodb-instance-detail';
  import { getLevelConfig } from '@services/source/configs';

  import { useGlobalBizs } from '@stores';


  interface Props { payload: MongodbInstanceDetailModel }

  const props = defineProps<Props>();

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const columns = [{
    label: t('参数项'),
    field: 'conf_name',
  }, {
    label: t('参数值'),
    field: 'conf_value',
  }, {
    label: t('描述'),
    field: 'description',
  }, {
    label: t('重启实例生效'),
    field: 'need_restart',
    width: 200,
    render: ({ cell }: { cell: number }) => (cell === 1 ? t('是') : t('否')),
  }];

  /**
   * 获取集群配置
   */
  const {
    data,
    loading: isLoading,
    run: fetchClusterConfig,
  } = useRequest(getLevelConfig, {
    manual: true,
  });

  watch(() => props, () => {
    fetchClusterConfig({
      level_name: 'cluster',
      conf_type: 'dbconf',
      level_value: props.payload.cluster_id,
      meta_cluster_type: props.payload.cluster_type,
      bk_biz_id: currentBizId,
      version: props.payload.version,
    });
  }, {
    immediate: true,
  });
</script>

<style lang="less" scoped>
.config-info {
  height: calc(100% - 96px);
  margin: 24px 0;
}
</style>
