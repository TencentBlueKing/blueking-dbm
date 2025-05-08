<template>
  <EditInfo
    class="pt-20"
    :columns="columns"
    :data="data" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getSingleClusterDetail } from '@services/source/sqlserverSingleCluster';

  import EditInfo, { type InfoColumn } from '@components/editable-info/index.vue';

  import ClusterTagCell from '@views/db-manage/common/cluster-table-column/components/cluster-tag-cell/Index.vue';

  interface Props {
    singleClusterData: {
      clusterId: number;
    };
  }

  type Emits = (e: 'refresh') => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const columns = computed(() => {
    const baseColumns: InfoColumn[][] = [
      [
        {
          key: 'cluster_name',
          label: t('集群名称'),
        },
        {
          key: 'master_domain',
          label: t('主访问入口'),
        },
        {
          key: 'slave_domain',
          label: t('从访问入口'),
        },
        {
          key: 'db_module_name',
          label: t('所属DB模块'),
        },
        {
          key: 'bk_cloud_name',
          label: t('管控区域'),
        },
      ],
      [
        {
          key: 'description',
          label: 'description',
        },
        {
          key: 'node_id',
          label: 'node_id',
        },
        {
          key: 'proxies',
          label: 'Proxy',
        },
        {
          key: 'creator',
          label: t('创建人'),
        },
        {
          key: 'create_at',
          label: t('创建时间'),
        },
      ],
    ];
    if (data.value) {
      baseColumns[0].push({
        key: 'sortedTags',
        label: t('标签'),
        render: () => (
          <ClusterTagCell
            data={data.value!}
            onSuccess={handleRefresh}
          />
        ),
      });
    }
    return baseColumns;
  });

  const { data, run: fetchInstDetails } = useRequest(getSingleClusterDetail, { manual: true });

  const updateDetails = () => {
    fetchInstDetails({ id: props.singleClusterData.clusterId });
  };

  watch(
    () => props.singleClusterData,
    () => {
      if (props.singleClusterData) {
        updateDetails();
      }
    },
    { immediate: true },
  );

  const handleRefresh = () => {
    updateDetails();
    emits('refresh');
  };
</script>
