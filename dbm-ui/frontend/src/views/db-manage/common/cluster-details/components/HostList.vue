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
      <BkTableColumn
        field="ip"
        label="IP" />
      <BkTableColumn
        field="host_info"
        :label="t('状态')">
        <template #default="{ data }: { data: IData }">
          <HostAgentStatus :data="data?.host_info?.alive || 0" />
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="host_info.bk_idc_city_name"
        :label="t('地域')">
        <template #default="{ data }: { data: IData }">
          {{ data.host_info.bk_idc_city_name || '--' }}
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="bk_sub_zone"
        :label="t('园区')">
        <template #default="{ data }: { data: IData }">
          {{ data.bk_sub_zone || '--' }}
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="bk_os_name"
        :label="t('操作系统')">
        <template #default="{ data }: { data: IData }">
          {{ data.bk_os_name || '--' }}
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="bk_svr_device_cls_name"
        :label="t('机型')">
        <template #default="{ data }: { data: IData }">
          {{ data.bk_svr_device_cls_name || '--' }}
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="host_info.bk_cpu_architecture"
        :label="t('CPU_核_')">
        <template #default="{ data }: { data: IData }">
          {{ data.host_info.bk_cpu_architecture || '--' }}
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="host_info.bk_mem"
        :label="t('内存M')">
        <template #default="{ data }: { data: IData }">
          {{ data.host_info.bk_mem || '--' }}
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="host_info.bk_disk"
        :label="t('磁盘G')">
        <template #default="{ data }: { data: IData }">
          {{ data.host_info.bk_disk || '--' }}
        </template>
      </BkTableColumn>
    </DbTable>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import HostAgentStatus from '@components/host-agent-status/Index.vue';

  import useClusterMachineList from '@views/db-manage/hooks/useClusterMachineList';

  import { execCopy, getSearchSelectorParams } from '@utils';

  interface Props {
    clusterId: number;
    clusterType: Parameters<typeof useClusterMachineList>[0];
  }

  type IData = ServiceReturnType<ReturnType<typeof useClusterMachineList>>['results'][number];

  const props = defineProps<Props>();

  const { t } = useI18n();
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
    const ipList = selectedHostList.value.map((item) => item.ip);

    execCopy(
      ipList.join('\n'),
      t('复制成功，共n条', {
        n: ipList.length,
      }),
    );
  };

  const handleNotAliveHostIp = () => {
    const ipList = (dbTable.value?.getData<IData>() || []).reduce<string[]>((result, item) => {
      if (!item.host_info.alive) {
        result.push(item.ip);
      }
      return result;
    }, []);
    execCopy(
      ipList.join('\n'),
      t('复制成功，共n条', {
        n: ipList.length,
      }),
    );
  };

  const handleAllHostIp = () => {
    const ipList = dbTable.value?.getData<IData>().map((item) => item.ip) || [];
    execCopy(
      ipList.join('\n'),
      t('复制成功，共n条', {
        n: ipList.length,
      }),
    );
  };

  const handleSearchValueChange = (payload: any) => {
    console.log('handleSearchValueChange = ', getSearchSelectorParams(payload));
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
