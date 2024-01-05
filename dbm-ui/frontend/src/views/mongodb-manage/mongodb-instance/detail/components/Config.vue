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

  import MongodbInstanceModel from '@services/model/mongodb/mongodb-instance';
  import {
    getConfigNames,
    getLevelConfig } from '@services/source/configs';

  import { useGlobalBizs } from '@stores';

  interface Props {
    payload: MongodbInstanceModel
  }

  const props = defineProps<Props>();

  /**
   * 获取集群配置
   */
  const  fetchClusterConfig = (payload: {
    conf_type: string;
    level_name: string;
    level_value: number;
    meta_cluster_type: string;
    version: string;
  }) => {
    isLoading.value = true;
    getLevelConfig(Object.assign(payload, {
      bk_biz_id: currentBizId,
    }))
      .then((res) => {
        data.value = res.conf_items;
      })
      .finally(() => {
        isLoading.value = false;
      });
  };

  const getPayload = (data: MongodbInstanceModel) => ({
    level_name: 'cluster',
    conf_type: 'dbconf',
    level_value: data.cluster_id,
    meta_cluster_type: data.cluster_type,
    version: data.version,
  });

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

  watch(() => props.payload, () => {
    fetchClusterConfig(getPayload(props.payload));
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
