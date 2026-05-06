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
    <PrimaryTable
      :data="modelValue"
      :max-height="300"
      row-key="id">
      <TableColumn
        col-key="instance_address"
        :title="t('实例')"
        :width="300">
        <template #default="{ row }: { row: IRowData }">
          <div class="password-form-instance">
            <span>{{ row.instance_address }}</span>
            <DbIcon
              v-if="instancePassworValidMap[genInstanceKey(row)]"
              v-bk-tooltips="t('当前临时密码未过期，继续修改将会覆盖原来的密码')"
              class="ml-4 instance-tip"
              type="attention-fill" />
          </div>
        </template>
      </TableColumn>
      <TableColumn
        col-key="cluster_type"
        :title="t('DB类型')"
        :width="200">
      </TableColumn>
      <TableColumn
        col-key="master_domain"
        :title="t('所属集群')">
      </TableColumn>
      <TableColumn
        col-key="operations"
        :title="t('操作')"
        :width="100">
        <template #default="{ row }: { row: IRowData }">
          <BkButton
            text
            theme="primary"
            @click="() => handleInstanceDelete(row)">
            {{ t('删除') }}
          </BkButton>
        </template>
      </TableColumn>
    </PrimaryTable>
  </BkFormItem>
  <InstanceSelector
    v-model="instanceSelectorValue"
    v-model:is-show="isShowInstanceSelector"
    :cluster-types="[
      ClusterTypes.TENDBSINGLE,
      ClusterTypes.TENDBHA,
      ClusterTypes.TENDBCLUSTER,
      ClusterTypes.SQLSERVER_HA,
      ClusterTypes.SQLSERVER_SINGLE,
    ]"
    :data-source-map="dataSourceMap"
    :unique-panel-settings="{
      enable: true,
      tip: t('仅可选择一种类型修改密码'),
    }"
    @change="handleInstanceSelectChange" />
</template>
<script setup lang="tsx">
  import { computed, shallowRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbhaInstanceModel from '@services/model/mysql/tendbha-instance';
  import SqlServerHaInstanceModel from '@services/model/sqlserver/sqlserver-ha-instance';
  import SqlServerSingleInstanceModel from '@services/model/sqlserver/sqlserver-single-instance';
  import TendbclusterInstanceModel from '@services/model/tendbcluster/tendbcluster-instance';
  import { queryAdminPassword } from '@services/source/permission';
  import { getTendbclusterInstanceList } from '@services/source/tendbcluster';
  import { getTendbhaInstanceList } from '@services/source/tendbha';
  import { getTendbsingleInstanceList } from '@services/source/tendbsingle';

  import { clusterTypeInfos, ClusterTypes } from '@common/const';

  import InstanceSelector from '@components/instance-selector-new/Index.vue';

  export type IRowData =
    | TendbhaInstanceModel
    | TendbclusterInstanceModel
    | SqlServerHaInstanceModel
    | SqlServerSingleInstanceModel;

  const modelValue = defineModel<IRowData[]>({
    default: () => [],
  });

  const { t } = useI18n();

  const genInstanceKey = (instance: { bk_cloud_id: number; ip: string; port: number }) =>
    `${instance.bk_cloud_id}:${instance.ip}:${instance.port}`;

  const dataSourceMap = {
    [ClusterTypes.TENDBCLUSTER]: (params: ServiceParameters<typeof getTendbclusterInstanceList>) =>
      getTendbclusterInstanceList({
        ...params,
        spider_ctl: true,
      }),
    [ClusterTypes.TENDBHA]: (params: ServiceParameters<typeof getTendbhaInstanceList>) =>
      getTendbhaInstanceList({
        ...params,
        role_exclude: 'proxy',
      }),
    [ClusterTypes.TENDBSINGLE]: (params: ServiceParameters<typeof getTendbsingleInstanceList>) =>
      getTendbsingleInstanceList({
        ...params,
        extra: 1,
      }),
  };

  const isShowInstanceSelector = shallowRef(false);
  const instanceSelectorValue = computed(() => {
    const value: Record<string, IRowData[]> = {
      [ClusterTypes.SQLSERVER_HA]: [],
      [ClusterTypes.SQLSERVER_SINGLE]: [],
      [ClusterTypes.TENDBCLUSTER]: [],
      [ClusterTypes.TENDBHA]: [],
      [ClusterTypes.TENDBSINGLE]: [],
    };

    modelValue.value.forEach((item) => {
      const clusterType = item.cluster_type as ClusterTypes;
      if (value[clusterType]) {
        value[clusterType].push(item);
      }
    });

    return value as Record<ClusterTypes, IRowData[]>;
  });

  const instancePassworValidMap = shallowRef<Record<string, boolean>>({});

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

  const handleInstanceSelectChange = (data: Record<ClusterTypes, IRowData[]>) => {
    const instanceList = Object.values(data).flatMap((item: any) => item);
    if (instanceList.length < 1) {
      return;
    }
    modelValue.value = instanceList;
    runQueryAdminPassword({
      db_type: clusterTypeInfos[instanceList[0]!.cluster_type as keyof typeof clusterTypeInfos].dbType,
      instances: instanceList.map(genInstanceKey).join(','),
    });
  };

  const handleInstanceDelete = (data: IRowData) => {
    modelValue.value = modelValue.value.filter((item) => item !== data);
  };
</script>
