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

  import MongodbInstanceDetailModel from '@services/model/mongodb/mongodb-instance-detail';
  import {
    getConfigNames,
    getLevelConfig } from '@services/source/configs';

  import { useGlobalBizs } from '@stores';

  const props = defineProps<{ payload: MongodbInstanceDetailModel }>();

  /**
   * 获取集群配置
   */
  const  fetchClusterConfig = () => {
    isLoading.value = true;
    getLevelConfig({
      level_name: 'cluster',
      conf_type: 'dbconf',
      level_value: props.payload.cluster_id,
      meta_cluster_type: props.payload.cluster_type,
      bk_biz_id: currentBizId,
      version: props.payload.version,
    }).then((res) => {
      data.value = res.conf_items;
    })
      .finally(() => {
        isLoading.value = false;
      });
  };

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

  const isLoading = ref(false);

  const data = shallowRef<ServiceReturnType<typeof getConfigNames>>();

  watch(() => props, () => {
    fetchClusterConfig();
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
