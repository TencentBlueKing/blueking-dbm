<template>
  <EditInfo
    class="pt-20"
    :columns="columns"
    :data="data" />
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getSingleClusterDetail } from '@services/source/sqlserverSingleCluster';

  import EditInfo, {
    type InfoColumn,
  } from '@components/editable-info/index.vue';

  interface Props {
    singleClusterData:{
      clusterId: number
    }
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const columns: InfoColumn[][] = [
    [
      {
        label: t('集群名称'),
        key: 'cluster_name',
      },
      {
        label: t('主访问入口'),
        key: 'master_domain',
      },
      {
        label: t('从访问入口'),
        key: 'slave_domain',
      },
      {
        label: t('所属DB模块'),
        key: 'db_module_name',
      },
      {
        label: t('管控区域'),
        key: 'bk_cloud_name',
      },
    ],
    [
      {
        label: 'description',
        key: 'description',
      },
      {
        label: 'node_id',
        key: 'node_id',

      },
      {
        label: 'Proxy',
        key: 'proxies',

      },
      {
        label: t('创建人'),
        key: 'creator',
      },
      {
        label: t('创建时间'),
        key: 'create_at',
      },
    ],
  ];

  const {
    run: fetchInstDetails,
    data,
  } = useRequest(getSingleClusterDetail, { manual: true });

  watch(() => props.singleClusterData, () => {
    if (props.singleClusterData) {
      fetchInstDetails({ cluster_id: props.singleClusterData.clusterId });
    }
  }, { immediate: true });
</script>
