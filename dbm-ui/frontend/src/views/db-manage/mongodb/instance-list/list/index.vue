<template>
  <div class="mongodb-instance-list-page">
    <div class="header-action">
      <BkButton
        class="w-88"
        theme="primary"
        @click="handleGoApply">
        {{ t('申请实例') }}
      </BkButton>
      <span
        v-bk-tooltips="{
          disabled: hasSelected,
          content: t('请选择操作实例'),
        }">
        <BkButton
          class="w-88 ml-6"
          :disabled="!hasSelected"
          @click="handleChangeInstanceOnline(selected)">
          {{ t('批量重启') }}
        </BkButton>
      </span>
      <DropdownExportExcel
        export-type="instance"
        :has-selected="hasSelected"
        :ids="selectedIds"
        type="mongodb" />
      <DbSearchSelect
        class="header-select"
        :data="searchSelectData"
        :model-value="searchValue"
        :placeholder="t('请输入或选择条件搜索')"
        unique-select
        :validate-values="validateSearchValues"
        @change="handleSearchValueChange" />
    </div>
    <DbTable
      ref="tableRef"
      :columns="columns"
      :data-source="dataSource"
      :disable-select-method="disableSelectMethod"
      releate-url-query
      :row-class="setRowClass"
      selectable
      :settings="settings"
      :show-overflow="false"
      show-settings
      @clear-search="clearSearchValue"
      @column-filter="columnFilterChange"
      @column-sort="columnSortChange"
      @selection="handleSelection"
      @setting-change="updateTableSettings" />
  </div>
</template>
<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import MongodbInstanceModel from '@services/model/mongodb/mongodb-instance';
  import { getMongoInstancesList } from '@services/source/mongodb';
  import { createTicket } from '@services/source/ticket';

  import { useLinkQueryColumnSerach, useStretchLayout, useTableSettings, useTicketMessage } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes, UserPersonalSettings } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';

  import DropdownExportExcel from '@views/db-manage/common/dropdown-export-excel/index.vue';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import RenderOperationTag from '@views/db-manage/common/RenderOperationTagNew.vue';

  import { getSearchSelectorParams } from '@utils';

  const instanceData = defineModel<{
    clusterId: number;
    instanceAddress: string;
  }>('instanceData');

  const ticketMessage = useTicketMessage();
  const { currentBizId } = useGlobalBizs();
  const router = useRouter();
  const route = useRoute();
  const { t } = useI18n();

  const instanceListClusterType =
    route.name === 'mongodbReplicaSetInstanceList' ? ClusterTypes.MONGO_REPLICA_SET : ClusterTypes.MONGO_SHARED_CLUSTER;

  const {
    clearSearchValue,
    columnAttrs,
    columnCheckedMap,
    columnFilterChange,
    columnSortChange,
    handleSearchValueChange,
    searchAttrs,
    searchValue,
    sortValue,
    validateSearchValues,
  } = useLinkQueryColumnSerach({
    attrs: ['role'],
    defaultSearchItem: {
      id: 'domain',
      name: t('访问入口'),
    },
    fetchDataFn: () => fetchData(isInit),
    isCluster: false,
    searchType: instanceListClusterType,
  });

  const dataSource = (params: ServiceParameters<typeof getMongoInstancesList>) =>
    getMongoInstancesList({
      ...params,
      cluster_type: instanceListClusterType,
    });

  const { isOpen: isStretchLayoutOpen, splitScreen: stretchLayoutSplitScreen } = useStretchLayout();

  const tableRef = useTemplateRef('tableRef');

  const selected = ref<MongodbInstanceModel[]>([]);

  const hasSelected = computed(() => selected.value.length > 0);
  const selectedIds = computed(() => selected.value.map((item) => item.bk_host_id));

  const searchSelectData = computed(() => [
    {
      id: 'instance',
      name: t('IP 或 IP:Port'),
    },
    {
      id: 'domain',
      name: t('域名'),
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
      ],
      id: 'status',
      multiple: true,
      name: t('状态'),
    },
    {
      children: searchAttrs.value.role,
      id: 'role',
      multiple: true,
      name: t('部署角色'),
    },
    {
      id: 'port',
      name: t('端口'),
    },
  ]);

  const columns = computed(() => {
    const list = [
      {
        field: 'instance_address',
        fixed: 'left',
        label: t('实例'),
        minWidth: 180,
        render: ({ data }: { data: MongodbInstanceModel }) => (
          <div style='display: flex; align-items: center;'>
            <div
              v-overflow-tips
              class='text-overflow'>
              <bk-button
                theme='primary'
                text
                onClick={() => handleToDetails(data)}>
                {data.instance_address}
              </bk-button>
            </div>
            {data.operationTagTips.map((item) => (
              <RenderOperationTag
                class='cluster-tag ml-4'
                data={item}
              />
            ))}
          </div>
        ),
        showOverflowTooltip: false,
      },
      {
        field: 'master_domain',
        fixed: 'left',
        label: t('域名'),
        minWidth: 200,
        render: ({ data }: { data: MongodbInstanceModel }) => (
          <div
            v-overflow-tips
            class='text-overflow'>
            <router-link
              to={{
                name: data.cluster_type === 'MongoReplicaSet' ? 'MongoDBReplicaSetList' : 'MongoDBSharedClusterList',
                query: { domain: data.master_domain },
              }}>
              {data.master_domain}
            </router-link>
          </div>
        ),
        showOverflowTooltip: false,
      },
      {
        field: 'role',
        filter: {
          checked: columnCheckedMap.value.role,
          list: columnAttrs.value.role,
        },
        label: t('角色'),
      },
      {
        field: 'status',
        filter: {
          checked: columnCheckedMap.value.status,
          list: [
            {
              text: t('正常'),
              value: 'running',
            },
            {
              text: t('异常'),
              value: 'unavailable',
            },
          ],
        },
        label: t('状态'),
        render: ({ data }: { data: MongodbInstanceModel }) => {
          const { text, theme } = data.dbStatusConfigureObj;
          return (
            <DbStatus
              theme={theme}
              type='linear'>
              {text}
            </DbStatus>
          );
        },
      },
      {
        field: 'shard',
        label: t('分片名'),
        render: ({ data }: { data: MongodbInstanceModel }) => data.shard || '--',
      },
      {
        field: 'bk_sub_zone',
        label: t('所在园区'),
        render: ({ data }: { data: MongodbInstanceModel }) => data.bk_sub_zone || '--',
        width: 140,
      },
      {
        field: 'createAtDisplay',
        label: t('部署时间'),
        sort: true,
      },
      {
        field: 'operation',
        fixed: 'right',
        label: t('操作'),
        render: ({ data }: { data: MongodbInstanceModel }) => (
          <>
            <OperationBtnStatusTips data={data}>
              <bk-button
                class='mr8'
                disabled={data.isRebooting}
                theme='primary'
                text
                onClick={() => handleChangeInstanceOnline([data])}>
                {t('重启')}
              </bk-button>
            </OperationBtnStatusTips>
          </>
        ),
        width: 100,
      },
    ];
    if (isStretchLayoutOpen.value) {
      list.pop();
    }
    return list;
  });

  // 设置用户个人表头信息
  const defaultSettings = {
    checked: (columns.value || []).map((item) => item.field).filter((key) => !!key && key !== 'id') as string[],
    fields: (columns.value || [])
      .filter((item) => item.field)
      .map((item) => ({
        field: item.field as string,
        label: item.label as string,
      })),
    showLineHeight: false,
    trigger: 'manual' as const,
  };

  const { settings, updateTableSettings } = useTableSettings(
    UserPersonalSettings.MONGODB_INSTANCE_TABLE_SETTINGS,
    defaultSettings,
  );

  let isInit = true;
  const fetchData = (loading?: boolean) => {
    tableRef.value!.fetchData(
      {
        ...getSearchSelectorParams(searchValue.value),
      },
      {
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        ...sortValue,
      },
      loading,
    );
    isInit = false;
  };

  const handleChangeInstanceOnline = (data: MongodbInstanceModel[]) => {
    InfoBox({
      cancelText: t('取消'),
      confirmText: t('确认'),
      contentAlign: 'center',
      footerAlign: 'center',
      headerAlign: 'center',
      infoType: 'warning',
      onConfirm: async () => {
        const params = {
          bk_biz_id: currentBizId,
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
        };
        await createTicket(params).then((res) => {
          ticketMessage(res.id);
          fetchData();
        });
      },
      subTitle: (
        <>
          {data.map((item) => (
            <div>{`${item.ip}:${item.port}`}</div>
          ))}
        </>
      ),
      title: t('确认重启实例？'),
    });
  };

  const handleGoApply = () => {
    router.push({
      name: route.name === 'mongodbReplicaSetInstanceList' ? 'MongoDBReplicaSetApply' : 'MongoDBSharedClusterApply',
    });
  };

  const disableSelectMethod = (data: MongodbInstanceModel) => (data.isRebooting ? t('实例重启中') : false);

  const handleSelection = (data: MongodbInstanceModel, list: MongodbInstanceModel[]) => {
    selected.value = list;
  };

  // 设置行样式
  const setRowClass = (data: MongodbInstanceModel) => {
    const classStack = [];
    if (data.isNew) {
      classStack.push('is-new-row');
    }
    if (
      instanceData.value &&
      data.cluster_id === instanceData.value.clusterId &&
      data.instance_address === instanceData.value.instanceAddress
    ) {
      classStack.push('is-selected-row');
    }
    return classStack.join(' ');
  };

  /**
   * 查看实例详情
   */
  const handleToDetails = (data: MongodbInstanceModel) => {
    stretchLayoutSplitScreen();
    instanceData.value = {
      clusterId: data.cluster_id,
      instanceAddress: data.instance_address,
    };
  };
</script>
<style lang="less" scoped>
  @import '@styles/mixins.less';

  .mongodb-instance-list-page {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .header-action {
      display: flex;
      padding-bottom: 16px;
      flex-wrap: wrap;

      .header-select {
        flex: 1;
        max-width: 500px;
        min-width: 320px;
        margin-left: auto;
      }
    }
  }
</style>
