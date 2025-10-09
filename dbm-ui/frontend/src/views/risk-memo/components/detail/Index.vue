<template>
  <div
    v-bk-loading="{ loading: detailLoading }"
    style="height: 100%">
    <div
      v-if="riskMemoDetail"
      class="risk-detail-info-main">
      <div class="title-operate-main">
        <div class="title">{{ riskMemoDetail?.name || '--' }}</div>
        <BkTag
          class="status"
          :theme="!isRiskDone ? 'success' : ''">
          {{ statusTextDisplay }}
        </BkTag>
        <BkButton
          v-if="!isRiskDone"
          size="small"
          @click="handleClickCloseRisk"
          >{{ isSpecial ? t('标记为失效') : t('结项') }}</BkButton
        >
        <BkPopConfirm
          v-else
          :confirm-config="{ loading: updateLoading }"
          :confirm-text="t('重启')"
          :content="isSpecial ? t('重启后，将恢复正常使用') : t('重启后，将恢复重新开放跟进内容')"
          placement="bottom-start"
          :title="isSpecial ? t('确认重启该要求？') : t('确认重启该跟进该风险？')"
          trigger="click"
          :width="280"
          @confirm="handleReopenRisk">
          <BkButton size="small">{{ t('重启') }}</BkButton>
        </BkPopConfirm>
      </div>
      <div class="basic-info-main">
        <div
          v-for="(info, index) in basicInfoList"
          :key="index"
          class="info-item">
          <div class="name">{{ info.name }}</div>
          <div class="ml-4 mr-4">:</div>
          <div
            v-overflow-tips
            class="value">
            {{ info.value }}
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
        <ScrollFaker>
          <div class="risk-detail-main">
            <div class="info-title">{{ t('基础信息') }}</div>
            <BasicInfo
              :data="riskMemoDetail"
              :is-special="isSpecial"
              @update-success="handleGetUpdateDetail" />
            <div class="info-title mt-30 mb-12">{{ t('添加跟进') }}</div>
            <AddFollowUp
              :is-risk-done="isRiskDone"
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
              :data="item"
              :is-risk-done="isRiskDone"
              :risk-id="riskId"
              :show-line="index !== recordList.length - 1"
              @update-success="handleGetUpdateDetail" />
          </div>
        </ScrollFaker>
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
      <span>{{ isSpecial ? t('请先在左侧新建要求') : t('请先在左侧新建风险') }}</span>
    </BkException>
  </div>
  <CloseRisk
    v-model:is-show="isShowCloseRisk"
    :data="riskMemoDetail"
    :is-special="isSpecial"
    @close-success="handleGetUpdateDetail" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getRiskMemoDetail, updateRiskStatus } from '@services/source/riskMemo';

  import { useGlobalBizs } from '@stores';

  import { getCostTimeDisplay, utcDisplayTime } from '@utils';

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

  const { bizIdObjectMap } = useGlobalBizs();
  const { t } = useI18n();

  const recordCount = ref(0);
  const isDescending = ref(true);
  const activeTab = ref('detail');
  const isShowCloseRisk = ref(false);
  const recordList = ref<FollowUpList>([]);

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

  const basicInfoList = computed(() => {
    const list = [
      {
        name: t('业务'),
        value: riskMemoDetail.value?.bk_biz_id ? bizIdObjectMap[riskMemoDetail.value?.bk_biz_id] : '--',
      },
      {
        name: t('创建人'),
        value: riskMemoDetail.value?.creator,
      },
      {
        name: t('创建时间'),
        value: utcDisplayTime(riskMemoDetail.value?.create_at),
      },
      {
        name: t('持续时间'),
        value: getCostTimeDisplay(riskMemoDetail.value?.duration_time || 0),
      },
    ];
    if (props.isSpecial) {
      list.pop();
    }
    return list;
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
            create_at: riskMemoDetail.value.update_at,
            creator: riskMemoDetail.value.updater,
            id: 0,
            is_follow_up_owner: true,
            isEnd: true,
            risk: riskMemoDetail.value.id,
            update_at: '',
            updater: '',
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
    () => props.riskId,
    () => {
      if (props.riskId) {
        runGetRiskMemoDetail({ risk_id: props.riskId });
      } else {
        riskMemoDetail.value = undefined;
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
</script>
<style lang="less">
  .risk-detail-info-main {
    flex: 1;
    height: 100%;
    background: #fff;
    padding: 18px 24px;
    overflow: hidden;
    display: flex;
    flex-direction: column;

    .risk-detail-main {
      .info-title {
        font-weight: 700;
        font-size: 14px;
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
        font-weight: 700;
        font-size: 16px;
        color: #313238;
      }

      .status {
        margin-left: 8px;
        margin-right: 4px;
      }
    }

    .basic-info-main {
      display: flex;
      align-items: center;
      font-size: 12px;
      margin-top: 4px;
      margin-bottom: 16px;

      .info-item {
        display: flex;
        align-items: center;
        margin-right: 32px;

        .name {
          color: #979ba5;
        }

        .value {
          color: #4d4f56;
          max-width: 300px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
      }
    }

    .tab-operate-main {
      display: flex;
      width: 100%;
      height: 42px;
      background: #f0f1f5;
      font-size: 14px;
      margin-bottom: 16px;
      user-select: none;

      .tab-item {
        width: 104px;
        height: 42px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 4px 4px 0 0;
        cursor: pointer;

        &.is-active {
          background: #fff;
          color: #3a84ff;
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
</style>
