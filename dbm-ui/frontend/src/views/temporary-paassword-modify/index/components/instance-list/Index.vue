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
    ]"
    :selected="instanceSelectorValue"
    unqiue-panel-value
    @change="handleInstanceSelectChange" />
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import { shallowRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbhaInstanceModel from '@services/model/mysql/tendbha-instance';
  import TendbInstanceModel from '@services/model/spider/tendbInstance';
  import SqlServerHaInstanceModel from '@services/model/sqlserver/sqlserver-ha-instance';
  import { queryAdminPassword } from '@services/source/permission';

  import { ClusterTypes } from '@common/const';

  import InstanceSelector, { type InstanceSelectorValues, type IValue } from '@components/instance-selector/Index.vue';


  type IRowData = TendbhaInstanceModel|TendbInstanceModel|SqlServerHaInstanceModel

  const { t } = useI18n();

  const genInstanceKey = (instance: { bk_cloud_id: number; ip: string; port: number }) =>
    `${instance.bk_cloud_id}:${instance.ip}:${instance.port}`;

  const modelValue = defineModel<any[]>({
    default: () => [],
  });

  const isShowInstanceSelector = shallowRef(false);
  const instanceSelectorValue = shallowRef<Record<string, IValue[]>>({
    [ClusterTypes.TENDBSINGLE]: [] as TendbhaInstanceModel[],
    [ClusterTypes.TENDBHA]: [] as TendbhaInstanceModel[],
    [ClusterTypes.TENDBCLUSTER]: [] as TendbInstanceModel[],
    [ClusterTypes.SQLSERVER_HA]: [] as SqlServerHaInstanceModel[],
  });

  const instancePassworValidMap = shallowRef<Record<string, boolean>>({});

  const columns = [
    {
      label: t('实例'),
      field: 'instance_address',
      width: 200,
      render: ({ data }: { data: IRowData }) => (
        <div class="password-form-instance">
          <span>{ data.instance_address }</span>
          {
            instancePassworValidMap.value[genInstanceKey(data)] && <db-icon
              v-bk-tooltips={ t('当前临时密码未过期，继续修改将会覆盖原来的密码') }
              class='ml-4 instance-tip'
              type="attention-fill" />
          }
        </div>
      ),
    },
    {
      label: t('DB类型'),
      field: 'db_type',
      width: 200,
      render: ({ data }: { data: IRowData }) => data.cluster_type,
    },
    {
      label: t('所属集群'),
      field: 'master_domain',
    },
    {
      label: t('操作'),
      field: 'operations',
      width: 100,
      render: ({ data }: { data: IRowData }) => (
        <bk-button
          text
          theme="primary"
          onClick={ () => handleInstanceDelete(data) }>
          { t('删除') }
        </bk-button>
      ),
    },
  ];

  const { run: runQueryAdminPassword } = useRequest(queryAdminPassword, {
    manual: true,
    onSuccess(data) {
      instancePassworValidMap.value = data.results.reduce<Record<string, boolean>>(
        (result, item) =>
          Object.assign(result, {
            [genInstanceKey(item)]: true,
          }),
        {},
      );
    },
    onError() {
      instancePassworValidMap.value = {};
    },
  });

  const handleAddInstance = () => {
    isShowInstanceSelector.value = true;
  };

  const handleInstanceSelectChange = (data: InstanceSelectorValues<IValue>) => {
    modelValue.value = _.flatten(Object.values(data));
    runQueryAdminPassword({
      instances: _.flatten(Object.values(data)).map(genInstanceKey).join(','),
    });
  };

  const handleInstanceDelete = (data: IRowData) => {

    const lastValue = { ...instanceSelectorValue.value }
    Object.values(lastValue).forEach(instanceList => {
      _.remove(instanceList, item => item === data)
    })

    instanceSelectorValue.value = lastValue
    modelValue.value = _.flatten(Object.values(lastValue));
  };
</script>
