<template>
  <div class="cluster-detail-instance-list-box">
    <div class="action-box mb-16">
      <BkButton
        :disabled="selectedList.length < 1"
        :loading="isRestartLoading"
        style="width: 105px"
        theme="primary"
        @click="handleBatchRestart">
        {{ t('批量重启') }}
      </BkButton>
      <BkDropdown
        :popover-options="{
          clickContentAutoHide: true,
          hideIgnoreReference: true,
        }">
        <template #default="{ popoverShow }">
          <BkButton
            class="ml-8"
            style="width: 105px">
            {{ t('复制实例') }}
            <DbIcon
              :class="{ 'is-show': popoverShow }"
              type="right-big" />
          </BkButton>
        </template>
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem>
              <BkButton
                :disabled="selectedList.length < 1"
                text
                @click="handleCopySelectedInstance">
                {{ t('已选实例') }}
              </BkButton>
            </BkDropdownItem>
            <BkDropdownItem>
              <BkButton
                text
                @click="handleCopyAbnormalInstance">
                {{ t('异常实例') }}
              </BkButton>
            </BkDropdownItem>
            <BkDropdownItem>
              <BkButton
                text
                @click="handleCopyAllInstance">
                {{ t('全部实例') }}
              </BkButton>
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
      <BkDropdown
        :popover-options="{
          clickContentAutoHide: true,
          hideIgnoreReference: true,
        }">
        <template #default="{ popoverShow }">
          <BkButton
            class="ml-8"
            style="width: 105px">
            {{ t('复制 IP') }}
            <DbIcon
              :class="{ 'is-show': popoverShow }"
              type="right-big" />
          </BkButton>
        </template>
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem>
              <BkButton
                :disabled="selectedList.length < 1"
                text
                @click="handleCopySelectedIp">
                {{ t('已选 IP') }}
              </BkButton>
            </BkDropdownItem>
            <BkDropdownItem>
              <BkButton
                text
                @click="handleCopyAbnormalIp">
                {{ t('异常 IP') }}
              </BkButton>
            </BkDropdownItem>
            <BkDropdownItem>
              <BkButton
                text
                @click="handleAllIp">
                {{ t('全部 IP') }}
              </BkButton>
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
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
      selectable
      @selection="handleSelectionChange">
      <BkTableColumn
        field="instance_address"
        fixed="left"
        :min-width="250"
        :title="t('实例')" />
      <BkTableColumn
        field="instance_domain"
        :min-width="300"
        :title="t('所属集群')">
        <template #default="{ data }: { data: MongodbInstanceModel }">
          {{ data.instance_domain || '--' }}
        </template>
      </BkTableColumn>
      <InstanceListFieldColumn />
      <BkTableColumn
        field="action"
        fixed="right"
        :title="t('操作')">
        <template #default="{ data }: { data: MongodbInstanceModel }">
          <BkButton
            text
            theme="primary"
            @click="handleRestart([data])">
            {{ t('重启') }}
          </BkButton>
        </template>
      </BkTableColumn>
    </DbTable>
  </div>
</template>
<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import MongodbInstanceModel from '@services/model/mongodb/mongodb-instance';
  import { createTicket } from '@services/source/ticket';

  import { useTicketMessage } from '@hooks';

  import { ClusterInstStatusKeys, ClusterTypes, TicketTypes } from '@common/const';

  import { InstanceListFieldColumn } from '@views/db-manage/common/cluster-details';
  import useClusterInstanceList from '@views/db-manage/hooks/useClusterInstaceList';

  import { execCopy, getSearchSelectorParams, messageWarn } from '@utils';

  interface Props {
    clusterId: number;
    clusterType: ClusterTypes.MONGO_REPLICA_SET | ClusterTypes.MONGO_SHARED_CLUSTER;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const ticketMessage = useTicketMessage();

  const requestHandler = useClusterInstanceList(props.clusterType);

  const searchSelectData = [
    {
      id: 'ip',
      name: 'IP',
    },
    {
      children: [
        {
          id: 'restoring',
          name: t('恢复中'),
        },
        {
          id: 'running',
          name: t('运行中'),
        },
        {
          id: 'unavailable',
          name: t('不可用'),
        },
        {
          id: 'upgrading',
          name: t('升级中'),
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
      cluster_type: props.clusterType,
    });

  const dbTable = useTemplateRef('dbTable');
  const selectedList = shallowRef<MongodbInstanceModel[]>([]);
  const isRestartLoading = ref(false);

  const fetchData = () => {
    dbTable.value?.fetchData();
  };

  const handleRestart = (data: MongodbInstanceModel[]) => {
    isRestartLoading.value = true;
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('确认'),
      contentAlign: 'center',
      footerAlign: 'center',
      headerAlign: 'center',
      infoType: 'warning',
      onCancel: () => {
        isRestartLoading.value = false;
      },
      onConfirm: () => {
        return createTicket({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          details: {
            infos: data.map((item) => ({
              bk_host_id: item.bk_host_id,
              cluster_id: item.cluster_id,
              instance_id: item.id,
              port: item.port,
              role: item.role,
            })),
          },
          ticket_type: TicketTypes.MONGODB_INSTANCE_RELOAD,
        })
          .then((res) => {
            ticketMessage(res.id);
            fetchData();
          })
          .finally(() => {
            isRestartLoading.value = false;
          });
      },
      subTitle: () => (
        <div>
          {data.map((item) => (
            <div>{`${item.ip}:${item.port}`}</div>
          ))}
        </div>
      ),
      title: t('确认重启实例？'),
    });
  };

  const handleBatchRestart = () => {
    handleRestart(selectedList.value);
  };

  const copyFieldData = (data: MongodbInstanceModel[], field: 'ip' | 'instance_address') => {
    const result = data.map((item) => item[field]) || [];

    if (result.length < 1) {
      messageWarn(t('没有可复制数据'));
      return;
    }
    execCopy(
      result.join('\n'),
      t('复制成功，共n条', {
        n: result.length,
      }),
    );
  };

  const handleCopySelectedInstance = () => {
    copyFieldData(selectedList.value, 'instance_address');
  };

  const handleCopyAbnormalInstance = () => {
    copyFieldData(
      _.filter(
        dbTable.value?.getData<MongodbInstanceModel>() || [],
        (item) => item.status !== ClusterInstStatusKeys.RUNNING,
      ),
      'instance_address',
    );
  };

  const handleCopyAllInstance = () => {
    copyFieldData(dbTable.value?.getData<MongodbInstanceModel>() || [], 'instance_address');
  };

  const handleCopySelectedIp = () => {
    copyFieldData(selectedList.value, 'ip');
  };

  const handleCopyAbnormalIp = () => {
    copyFieldData(
      _.filter(
        dbTable.value?.getData<MongodbInstanceModel>() || [],
        (item) => item.status !== ClusterInstStatusKeys.RUNNING,
      ),
      'ip',
    );
  };

  const handleAllIp = () => {
    copyFieldData(dbTable.value?.getData<MongodbInstanceModel>() || [], 'ip');
  };

  const handleSearchValueChange = (payload: any) => {
    dbTable.value?.fetchData(getSearchSelectorParams(payload));
  };

  const handleSelectionChange = (_: any[], selectList: MongodbInstanceModel[]) => {
    selectedList.value = selectList;
  };
</script>
<style lang="less">
  .cluster-detail-instance-list-box {
    padding: 18px 0;

    .action-box {
      display: flex;
    }

    .is-show {
      transform: rotateZ(180deg);
      transition: all 0.15s;
    }
  }
</style>
