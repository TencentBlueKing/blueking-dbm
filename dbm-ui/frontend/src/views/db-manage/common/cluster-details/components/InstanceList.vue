<template>
  <div class="cluster-detail-instance-list-box">
    <div class="action-box mb-16">
      <BkButton
        class="ml-8"
        style="width: 105px"
        @click="handleNotAliveHostIp">
        {{ t('复制异常 IP') }}
      </BkButton>
      <BkButton
        class="ml-8"
        style="width: 105px"
        @click="handleAllHostIp">
        {{ t('复制所有 IP') }}
      </BkButton>
      <DbSearchSelect
        :data="searchSelectData"
        :placeholder="t('请输入或选择条件搜索')"
        style="flex: 1; max-width: 560px; margin-left: auto"
        unique-select
        @change="handleSearchValueChange" />
    </div>
    <DbTable
      :dataSource="dataSource"
      ref="dbTable">
      <BkTableColumn
        :title="t('实例')"
        field="instance_address" />
      <BkTableColumn
        :title="t('状态')"
        field="status">
        <template #default="{ data }: { data: IColumnData }">
          <ClusterInstanceStatus :data="data.status" />
        </template>
      </BkTableColumn>
      <BkTableColumn
        :title="t('部署角色')"
        field="role" />
      <BkTableColumn
        :title="t('版本')"
        field="version" />
      <BkTableColumn
        :title="t('部署时间')"
        field="create_at" />
    </DbTable>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import useClusterInstanceList from '@views/db-manage/hooks/useClusterInstaceList';
  import ClusterInstanceStatus from '@components/cluster-instance-status/Index.vue';
  import { execCopy, getSearchSelectorParams, messageWarn } from '@utils';
  import { ClusterInstStatusKeys } from '@common/const';

  interface Props {
    clusterId: number;
    clusterType: Parameters<typeof useClusterInstanceList>[0];
  }

  type IColumnData = ServiceReturnType<ReturnType<typeof useClusterInstanceList>>['results'][number];
  const props = defineProps<Props>();

  const { t } = useI18n();

  const requestHandler = useClusterInstanceList(props.clusterType);

  const searchSelectData = [
    {
      id: 'ip',
      name: 'IP',
    },
    {
      children: [
        {
          id: 'running',
          name: t('正常'),
        },
        {
          id: 'unavailable',
          name: t('异常'),
        },
        {
          id: 'loading',
          name: t('重建中'),
        },
      ],
      id: 'status',
      multiple: true,
      name: t('状态'),
    },
    {
      id: 'instance_role',
      name: t('部署角色'),
    },
    {
      id: 'version',
      name: t('版本'),
    },
  ];

  const dataSource = (params: ServiceParameters<typeof requestHandler>) =>
    requestHandler({
      ...params,
      cluster_id: props.clusterId,
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
    });

  const dbTable = useTemplateRef('dbTable');

  const handleNotAliveHostIp = () => {
    const ipList = (dbTable.value?.getData<IColumnData>() || []).reduce<string[]>((result, item) => {
      if (item.status !== ClusterInstStatusKeys.RUNNING) {
        result.push(item.ip);
      }
      return result;
    }, []);

    if (ipList.length < 1) {
      messageWarn(t('没有可复制实例'));
      return;
    }
    execCopy(
      ipList.join('\n'),
      t('复制成功，共n条', {
        n: ipList.length,
      }),
    );
  };

  const handleAllHostIp = () => {
    const ipList = dbTable.value?.getData<IColumnData>().map((item) => item.ip) || [];

    if (ipList.length < 1) {
      messageWarn(t('没有可复制实例'));
      return;
    }
    execCopy(
      ipList.join('\n'),
      t('复制成功，共n条', {
        n: ipList.length,
      }),
    );
  };

  const handleSearchValueChange = (payload: any) => {
    dbTable.value?.fetchData(getSearchSelectorParams(payload));
  };

  onMounted(() => {
    dbTable.value?.fetchData();
  });
</script>
<style lang="less">
  .cluster-detail-instance-list-box {
    padding: 18px 0;

    .action-box {
      display: flex;
    }
  }
</style>
