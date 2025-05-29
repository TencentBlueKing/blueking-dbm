<template>
  <div class="cluster-detail-host-list-box">
    <div class="mb-16 action-box">
      <BkButton
        v-bk-tooltips="{
          content: t('请选择主机'),
          disabled: selectedHostList.length > 0,
        }"
        :disabled="selectedHostList.length < 1"
        style="width: 105px"
        @click="handleSelectedHostIp">
        {{ t('复制已选 IP') }}
      </BkButton>
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
      ref="dbTable"
      :data-source="dataSource"
      primary-key="bk_host_id"
      :row-config="{
        useKey: true,
        keyField: 'bk_host_id',
      }"
      selectable
      @selection="handleSelectChange">
      <HostListFieldColumn />
    </DbTable>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import useClusterMachineList from '@views/db-manage/hooks/useClusterMachineList';

  import { getSearchSelectorParams } from '@utils';

  import { useCopyMachineIp } from '../hooks';
  import HostListFieldColumn from '../HostListFieldColumn.vue';

  interface Props {
    clusterId: number;
    clusterType: Parameters<typeof useClusterMachineList>[0];
  }

  type IData = ServiceReturnType<ReturnType<typeof useClusterMachineList>>['results'][number];

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { copyAllIp, copyNotAliveIp } = useCopyMachineIp();
  const requestHandler = useClusterMachineList(props.clusterType);

  const dataSource = (params: ServiceParameters<typeof requestHandler>) =>
    requestHandler({
      cluster_ids: `${props.clusterId}`,
      ...params,
    });

  const searchSelectData = [
    {
      id: 'ip',
      name: 'IP',
    },
    {
      children: [
        {
          id: 'normal',
          name: t('正常'),
        },
        {
          id: 'abnormal',
          name: t('异常'),
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
      id: 'region',
      name: t('地域'),
    },
    {
      id: 'bk_sub_zone',
      name: t('园区'),
    },
    {
      id: 'bk_os_name',
      name: t('操作系统'),
    },

    {
      id: 'bk_svr_device_cls_name',
      name: t('机型'),
    },
  ];

  const dbTable = useTemplateRef('dbTable');

  const selectedHostList = shallowRef<IData[]>([]);

  const handleSelectChange = (_: any[], list: IData[]) => {
    selectedHostList.value = list;
  };

  const handleSelectedHostIp = () => {
    copyAllIp(selectedHostList.value);
  };

  const handleNotAliveHostIp = () => {
    copyNotAliveIp(dbTable.value?.getData<IData>() || []);
  };

  const handleAllHostIp = () => {
    copyAllIp(dbTable.value?.getData<IData>() || []);
  };

  const handleSearchValueChange = (payload: any) => {
    dbTable.value?.fetchData(getSearchSelectorParams(payload));
  };

  onMounted(() => {
    dbTable.value?.fetchData();
  });
</script>
<style lang="less">
  .cluster-detail-host-list-box {
    padding: 18px 0;

    .action-box {
      display: flex;
    }
  }
</style>
