<template>
  <div class="big-data-cluster-detail-instance-list-box">
    <div class="action-box mb-16">
      <BkButton
        :disabled="isBatchRestartDisabled || isRestartActionDisabled"
        :loading="isBatchRestartLoading"
        style="width: 105px"
        theme="primary"
        @click="handleRestart()">
        {{ t('批量重启') }}
      </BkButton>
      <BkDropdown>
        <BkButton
          class="ml-8"
          style="width: 105px">
          {{ t('复制实例') }}
          <DbIcon type="right-big" />
        </BkButton>
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem>
              <BkButton
                :disabled="selectionList.length < 1"
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
      <BkDropdown>
        <BkButton
          class="ml-8"
          style="width: 105px">
          {{ t('复制 IP') }}
          <DbIcon type="right-big" />
        </BkButton>
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem>
              <BkButton
                :disabled="selectionList.length < 1"
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
        :model-value="searchSelectValue"
        :placeholder="t('请输入或选择条件搜索')"
        style="flex: 1; max-width: 560px; margin-left: auto"
        unique-select
        @change="handleSearchValueChange" />
    </div>
    <DbTable
      ref="dbTable"
      :data-source="dataSource"
      primary-key="id"
      selectable
      @selection="handleSelection">
      <BkTableColumn
        field="instance_address"
        fixed="left"
        :title="t('实例')" />
      <InstanceListFieldColumn />
      <BkTableColumn
        field="action"
        fixed="right"
        :title="t('操作')">
        <template #default="{ data }: { data: IInstanceDetail }">
          <BkButton
            text
            theme="primary"
            @click="handleRestart(data)">
            {{ t('重启') }}
          </BkButton>
        </template>
      </BkTableColumn>
    </DbTable>
  </div>
</template>
<script lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import DorisModel from '@services/model/doris/doris';
  import EsModel from '@services/model/es/es';
  import HdfsModel from '@services/model/hdfs/hdfs';
  import KafkaDetailModel from '@services/model/kafka/kafka-detail';
  import PulsarModel from '@services/model/pulsar/pulsar';
  import { createTicket } from '@services/source/ticket';

  import { useTicketMessage, useUrlSearch } from '@hooks';

  import { ClusterInstStatusKeys, ClusterTypes, TicketTypes } from '@common/const';

  import useClusterInstanceList from '@views/db-manage/hooks/useClusterInstaceList';

  import { execCopy, getSearchSelectorParams, messageWarn } from '@utils';

  import { URL_INSTANCE_MEMO_KEY } from '../constants';
  import InstanceListFieldColumn from '../InstanceListFieldColumn.vue';
  import { getSearchSelectValue } from '../utils/index';

  interface ClusterTypeRelateClusterModel {
    [ClusterTypes.DORIS]: DorisModel;
    [ClusterTypes.ES]: EsModel;
    [ClusterTypes.HDFS]: HdfsModel;
    [ClusterTypes.KAFKA]: KafkaDetailModel;
    [ClusterTypes.PULSAR]: PulsarModel;
  }

  const clusterTypeWithTicketTypeMap: Record<keyof ClusterTypeRelateClusterModel, TicketTypes> = {
    [ClusterTypes.DORIS]: TicketTypes.DORIS_REBOOT,
    [ClusterTypes.ES]: TicketTypes.ES_REBOOT,
    [ClusterTypes.HDFS]: TicketTypes.HDFS_REBOOT,
    [ClusterTypes.KAFKA]: TicketTypes.KAFKA_REBOOT,
    [ClusterTypes.PULSAR]: TicketTypes.PULSAR_REBOOT,
  };

  type IInstanceDetail = ServiceReturnType<ReturnType<typeof useClusterInstanceList>>['results'][number];
</script>
<script setup lang="tsx" generic="T extends keyof ClusterTypeRelateClusterModel">
  export interface Props<T extends keyof ClusterTypeRelateClusterModel> {
    clusterData: ClusterTypeRelateClusterModel[T];
    clusterType: T;
  }

  const props = defineProps<Props<T>>();

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const ticketMessage = useTicketMessage();
  const requestHandler = useClusterInstanceList(props.clusterType);
  const { getSearchParams } = useUrlSearch();

  const urlPaylaod = JSON.parse(decodeURIComponent(String(route.query[URL_INSTANCE_MEMO_KEY] || '{}')));

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
      cluster_id: props.clusterData.id,
    });

  const dbTable = useTemplateRef('dbTable');
  const isRestartLoading = ref(false);
  const isBatchRestartLoading = ref(false);
  const isRestartActionDisabled = ref(false);
  const selectionList = ref<IInstanceDetail[]>([]);
  const searchSelectValue = shallowRef<ReturnType<typeof getSearchSelectValue>>([]);

  const isBatchRestartDisabled = computed(() => selectionList.value.length < 1);

  const copyFieldData = (data: IInstanceDetail[], field: 'ip' | 'instance_address') => {
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
    copyFieldData(selectionList.value, 'instance_address');
  };

  const handleCopyAbnormalInstance = () => {
    copyFieldData(
      _.filter(
        dbTable.value?.getData<IInstanceDetail>() || [],
        (item) => item.status !== ClusterInstStatusKeys.RUNNING,
      ),
      'instance_address',
    );
  };

  const handleCopyAllInstance = () => {
    copyFieldData(dbTable.value?.getData<IInstanceDetail>() || [], 'instance_address');
  };

  const handleCopySelectedIp = () => {
    copyFieldData(selectionList.value, 'ip');
  };

  const handleCopyAbnormalIp = () => {
    copyFieldData(
      _.filter(
        dbTable.value?.getData<IInstanceDetail>() || [],
        (item) => item.status !== ClusterInstStatusKeys.RUNNING,
      ),
      'ip',
    );
  };

  const handleAllIp = () => {
    copyFieldData(dbTable.value?.getData<IInstanceDetail>() || [], 'ip');
  };

  const handleSearchValueChange = _.debounce((payload: any) => {
    const serachParams = getSearchSelectorParams(payload);
    dbTable.value?.fetchData(serachParams);
    router.replace({
      query: {
        ...getSearchParams(),
        [URL_INSTANCE_MEMO_KEY]: encodeURIComponent(JSON.stringify(serachParams)),
      },
    });
  }, 100);

  const handleSelection = (_: any, selectedRows: IInstanceDetail[]) => {
    selectionList.value = selectedRows;
  };

  const handleRestart = (data?: IInstanceDetail) => {
    const restartInstanceList = data ? [data] : selectionList.value;

    if (data) {
      isRestartLoading.value = true;
    } else {
      isBatchRestartLoading.value = true;
    }

    const formatRequestData = (data: Array<IInstanceDetail>) =>
      data.map((item) => {
        const [ip, port] = item.instance_address.split(':');
        return {
          bk_cloud_id: item.bk_cloud_id,
          bk_host_id: item.bk_host_id,
          instance_id: item.id,
          instance_name: item.instance_name,
          ip,
          port: Number(port),
        };
      });

    InfoBox({
      cancelText: t('取消'),
      confirmText: t('确认重启'),
      contentAlign: 'left',
      extCls: 'big-data-instance-replace-model',
      footerAlign: 'center',
      headerAlign: 'center',
      infoType: 'warning',
      onCancel: () => {
        if (data) {
          isRestartLoading.value = false;
        } else {
          isBatchRestartLoading.value = false;
        }
      },
      onConfirm: () => {
        isRestartActionDisabled.value = true;
        return createTicket({
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          details: {
            cluster_id: props.clusterData.id,
            instance_list: formatRequestData(restartInstanceList),
          },
          ticket_type: clusterTypeWithTicketTypeMap[props.clusterType],
        })
          .then((data) => {
            ticketMessage(data.id);
            window.changeConfirm = false;
          })
          .finally(() => {
            isRestartActionDisabled.value = false;
            if (data) {
              isRestartLoading.value = false;
            } else {
              isBatchRestartLoading.value = false;
            }
          });
      },
      subTitle: () => (
        <div style='background-color: #F5F7FA; padding: 8px 16px;'>
          <div class='tips-item'>
            {t('实例')} :
            <span
              class='ml-8'
              style='color: #313238'>
              {restartInstanceList.map((instanceItem) => instanceItem.instance_address).join(', ')}
            </span>
          </div>
          <div class='mt-4'>{t('连接将会断开，请谨慎操作！')}</div>
        </div>
      ),
      title: t('确认重启该实例？'),
    });
  };

  onMounted(() => {
    searchSelectValue.value = getSearchSelectValue(searchSelectData, urlPaylaod);
  });
</script>
<style lang="less">
  .big-data-cluster-detail-instance-list-box {
    padding: 18px 0;

    .action-box {
      display: flex;
    }
  }

  .big-data-instance-replace-model {
    .bk-modal-content div {
      font-size: 14px;
    }

    .tips-item {
      padding: 2px 0;
    }
  }
</style>
