<template>
  <BkSideslider
    v-model:is-show="isShow"
    :before-close="handleBeforeClose"
    class="edit-single-subscription-main"
    :width="640">
    <template #header>
      <div class="major-title">
        <div class="title">{{ t('编辑告警订阅') }}</div>
        <div class="split-line"></div>
        <div class="sub-title">{{ data.master_domain }}</div>
      </div>
    </template>
    <div class="content-main">
      <BkAlert
        class="mb-14"
        closable
        theme="warning"
        :title="t('修改订阅后，将接收集群相关的告警通知（仅对您个人生效，不影响其他用户）')" />
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
    <template #footer>
      <BkButton
        class="w-88"
        :loading="saveLoading"
        theme="primary"
        @click="handleConfirm">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        class="w-88 ml-8"
        style="width: 64px"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkSideslider>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { saveSubscribe } from '@services/source/monitorSubscribe';

  import { useBeforeClose } from '@hooks';

  import { useAlarmSubscribe } from '@stores';

  import AlertSeverityGroup from '@views/db-manage/common/cluster-batch-edit-subscription/components/content/components/AlertSeverityGroup.vue';
  import NoticeWaysGroup from '@views/db-manage/common/cluster-batch-edit-subscription/components/content/components/NoticeWaysGroup.vue';

  import { messageSuccess } from '@utils';

  import type { IRowData } from '../Index.vue';

  interface Props {
    data?: IRowData;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: () => ({}) as IRowData,
  });

  const isShow = defineModel<boolean>('isShow', { default: false });

  const { t } = useI18n();
  const { initSubscribedDomainInfo, metricsMap } = useAlarmSubscribe();
  const checkBeforeClose = useBeforeClose();

  const alertSeverity = ref<number[]>([]);
  const noticeWays = ref<string[]>([]);

  const indicatorList = computed(() => (props.data ? metricsMap[props.data.cluster_type].list : []));

  const defaultChecked = true;

  const { loading: saveLoading, run: runSaveSubscribe } = useRequest(saveSubscribe, {
    manual: true,
    onSuccess: () => {
      messageSuccess('保存成功');
      initSubscribedDomainInfo();
      isShow.value = false;
    },
  });

  watch(
    () => props.data,
    () => {
      if (!props.data) {
        return;
      }

      alertSeverity.value = props.data.alert_severity;
      noticeWays.value = props.data.notice_ways;
    },
    {
      immediate: true,
    },
  );

  const handleConfirm = () => {
    const params = {
      alert_level: alertSeverity.value,
      bk_biz_id: props.data.bk_biz_id,
      clusters: [
        {
          cluster_domain: props.data.master_domain,
          cluster_type: props.data.cluster_type,
        },
      ],
      notice_ways: noticeWays.value,
    };
    runSaveSubscribe(params);
  };

  const handleCancel = () => {
    isShow.value = false;
  };

  const handleBeforeClose = () => {
    const isChanged =
      !_.isEqual(alertSeverity.value, props.data.alert_severity) ||
      !_.isEqual(noticeWays.value, props.data.notice_ways);
    return checkBeforeClose(isChanged);
  };
</script>
<style lang="less">
  .edit-single-subscription-main {
    .bk-sideslider-title {
      .major-title {
        display: flex;
        align-items: center;

        .title {
          font-size: 20px;
          color: #313238;
        }

        .split-line {
          width: 1px;
          height: 14px;
          margin: 0 10px;
          background-color: #dcdee5;
        }

        .sub-title {
          font-size: 14px;
          color: #979ba5;
        }
      }
    }

    .content-main {
      padding: 16px 24px 0;
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
</style>
