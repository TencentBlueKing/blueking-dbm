<template>
  <div class="alarm-subscription-main">
    <BkException
      v-if="isEmpty"
      class="empty-main"
      :description="t('暂未添加告警订阅')"
      scene="part"
      type="empty">
      <AuthButton
        :action-id="permissionId"
        class="w-88 mt-12"
        :disabled="data.isOffline"
        :permission="data.permission[permissionId]"
        :resource="data.id"
        theme="primary"
        @click="handleClickAdd">
        {{ t('立即添加') }}
      </AuthButton>
    </BkException>
    <template v-else>
      <BkAlert
        class="alert-main mt-24"
        closable
        theme="warning"
        :title="t('仅展示个人针对当前集群的告警订阅配置')" />
      <div class="content-main">
        <div
          class="item-title"
          style="margin-top: -2px">
          {{ t('指标') }}
        </div>
        <div class="indicator-list">
          <div
            v-for="name in indicatorList"
            :key="name"
            class="name-item">
            <BkCheckbox
              checked
              disabled
              :model-value="defaultChecked" />
            <div
              v-overflow-tips
              class="name">
              {{ name }}
            </div>
          </div>
        </div>
        <div class="item-title mt-10">
          {{ t('告警级别') }}
        </div>
        <AlertSeverityGroup
          v-model="alertSeverity"
          class="alarm-level-main" />
        <div class="item-title">{{ t('通知渠道') }}</div>
        <NoticeWaysGroup v-model="noticeWays" />
      </div>
      <div class="operation-main">
        <BkButton
          class="w-88"
          :loading="saveLoading"
          theme="primary"
          @click="handleClickSave">
          {{ isCreate ? t('确定') : t('保存') }}
        </BkButton>
        <BkButton
          v-if="isCreate"
          class="w-88 ml-8"
          @click="handleClickCancel">
          {{ t('取消') }}
        </BkButton>
        <BkPopConfirm
          v-else
          :content="t('删除订阅将停止发送告警通知并删除配置，如有需要可再次订阅。')"
          ext-cls="delete-subscribe-pop-confirm"
          placement="bottom-start"
          :title="t('确认删除该告警订阅？')"
          trigger="click"
          :width="280"
          @confirm="handleClickDelete">
          <BkButton
            class="w-88 ml-8"
            :loading="deleteLoading">
            {{ t('删除订阅') }}
          </BkButton>
        </BkPopConfirm>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { deleteSubscribe, saveSubscribe } from '@services/source/monitorSubscribe';

  import { useAlarmSubscribe } from '@hooks';

  import { DBTypes } from '@common/const';

  import AlertSeverityGroup from '@views/db-manage/common/cluster-batch-edit-subscription/components/content/components/AlertSeverityGroup.vue';
  import NoticeWaysGroup from '@views/db-manage/common/cluster-batch-edit-subscription/components/content/components/NoticeWaysGroup.vue';

  import { messageSuccess } from '@utils';

  import type { ClusterModel, ISupportClusterType } from '../../cluster-table/types';

  interface Props {
    clusterType: string;
    data: { master_domain?: string } & ClusterModel<ISupportClusterType>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { initSubscribedDomainInfo, metricsMap, subscribedDomainInfo } = useAlarmSubscribe();

  const isEmpty = ref(false);
  const isCreate = ref(false);
  const alertSeverity = ref<number[]>([1]);
  const noticeWays = ref<string[]>(['weixin']);

  // 数据库类型对应的告警订阅权限 actionId
  const subscribeMonitorActionIdMap: Record<DBTypes, string> = {
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

  const indicatorList = computed(() => metricsMap.value[props.clusterType].list || []);
  const permissionId = computed(
    () => subscribeMonitorActionIdMap[props.data.db_type as DBTypes] as keyof typeof props.data.permission,
  );

  let currentInfo: (typeof subscribedDomainInfo.value.dataList)[number] | undefined;

  const defaultChecked = true;

  const { loading: saveLoading, run: runSaveSubscribe } = useRequest(saveSubscribe, {
    manual: true,
    onSuccess: () => {
      messageSuccess('保存成功');
      initSubscribedDomainInfo();
      isCreate.value = false;
    },
  });

  const { loading: deleteLoading, run: runDeleteSubscribe } = useRequest(deleteSubscribe, {
    manual: true,
    onSuccess: () => {
      messageSuccess('删除成功');
      isEmpty.value = true;
      isCreate.value = true;
      initSubscribedDomainInfo();
    },
  });

  watch(
    () => [props.data.master_domain, subscribedDomainInfo.value.dataList],
    () => {
      currentInfo = subscribedDomainInfo.value.dataList.find((item) => item.master_domain === props.data.master_domain);
      if (currentInfo) {
        alertSeverity.value = currentInfo.alert_severity;
        noticeWays.value = currentInfo.notice_ways;
        isEmpty.value = false;
      } else {
        isEmpty.value = true;
      }
    },
    {
      immediate: true,
    },
  );

  const handleClickAdd = () => {
    isEmpty.value = false;
    isCreate.value = true;
  };

  const handleClickCancel = () => {
    isEmpty.value = true;
    isCreate.value = false;
  };

  const handleClickSave = () => {
    const params = {
      alert_level: alertSeverity.value,
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      clusters: [
        {
          cluster_domain: props.data.master_domain!,
          cluster_type: props.clusterType,
        },
      ],
      notice_ways: noticeWays.value,
    };
    runSaveSubscribe(params);
  };

  const handleClickDelete = () => {
    if (currentInfo) {
      runDeleteSubscribe({
        ids: [currentInfo.id],
      });
    }
  };
</script>
<style lang="less">
  .alarm-subscription-main {
    padding: 16px 0;
    font-family: MicrosoftYaHei, Arial, sans-serif;

    .empty-main {
      margin-top: 80px;

      .bk-exception-img {
        height: 150px;
      }

      .bk-exception-description {
        margin-top: -10px;
        font-size: 14px;
        color: #4d4f56;
      }
    }

    .alert-main {
      color: #4d4f56;
    }

    .operation-main {
      margin-top: 32px;
    }

    .content-main {
      margin-top: 16px;
      font-family: MicrosoftYaHei, Arial, sans-serif;

      .item-title {
        margin: 22px 0 12px;
        font-size: 14px;
        font-weight: 700;
        color: #313238;
      }

      .alarm-level-main {
        .bk-checkbox-label {
          .rect-shape {
            width: 12px;
            height: 12px;
          }
        }
      }

      .indicator-list {
        display: flex;
        font-size: 12px;
        flex-wrap: wrap;

        .name-item {
          display: flex;
          width: 50%;
          margin-bottom: 12px;
          align-items: center;

          .name {
            padding-right: 8px;
            margin-left: 6px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            flex: 1;
          }
        }
      }
    }
  }

  .delete-subscribe-pop-confirm {
    .bk-pop-confirm-footer {
      button {
        width: 64px;
      }
    }
  }
</style>
