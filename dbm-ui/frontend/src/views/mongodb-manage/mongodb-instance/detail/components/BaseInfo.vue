<template>
  <EditInfo
    class="base-info pt-20"
    :columns="columns"
    :data="data" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { getMongoInstanceDetail } from '@services/source/mongodb';

  import {
    type ClusterInstStatus,
    clusterInstStatus,
  } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';
  import EditInfo, {
    type InfoColumn,
  } from '@components/editable-info/index.vue';

  interface Props {
    data: ServiceReturnType<typeof getMongoInstanceDetail>
  }

  const props = defineProps<Props>();

  const router = useRouter();
  const { t } = useI18n();

  const columns: InfoColumn[][] = [
    [
      {
        label: t('实例'),
        key: 'instance_address',
      },
      {
        label: t('主机IP'),
        key: 'bk_host_innerip',
      },
      {
        label: t('状态'),
        key: 'status',
        render: () => {
          const status = props.data.status as ClusterInstStatus;
          if (!status) return '--';
          const info = clusterInstStatus[status] || clusterInstStatus.unavailable;
          return <DbStatus theme={ info.theme }>{ info.text }</DbStatus>;
        },
      },
      {
        label: t('主访问入口'),
        key: 'master_domain',
        render: () => {
          const domain = props.data.master_domain;
          if (!domain) return '--';
          return (
            <div class="inline-item">
              <div class="text-overflow" v-overflow-tips>
                <bk-button
                  text
                  theme="primary"
                  onClick={ handleToClusterDetails }>
                  { domain }
                </bk-button>
              </div>
              <db-icon
                type="link"
                class="ml-4"
              />
            </div>
          );
        },
      },
      {
        label: t('从访问入口'),
        key: 'slave_domain',
      },
      {
        label: t('管控区域'),
        key: 'bk_cloud_name',
      },
      {
        label: t('所在城市'),
        key: 'idc_city_name',
      },
      {
        label: t('所在机房'),
        key: 'bk_idc_name',
      },
    ],
    [
      {
        label: t('部署架构'),
        key: 'cluster_type_display',
      },
      {
        label: t('部署角色'),
        key: 'role',
      },
      {
        label: t('部署时间'),
        key: 'create_at',
      },
      {
        label: 'CPU',
        key: 'bk_cpu',
        render: () => {
          if (!Number.isFinite(props.data.bk_cpu)) {
            return '--';
          }
          return `${props.data.bk_cpu}${t('核')}`;
        },
      },
      {
        label: t('内存'),
        key: 'bk_mem',
        render: () => {
          if (!Number.isFinite(props.data.bk_mem)) {
            return '--';
          }
          return `${props.data.bk_mem}MB`;
        },
      },
      {
        label: t('磁盘'),
        key: 'bk_disk',
        render: () => {
          if (!Number.isFinite(props.data.bk_disk)) {
            return '--';
          }
          return `${props.data.bk_disk}GB`;
        },
      },
    ],
  ];

  /**
   * 查看集群详情
   */
  const handleToClusterDetails = () => {
    router.push({
      name: props.data.cluster_type === 'MongoReplicaSet' ? 'replicaSetList' : 'sharedClusterList',
      query: {
        cluster_name: props.data.cluster_name,
      },
    });
  };
</script>

<style lang="less" scoped>
.base-info {
  box-shadow: unset;

  :deep(.inline-item) {
    display: flex;
    align-items: center;

    .db-icon-link {
      color: @primary-color;
      cursor: pointer;
      flex-shrink: 0;
    }
  }
}
</style>

