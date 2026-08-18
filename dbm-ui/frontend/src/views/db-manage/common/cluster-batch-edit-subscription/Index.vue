<template>
  <DbDialog
    v-model:is-show="isShow"
    class="batch-edit-alarm-subscription-dialog"
    :close-icon="false"
    :confirm-button-disable-info="{
      disabled: isEmpty,
      tooltips: { content: '', disabled: true },
    }"
    :confirm-handler="handleConfirm"
    :esc-close="false"
    :quick-close="false"
    :width="912">
    <BkResizeLayout
      :border="false"
      collapsible
      :initial-divide="365"
      :min="365"
      placement="right"
      style="height: 100%">
      <template #aside>
        <div class="aside-summary-main">
          <span>{{ t('已选集群') }}：</span>
          <I18nT
            keypath="共 {n} 个，{action} {k}"
            tag="span">
            <template #n>{{ count.n }}</template>
            <template #action>{{ t('设置') }}</template>
            <template #k>{{ count.k }}</template>
          </I18nT>
          <I18nT
            v-if="count.s > 0"
            keypath="，跳过 {s}"
            tag="span">
            <template #s>{{ count.s }}</template>
          </I18nT>
          <I18nT
            v-if="count.a > 0"
            keypath="（无权限 {a}）"
            tag="span">
            <template #a>{{ count.a }}</template>
          </I18nT>
        </div>
        <DomainList
          v-model="domainMapList"
          :show-update="showUpdate" />
      </template>
      <template #main>
        <EditContent
          ref="editContentRef"
          :cluster-types="clusterTypes"
          :metrics-map="metricsMap"
          :show-update="showUpdate" />
      </template>
    </BkResizeLayout>
    <template #footer>
      <BkButton
        :disabled="isEmpty || !count.k"
        style="width: 88px"
        theme="primary"
        @click="handleConfirm">
        {{ t('设置') }}
      </BkButton>
      <BkButton
        class="ml-8"
        style="width: 88px"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </DbDialog>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { saveSubscribe } from '@services/source/monitorSubscribe';

  import { useAlarmSubscribe } from '@hooks';

  import { DBTypes } from '@common/const';

  import { countBatchOperation, messageSuccess } from '@utils';

  import EditContent from './components/content/Index.vue';
  import DomainList, { type DomainInfo } from './components/domain-list/Index.vue';

  interface Props {
    selected?: {
      cluster_type: string;
      db_type?: string;
      id?: number;
      master_domain: string;
      permission?: Record<string, boolean>;
    }[];
    showUpdate?: boolean;
  }

  const props = withDefaults(defineProps<Props>(), {
    selected: () => [],
    showUpdate: true,
  });

  const isShow = defineModel<boolean>('isShow', { default: false });

  const { t } = useI18n();
  const { initSubscribedDomainInfo, metricsMap, subscribedDomainInfo } = useAlarmSubscribe();

  const editContentRef = ref<InstanceType<typeof EditContent>>();
  const domainMapList = ref<Record<string, DomainInfo[]>>({});

  const clusterTypes = computed(() => [...new Set(props.selected.map((item) => item.cluster_type))]);

  const isEmpty = computed(() => !Object.values(domainMapList.value).flat().length);

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

  /** 统一计数：设置告警订阅仅无权限跳过（a），无状态不符维度 */
  const count = computed(() =>
    countBatchOperation(props.selected, {
      hasPermission: hasSubscribePermission,
      statusMismatch: () => false,
    }),
  );

  const { runAsync: runSaveSubscribe } = useRequest(saveSubscribe, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('保存成功'));
      initSubscribedDomainInfo();
      editContentRef.value!.reset();
      isShow.value = false;
    },
  });

  watch(
    () => [isShow.value, props.selected],
    () => {
      if (isShow.value) {
        domainMapList.value = props.selected.reduce<
          Record<
            string,
            {
              clusterDomian: string;
              clusterType: string;
              hasPermission: boolean;
              isIgnore: boolean;
              isNew: boolean;
            }[]
          >
        >((dataMap, item) => {
          const displayName = metricsMap.value[item.cluster_type]?.displayName;
          if (!dataMap[displayName]) {
            Object.assign(dataMap, { [displayName]: [] });
          }
          dataMap[displayName].push({
            clusterDomian: item.master_domain,
            clusterType: item.cluster_type,
            hasPermission: hasSubscribePermission(item),
            isIgnore: !metricsMap.value[item.cluster_type].list.length,
            isNew: !subscribedDomainInfo.value.dataSet.has(item.master_domain),
          });
          return dataMap;
        }, {});
      }
    },
    {
      immediate: true,
    },
  );

  const handleConfirm = () => {
    const contentData = editContentRef.value!.getData();
    // 仅提交有权限的集群，跳过无权限的
    const domainList = Object.values(domainMapList.value)
      .flat()
      .filter((item) => item.hasPermission);
    const params = {
      ...contentData,
      clusters: domainList.map((item) => ({
        cluster_domain: item.clusterDomian,
        cluster_type: item.clusterType,
      })),
    };
    return runSaveSubscribe(params);
  };

  const handleCancel = () => {
    isShow.value = false;
  };
</script>
<style lang="less">
  .batch-edit-alarm-subscription-dialog {
    .bk-modal-header {
      display: none;
    }

    .bk-dialog-content {
      padding: 0;
      margin: 0;
    }

    .dialog-header-main {
      padding: 16px 24px 0;
      font-size: 20px;
      color: #313238;
    }

    .aside-summary-main {
      display: flex;
      height: 40px;
      padding-left: 24px;
      font-size: 12px;
      color: #313238;
      background: #fff;
      border-bottom: 1px solid #dcdee5;
      align-items: center;
    }
  }
</style>
