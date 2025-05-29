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
      primary-key="id"
      selectable
      @selection="handleSelection">
      <BkTableColumn
        field="instance_address"
        :title="t('实例')" />
      <BkTableColumn
        field="status"
        :title="t('状态')">
        <template #default="{ data }: { data: IInstanceDetail }">
          <ClusterInstanceStatus :data="data.status" />
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="role"
        :title="t('部署角色')">
        <template #default="{ data }: { data: IInstanceDetail }">
          <RenderClusterRole :data="[data.role]" />
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="version"
        :title="t('版本')" />
      <BkTableColumn
        field="create_at"
        :title="t('部署时间')" />
      <BkTableColumn
        field="action"
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
  import { useI18n } from 'vue-i18n';

  import DorisModel from '@services/model/doris/doris';
  import EsModel from '@services/model/es/es';
  import HdfsModel from '@services/model/hdfs/hdfs';
  import KafkaDetailModel from '@services/model/kafka/kafka-detail';
  import PulsarModel from '@services/model/pulsar/pulsar';
  import { createTicket } from '@services/source/ticket';

  import { useTicketMessage } from '@hooks';

  import { ClusterInstStatusKeys, ClusterTypes, TicketTypes } from '@common/const';

  import ClusterInstanceStatus from '@components/cluster-instance-status/Index.vue';

  import RenderClusterRole from '@views/db-manage/common/RenderRole.vue';
  import useClusterInstanceList from '@views/db-manage/hooks/useClusterInstaceList';

  import { execCopy, getSearchSelectorParams, messageWarn } from '@utils';

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
      cluster_id: props.clusterData.id,
    });

  const dbTable = useTemplateRef('dbTable');
  const isRestartLoading = ref(false);
  const isBatchRestartLoading = ref(false);
  const isRestartActionDisabled = ref(false);
  const batchSelectInstanceList = ref<IInstanceDetail[]>([]);

  const isBatchRestartDisabled = computed(() => batchSelectInstanceList.value.length < 1);

  const handleNotAliveHostIp = () => {
    const ipList = (dbTable.value?.getData<IInstanceDetail>() || []).reduce<string[]>((result, item) => {
      if (item.status !== ClusterInstStatusKeys.RUNNING) {
        result.push(item.ip);
      }
      return result;
    }, []);

    if (ipList.length < 1) {
      messageWarn(t('没有可复制 IP'));
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
    const ipList = dbTable.value?.getData<IInstanceDetail>().map((item) => item.ip) || [];

    if (ipList.length < 1) {
      messageWarn(t('没有可复制 IP'));
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

  const handleSelection = (_: any, selectedRows: IInstanceDetail[]) => {
    batchSelectInstanceList.value = selectedRows;
  };

  const handleRestart = (data?: IInstanceDetail) => {
    const restartInstanceList = data ? [data] : batchSelectInstanceList.value;

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
      onClose: () => {
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
    dbTable.value?.fetchData();
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
