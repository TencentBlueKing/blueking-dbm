<template>
  <BkFormItem
    class="pr-32"
    :label="t('需要修改的实例')"
    property="instanceList"
    required>
    <BkButton
      class="mb-16"
      @click="handleAddInstance">
      <DbIcon
        class="mr-8"
        type="add" />
      {{ t('添加实例') }}
    </BkButton>
    <BkTable
      :columns="columns"
      :data="modelValue"
      :max-height="300"
      show-overflow-tooltip>
      <!-- <BkTableColumn label="asdasd">
        <template #default="{ data }"> {{ data.instance_address }}sadadad </template>
      </BkTableColumn> -->
    </BkTable>
  </BkFormItem>

  <InstanceSelector
    v-model:is-show="isShowInstanceSelector"
    :cluster-types="[
      ClusterTypes.TENDBSINGLE,
      ClusterTypes.TENDBHA,
      ClusterTypes.TENDBCLUSTER,
      ClusterTypes.SQLSERVER_HA,
      ClusterTypes.SQLSERVER_SINGLE,
    ]"
    hide-manual-input
    :selected="instanceSelectorValue"
    :tab-list-config="tabListConfig"
    :unqiue-panel-tips="t('仅可选择一种类型修改密码')"
    unqiue-panel-value
    @change="handleInstanceSelectChange" />
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import { shallowRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import TendbhaInstanceModel from '@services/model/mysql/tendbha-instance';
  import TendbsingleModel from '@services/model/mysql/tendbsingle';
  import SqlServerHaModel from '@services/model/sqlserver/sqlserver-ha';
  import SqlServerHaInstanceModel from '@services/model/sqlserver/sqlserver-ha-instance';
  import SqlServerSingleInstanceModel from '@services/model/sqlserver/sqlserver-single-instance';
  import TendbclusterModel from '@services/model/tendbcluster/tendbcluster';
  import TendbclusterInstanceModel from '@services/model/tendbcluster/tendbcluster-instance';
  import { queryAdminPassword } from '@services/source/permission';
  import { getTendbclusterInstanceList } from '@services/source/tendbcluster';
  import { getTendbhaInstanceList } from '@services/source/tendbha';

  import { clusterTypeInfos, ClusterTypes } from '@common/const';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type IValue,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';

  type IRowData =
    | TendbhaInstanceModel
    | TendbclusterInstanceModel
    | SqlServerHaInstanceModel
    | SqlServerSingleInstanceModel;

  const { t } = useI18n();

  const genInstanceKey = (instance: { bk_cloud_id: number; ip: string; port: number }) =>
    `${instance.bk_cloud_id}:${instance.ip}:${instance.port}`;

  const tabListConfig = {
    [ClusterTypes.SQLSERVER_HA]: [
      {
        topoConfig: {
          countFunc: (item: SqlServerHaModel) => item.masters.length + item.slaves.length,
        },
      },
    ],
    [ClusterTypes.TENDBCLUSTER]: [
      {
        name: 'TendbCluster',
        tableConfig: {
          firsrColumn: {
            field: 'instance_address',
            label: t('实例'),
            role: '',
          },
          getTableList: (params: ServiceParameters<typeof getTendbclusterInstanceList>) =>
            getTendbclusterInstanceList({
              ...params,
              spider_ctl: true,
            }),
        },
        topoConfig: {
          countFunc: (item: TendbclusterModel) =>
            item.remote_db.length + item.remote_dr.length + item.spider_master.length * 2 + item.spider_slave.length,
        },
      },
    ],
    [ClusterTypes.TENDBHA]: [
      {
        id: 'tendbha',
        name: t('Mysql 主从'),
        tableConfig: {
          firsrColumn: {
            field: 'instance_address',
            label: t('实例'),
            role: '',
          },
          getTableList: (params: ServiceParameters<typeof getTendbhaInstanceList>) =>
            getTendbhaInstanceList({
              ...params,
              role_exclude: 'proxy',
            }),
        },
        topoConfig: {
          countFunc: (item: TendbhaModel) => item.masters.length + item.slaves.length,
        },
      },
    ],
    [ClusterTypes.TENDBSINGLE]: [
      {
        id: 'tendbsingle',
        name: t('Mysql 单节点'),
        topoConfig: {
          countFunc: (item: TendbsingleModel) => item.masters.length,
        },
      },
    ],
  } as unknown as Record<ClusterTypes, PanelListType>;

  const modelValue = defineModel<IValue[]>({
    default: () => [],
  });

  const isShowInstanceSelector = shallowRef(false);
  const instanceSelectorValue = shallowRef<Record<string, IValue[]>>({
    [ClusterTypes.SQLSERVER_HA]: [] as SqlServerHaInstanceModel[],
    [ClusterTypes.SQLSERVER_SINGLE]: [] as SqlServerSingleInstanceModel[],
    [ClusterTypes.TENDBCLUSTER]: [] as TendbclusterInstanceModel[],
    [ClusterTypes.TENDBHA]: [] as TendbhaInstanceModel[],
    [ClusterTypes.TENDBSINGLE]: [] as TendbhaInstanceModel[],
  });

  const instancePassworValidMap = shallowRef<Record<string, boolean>>({});

  const columns = [
    {
      field: 'instance_address',
      label: t('实例'),
      render: ({ data }: { data: IRowData }) => (
        <div class='password-form-instance'>
          <span>{data.instance_address}</span>
          {instancePassworValidMap.value[genInstanceKey(data)] && (
            <db-icon
              v-bk-tooltips={t('当前临时密码未过期，继续修改将会覆盖原来的密码')}
              class='ml-4 instance-tip'
              type='attention-fill'
            />
          )}
        </div>
      ),
      width: 200,
    },
    {
      field: 'db_type',
      label: t('DB类型'),
      render: ({ data }: { data: IRowData }) => data.cluster_type,
      width: 200,
    },
    {
      field: 'master_domain',
      label: t('所属集群'),
    },
    {
      field: 'operations',
      label: t('操作'),
      render: ({ data }: { data: IRowData }) => (
        <bk-button
          theme='primary'
          text
          onClick={() => handleInstanceDelete(data)}>
          {t('删除')}
        </bk-button>
      ),
      width: 100,
    },
  ];

  const { run: runQueryAdminPassword } = useRequest(queryAdminPassword, {
    manual: true,
    onError() {
      instancePassworValidMap.value = {};
    },
    onSuccess(data) {
      instancePassworValidMap.value = data.results.reduce<Record<string, boolean>>(
        (result, item) =>
          Object.assign(result, {
            [genInstanceKey(item)]: true,
          }),
        {},
      );
    },
  });

  const handleAddInstance = () => {
    isShowInstanceSelector.value = true;
  };

  const handleInstanceSelectChange = (data: InstanceSelectorValues<IValue>) => {
    const instanceList = _.flatten(Object.values(data));
    if (instanceList.length < 1) {
      return;
    }
    instanceSelectorValue.value = data;
    modelValue.value = instanceList;
    runQueryAdminPassword({
      db_type: clusterTypeInfos[instanceList[0]!.cluster_type as keyof typeof clusterTypeInfos].dbType,
      instances: _.flatten(Object.values(data)).map(genInstanceKey).join(','),
    });
  };

  const handleInstanceDelete = (data: IRowData) => {
    const lastValue = { ...instanceSelectorValue.value };
    Object.values(lastValue).forEach((instanceList) => {
      _.remove(instanceList, (item) => item === data);
    });

    instanceSelectorValue.value = lastValue;
    modelValue.value = _.flatten(Object.values(lastValue));
  };
</script>
