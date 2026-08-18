<template>
  <BkDialog
    v-model:is-show="isShow"
    class="batch-delete-subscription-dialog"
    header-align="center"
    quick-close
    :width="480">
    <template #header>
      <span class="dialog-title">{{ t('确定批量删除n个集群的告警订阅？', { n: count.k }) }}</span>
    </template>
    <div class="operate-cluster-confirm-content">
      <BkAlert
        class="mb-12"
        theme="info"
        :title="t('已订阅的集群将停止发送订阅通知并删除配置。没有订阅的集群保持不变。')" />
      <div class="confirm-summary">
        <span>{{ t('已选集群') }}：</span>
        <I18nT
          keypath="共 {n} 个，{action} {k}"
          tag="span">
          <template #n>
            <strong>{{ count.n }}</strong>
          </template>
          <template #action>{{ t('删除') }}</template>
          <template #k>
            <strong>{{ count.k }}</strong>
          </template>
        </I18nT>
        <I18nT
          v-if="count.s > 0"
          keypath="，跳过 {s}"
          tag="span">
          <template #s>
            <span class="skip-num">{{ count.s }}</span>
          </template>
        </I18nT>
        <I18nT
          v-if="count.a > 0 && count.b > 0"
          keypath="（无权限 {a}，{reason} {b}）"
          tag="span">
          <template #a>{{ count.a }}</template>
          <template #reason>{{ t('未订阅') }}</template>
          <template #b>{{ count.b }}</template>
        </I18nT>
        <I18nT
          v-else-if="count.a > 0"
          keypath="（无权限 {a}）"
          tag="span">
          <template #a>{{ count.a }}</template>
        </I18nT>
        <I18nT
          v-else-if="count.b > 0"
          keypath="（{reason} {b}）"
          tag="span">
          <template #reason>{{ t('未订阅') }}</template>
          <template #b>{{ count.b }}</template>
        </I18nT>
      </div>
      <div class="confirm-list">
        <div class="list-title">{{ t('将删除告警订阅的集群（{n}）', { n: count.k }) }}</div>
        <div
          v-for="item in subscribedList"
          :key="item.master_domain"
          class="list-item">
          <span
            v-overflow-tips
            class="domain-name">
            {{ item.master_domain }}
          </span>
          <!-- <BkTag
            v-if="showUpdate"
            class="status-tag"
            size="small"
            theme="danger">
            {{ t('删除') }}
          </BkTag> -->
        </div>
      </div>
    </div>
    <template #footer>
      <BkButton
        class="mr-8"
        :disabled="!count.k"
        :loading="deleteLoading"
        theme="danger"
        @click="handleConfirm">
        {{ t('删除') }}
      </BkButton>
      <BkButton @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { deleteSubscribe } from '@services/source/monitorSubscribe';

  import { useAlarmSubscribe } from '@hooks';

  import { DBTypes } from '@common/const';

  import { countBatchOperation, messageSuccess } from '@utils';

  interface Props {
    selected?: {
      db_type?: string;
      id?: number;
      master_domain: string;
      permission?: Record<string, boolean>;
    }[];
    // showUpdate?: boolean;
  }

  type Emits = (e: 'success') => void;

  const props = withDefaults(defineProps<Props>(), {
    selected: () => [],
    showUpdate: true,
  });

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', { default: false });

  const { t } = useI18n();
  const { initSubscribedDomainInfo, subscribedDomainInfo } = useAlarmSubscribe();

  const domainList = ref<
    {
      hasPermission: boolean;
      isSubscribed: boolean;
      master_domain: string;
    }[]
  >([]);
  const domainSubscribeIdMap = ref<Record<string, number>>({});

  /** 各数据库类型对应的告警订阅权限 action */
  const subscribeMonitorActionIdMap: Record<string, string> = {
    [DBTypes.DORIS]: 'doris_subscribe_monitor',
    [DBTypes.ES]: 'es_subscribe_monitor',
    [DBTypes.HDFS]: 'hdfs_subscribe_monitor',
    [DBTypes.INFLUXDB]: 'influxdb_subscribe_monitor',
    [DBTypes.KAFKA]: 'kafka_subscribe_monitor',
    [DBTypes.MONGODB]: 'mongodb_subscribe_monitor',
    [DBTypes.MYSQL]: 'mysql_subscribe_monitor',
    [DBTypes.ORACLE]: 'oracle_subscribe_monitor',
    [DBTypes.PULSAR]: 'pulsar_subscribe_monitor',
    [DBTypes.REDIS]: 'redis_subscribe_monitor',
    [DBTypes.RIAK]: 'riak_subscribe_monitor',
    [DBTypes.SQLSERVER]: 'sqlserver_subscribe_monitor',
    [DBTypes.TENDBCLUSTER]: 'tendbcluster_subscribe_monitor',
  };

  /** 集群是否具备告警订阅权限（permission 字段始终返回布尔值） */
  const hasSubscribePermission = (item: NonNullable<Props['selected']>[number]) =>
    item.permission?.[subscribeMonitorActionIdMap[item.db_type ?? '']] !== false;

  /** 统一计数：无权限跳过（a）+ 未订阅跳过（b） */
  const count = computed(() =>
    countBatchOperation(domainList.value, {
      hasPermission: (item) => item.hasPermission,
      statusMismatch: (item) => !item.isSubscribed,
    }),
  );

  /** 将删除告警订阅的集群（有权限且已订阅的，即 K） */
  const subscribedList = computed(() => domainList.value.filter((item) => item.hasPermission && item.isSubscribed));

  const { loading: deleteLoading, run: runDeleteSubscribe } = useRequest(deleteSubscribe, {
    manual: true,
    onSuccess: () => {
      messageSuccess('删除成功');
      emits('success');
      initSubscribedDomainInfo();
      isShow.value = false;
    },
  });

  watch(
    () => [isShow.value, props.selected],
    () => {
      if (isShow.value) {
        domainSubscribeIdMap.value = subscribedDomainInfo.value.dataList.reduce<Record<string, number>>(
          (dataMap, item) =>
            Object.assign(dataMap, {
              [item.master_domain]: item.id,
            }),
          {},
        );

        domainList.value = [];
        props.selected.forEach((item) => {
          const isSubscribed = checkIsDomainSubscribe(item.master_domain);
          domainList.value.push({
            hasPermission: hasSubscribePermission(item),
            isSubscribed,
            master_domain: item.master_domain,
          });
        });
      }
    },
    { immediate: true },
  );

  const checkIsDomainSubscribe = (domain: string) => subscribedDomainInfo.value.dataSet.has(domain);

  const handleConfirm = () => {
    const ids = props.selected.map((item) => domainSubscribeIdMap.value[item.master_domain]).filter((item) => !!item);
    runDeleteSubscribe({ ids });
  };

  const handleCancel = () => {
    isShow.value = false;
  };
</script>
<style lang="less">
  .dialog-title {
    font-size: 16px;
    font-weight: 700;
  }

  .operate-cluster-confirm-content {
    .confirm-summary {
      padding: 8px 12px;
      font-size: 12px;
      line-height: 20px;
      color: #63656e;
      background-color: #f0f1f5;

      strong {
        font-weight: 700;
        color: #313238;
      }

      .skip-num {
        font-weight: 700;
        color: #ff9c01;
      }
    }

    .confirm-list {
      max-height: 240px;
      overflow-y: auto;
      border: 1px solid #eaebf0;
      border-top: none;

      .list-title {
        padding: 8px 12px;
        font-size: 12px;
        font-weight: 700;
        color: #313238;
        background-color: #fff;
        border-bottom: 1px solid #f0f1f5;
      }

      .list-item {
        display: flex;
        align-items: center;
        padding: 8px 12px;
        font-size: 12px;
        color: #63656e;
        border-bottom: 1px solid #f0f1f5;

        &:last-child {
          border-bottom: none;
        }

        .domain-name {
          flex: 1;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .status-tag {
          margin-left: 12px;
        }
      }
    }
  }
</style>
