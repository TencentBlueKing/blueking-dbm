<template>
  <div
    v-if="riskMemoDetail"
    v-bk-loading="{ loading: detailLoading }"
    class="risk-detail-info-main"
    style="height: 100%">
    <div class="title-operate-main">
      <div class="title">{{ riskMemoDetail?.name || '--' }}</div>
      <BkTag
        class="status"
        :theme="!isRiskDone ? 'success' : ''">
        {{ statusTextDisplay }}
      </BkTag>
      <AuthButton
        v-if="!isRiskDone"
        action-id="risk_memo_manage"
        :biz-id="riskMemoDetail.bk_biz_id"
        :permission="riskMemoManagePermission"
        size="small"
        @click="handleClickCloseRisk">
        {{ isSpecial ? t('标记为失效') : t('结项') }}
      </AuthButton>
      <BkPopConfirm
        v-else
        :confirm-config="{ loading: updateLoading }"
        :confirm-text="t('重启')"
        :content="isSpecial ? t('重启后，将恢复正常使用') : t('重启后，将恢复重新开放跟进内容')"
        placement="bottom-start"
        :popover-options="{
          disabled: !riskMemoManagePermission,
        }"
        :title="isSpecial ? t('确认重启该要求？') : t('确认重启该跟进该风险？')"
        trigger="click"
        :width="280"
        @confirm="handleReopenRisk">
        <AuthButton
          action-id="risk_memo_manage"
          :biz-id="riskMemoDetail.bk_biz_id"
          :permission="riskMemoManagePermission"
          size="small">
          {{ t('重启') }}
        </AuthButton>
      </BkPopConfirm>
    </div>
    <div class="basic-info-main">
      <div class="info-item">
        <div class="name">ID</div>
        <div class="ml-4 mr-4">:</div>
        <div
          v-overflow-tips
          class="value">
          {{ riskMemoDetail?.id }}
        </div>
      </div>
      <div class="info-item">
        <div class="name">{{ t('业务') }}</div>
        <div class="ml-4 mr-4">:</div>
        <div
          v-overflow-tips
          class="value">
          {{ riskMemoDetail?.bk_biz_id ? bizIdMap.get(riskMemoDetail?.bk_biz_id)?.name : '--' }}
        </div>
      </div>
      <div class="info-item">
        <div class="name">{{ t('创建人') }}</div>
        <div class="ml-4 mr-4">:</div>
        <div
          v-overflow-tips
          class="value">
          {{ riskMemoDetail?.creator || '--' }}
        </div>
      </div>
      <div class="info-item">
        <div class="name">{{ t('创建时间') }}</div>
        <div class="ml-4 mr-4">:</div>
        <div
          v-overflow-tips
          class="value">
          {{ utcDisplayTime(riskMemoDetail?.create_at) }}
        </div>
      </div>
      <div
        v-if="!isSpecial"
        class="info-item">
        <div class="name">{{ t('持续时间') }}</div>
        <div class="ml-4 mr-4">:</div>
        <div
          v-overflow-tips
          class="value">
          {{ durationTimeDisplay }}
        </div>
      </div>
      <div class="info-item">
        <div class="name">{{ t('最近更新') }}</div>
        <div class="ml-4 mr-4">:</div>
        <div
          v-overflow-tips
          class="value">
          {{ latestUpdateDisplay }}
        </div>
      </div>
    </div>
    <div class="tab-operate-main">
      <div
        v-for="tab in tabList"
        :key="tab.id"
        class="tab-item"
        :class="{ 'is-active': tab.id === activeTab }"
        @click="() => handleChooseTab(tab.id)">
        {{ tab.label }}
      </div>
    </div>
    <div
      v-if="activeTab === 'detail'"
      class="operate-content-main">
      <div class="risk-detail-main">
        <div class="info-title">{{ t('基础信息') }}</div>
        <BasicInfo
          :data="riskMemoDetail"
          :is-special="isSpecial"
          :manage-permission="riskMemoManagePermission"
          @update-success="handleGetUpdateDetail" />
        <div class="info-title mt-30 mb-12">{{ t('添加跟进') }}</div>
        <AddFollowUp
          :biz-id="riskMemoDetail.bk_biz_id"
          :is-risk-done="isRiskDone"
          :manage-permission="riskMemoManagePermission"
          :risk-id="riskId"
          @success="handleGetUpdateDetail" />
        <div class="info-title mt-24 mb-16">
          <span>{{ t('跟进记录') }}</span>
          <span>（{{ recordCount }}）</span>
          <BkTag
            class="time-sort"
            @click="handleClickSort">
            <span class="mr-6">{{ isDescending ? t('时间倒序') : t('时间正序') }}</span>
            <DbIcon
              v-if="isDescending"
              type="sortupshengxu" />
            <DbIcon
              v-else
              type="sortdownjiangxu" />
          </BkTag>
        </div>
        <FollowUpRecordItem
          v-for="(item, index) in recordList"
          :key="`${item.id}_${index}`"
          :biz-id="riskMemoDetail.bk_biz_id"
          :data="item"
          :is-risk-done="isRiskDone"
          :manage-permission="riskMemoManagePermission"
          :risk-id="riskId"
          :show-line="index !== recordList.length - 1"
          @update-success="handleGetUpdateDetail" />
      </div>
    </div>
    <div
      v-else
      class="operate-records-main">
      <OperationRecord :risk-id="riskMemoDetail.id" />
    </div>
  </div>
  <BkException
    v-else
    class="detail-empty-main"
    type="empty">
    <span>{{ emptyTip }}</span>
  </BkException>
  <CloseRisk
    v-model:is-show="isShowCloseRisk"
    :data="riskMemoDetail"
    :is-special="isSpecial"
    @close-success="handleGetUpdateDetail" />
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { simpleCheckAllowed } from '@services/source/iam';
  import { getRiskMemoDetail, updateRiskStatus } from '@services/source/riskMemo';

  import { useGlobalBizs } from '@stores';

  import { getCostTimeDisplay, utcDisplayTime } from '@utils';

  import { useIntervalFn } from '@vueuse/core';

  import AddFollowUp from './components/AddFollowUp.vue';
  import BasicInfo from './components/basic-info/Index.vue';
  import CloseRisk from './components/CloseRisk.vue';
  import FollowUpRecordItem from './components/FollowUpRecordItem.vue';
  import OperationRecord from './components/OperationRecord.vue';

  export type RiskMemoDetail = ServiceReturnType<typeof getRiskMemoDetail>;
  export type FollowUpList = Array<{ isEnd?: boolean; isStart?: boolean } & RiskMemoDetail['follow_ups'][number]>;

  interface Props {
    isSpecial?: boolean;
    riskId: number;
  }

  type Emits = (e: 'updateSuccess') => void;

  const props = withDefaults(defineProps<Props>(), {
    isSpecial: false,
  });

  const emits = defineEmits<Emits>();

  const { bizIdMap } = useGlobalBizs();
  const { t } = useI18n();

  const recordCount = ref(0);
  const isDescending = ref(true);
  const activeTab = ref('detail');
  const isShowCloseRisk = ref(false);
  const recordList = ref<FollowUpList>([]);
  const durationTimeDisplay = ref(getCostTimeDisplay(0));

  const isRiskDone = computed(() => riskMemoDetail.value?.status === 'done');
  const statusTextDisplay = computed(() => {
    if (!isRiskDone.value) {
      return t('进行中');
    }

    if (props.isSpecial) {
      return t('已失效');
    }

    return t('已结项');
  });
  const emptyTip = computed(() => {
    if (props.riskId === -1) {
      return props.isSpecial ? t('未选择要求') : t('未选择风险');
    }

    if (props.isSpecial) {
      return t('请先在左侧新建要求');
    }

    return t('请先在左侧新建风险');
  });
  const latestUpdateDisplay = computed(() => {
    if (riskMemoDetail.value?.final_time) {
      return utcDisplayTime(riskMemoDetail.value.final_time);
    }

    if (riskMemoDetail.value?.followup_update_at) {
      return utcDisplayTime(riskMemoDetail.value.followup_update_at);
    }

    return utcDisplayTime(riskMemoDetail.value?.create_at);
  });

  const {
    data: riskMemoDetail,
    loading: detailLoading,
    run: runGetRiskMemoDetail,
  } = useRequest(getRiskMemoDetail, { manual: true });

  const { loading: updateLoading, run: runUpdateRiskStatus } = useRequest(updateRiskStatus, {
    manual: true,
    onSuccess: () => {
      handleGetUpdateDetail();
    },
  });

  const { data: riskMemoManagePermission, run: runSimpleCheckAllowed } = useRequest(simpleCheckAllowed, {
    manual: true,
  });

  // 计时
  const { pause, resume } = useIntervalFn(() => {
    const duratiopn = Math.floor(Date.now() / 1000) - dayjs(riskMemoDetail.value?.create_at).valueOf() / 1000;
    durationTimeDisplay.value = getCostTimeDisplay(duratiopn);
  }, 1000);

  const tabList = [
    {
      id: 'detail',
      label: t('风险详情'),
    },
    {
      id: 'record',
      label: t('操作记录'),
    },
  ];

  watch(
    () => [riskMemoDetail.value?.follow_ups, riskMemoDetail.value?.final_content],
    () => {
      if (riskMemoDetail.value?.follow_ups) {
        recordCount.value = riskMemoDetail.value!.follow_ups.length;
        const list: FollowUpList = [
          ...riskMemoDetail.value!.follow_ups,
          {
            content: '',
            create_at: riskMemoDetail.value!.create_at,
            creator: riskMemoDetail.value!.creator,
            id: 0,
            is_follow_up_owner: true,
            isStart: true,
            risk: riskMemoDetail.value!.id,
            update_at: '',
            updater: '',
          },
        ];
        if (riskMemoDetail.value!.final_content) {
          list.unshift({
            content: riskMemoDetail.value.final_content,
            create_at: riskMemoDetail.value.final_time,
            creator: riskMemoDetail.value.updater,
            id: 0,
            is_follow_up_owner: true,
            isEnd: true,
            risk: riskMemoDetail.value.id,
            update_at: riskMemoDetail.value.update_at,
            updater: riskMemoDetail.value.updater,
          });
        }
        recordList.value = list;
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => [riskMemoDetail.value?.status, props.isSpecial],
    () => {
      if (props.isSpecial) {
        pause();
        return;
      }

      if (riskMemoDetail.value?.status === 'done') {
        pause();
        const duration =
          dayjs(riskMemoDetail.value.final_time).valueOf() / 1000 -
          dayjs(riskMemoDetail.value.create_at).valueOf() / 1000;
        durationTimeDisplay.value = getCostTimeDisplay(duration);
      } else {
        resume();
      }
    },
  );

  watch(
    () => props.riskId,
    () => {
      if (props.riskId > 0) {
        runGetRiskMemoDetail({ risk_id: props.riskId });
      } else {
        riskMemoDetail.value = undefined;
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => riskMemoDetail.value?.bk_biz_id,
    (bizId) => {
      if (bizId) {
        runSimpleCheckAllowed({
          action_id: 'risk_memo_manage',
          bk_biz_id: bizId,
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleChooseTab = (id: string) => {
    activeTab.value = id;
  };

  const handleClickSort = () => {
    recordList.value.reverse();
    isDescending.value = !isDescending.value;
  };

  const handleClickCloseRisk = () => {
    isShowCloseRisk.value = true;
  };

  const handleReopenRisk = () => {
    runUpdateRiskStatus({ risk_id: props.riskId, status: 'backlog' });
  };

  const handleGetUpdateDetail = () => {
    runGetRiskMemoDetail({ risk_id: props.riskId });
    emits('updateSuccess');
  };

  onBeforeUnmount(() => {
    pause();
  });
</script>
<style lang="less">
  .risk-detail-info-main {
    display: flex;
    height: 100%;
    padding: 18px 24px;
    overflow: hidden;
    background: #fff;
    flex: 1;
    flex-direction: column;

    .risk-detail-main {
      .info-title {
        font-size: 14px;
        font-weight: 700;
        color: #313238;

        .time-sort {
          cursor: pointer;
        }
      }
    }

    .title-operate-main {
      display: flex;
      align-items: center;

      .title {
        font-size: 16px;
        font-weight: 700;
        color: #313238;
      }

      .status {
        margin-right: 4px;
        margin-left: 8px;
      }
    }

    .basic-info-main {
      display: flex;
      margin-top: 4px;
      margin-bottom: 16px;
      font-size: 12px;
      align-items: center;
      flex-wrap: wrap;

      .info-item {
        display: flex;
        align-items: center;
        margin-right: 26px;

        .name {
          color: #979ba5;
        }

        .value {
          max-width: 300px;
          overflow: hidden;
          color: #4d4f56;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
      }
    }

    .tab-operate-main {
      display: flex;
      width: 100%;
      height: 42px;
      margin-bottom: 16px;
      font-size: 14px;
      background: #f0f1f5;
      user-select: none;

      .tab-item {
        display: flex;
        width: 104px;
        height: 42px;
        cursor: pointer;
        border-radius: 4px 4px 0 0;
        align-items: center;
        justify-content: center;

        &.is-active {
          color: #3a84ff;
          background: #fff;
        }
      }
    }

    .operate-content-main {
      flex: 1;
      overflow-y: auto;
    }

    .operate-records-main {
      flex: 1;
      overflow: hidden;
    }
  }

  .detail-empty-main {
    margin-top: 100px;

    .bk-exception-footer {
      margin-top: -50px;
    }
  }
</style>
