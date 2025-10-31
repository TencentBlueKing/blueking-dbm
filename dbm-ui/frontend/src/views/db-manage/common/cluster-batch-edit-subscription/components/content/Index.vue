<template>
  <div class="edit-content-main">
    <div class="major-title">
      {{ t('批量设置告警订阅') }}
    </div>
    <BkAlert
      v-if="showUpdate"
      class="alert-main"
      closable
      style="margin-top: -4px"
      theme="warning">
      <template #title>
        <span>1. {{ t('添加订阅后，将接收集群相关的告警通知(仅对您个人生效，不影响其他用户)') }}</span>
        <br />
        <span>2. {{ t('未订阅的集群自动新增订阅，已订阅的集群更新为当前配置') }}</span>
      </template>
    </BkAlert>
    <div class="edit-items-main">
      <div class="title-main">
        <div class="title">{{ t('指标') }}</div>
        <div class="sub-title">({{ t('根据架构类型，自动订阅相关的指标') }})</div>
      </div>
      <div class="indicator-list mb-22">
        <div
          v-for="(item, index) in indicatorList"
          :key="index"
          class="indicator-item">
          <template v-if="item.list.length > 0">
            <div class="item-title">{{ item.title }}</div>
            <div class="item-list">
              <div
                v-for="name in item.list"
                :key="name"
                class="name-item"
                :style="{ width: item.list.length > 1 ? '50%' : '100%' }">
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
          </template>
        </div>
      </div>
      <div class="title-main">
        <div class="title">{{ t('告警级别') }}</div>
      </div>
      <AlarmLevelCheckboxGroup
        v-model="alertSeverity"
        class="mb-22" />
      <div class="title-main">
        <div class="title">{{ t('通知渠道') }}</div>
      </div>
      <NotifyChannelCheckboxGroup v-model="noticeWays" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import AlarmLevelCheckboxGroup from './components/AlertSeverityGroup.vue';
  import NotifyChannelCheckboxGroup from './components/NoticeWaysGroup.vue';

  interface Props {
    clusterTypes?: string[];
    metricsMap?: Record<
      string,
      {
        displayName: string;
        list: string[];
      }
    >;
    showUpdate?: boolean;
  }

  interface Exposes {
    getData: () => {
      alert_level: number[];
      notice_ways: string[];
    };
    reset: () => void;
  }

  const props = withDefaults(defineProps<Props>(), {
    clusterTypes: () => [],
    metricsMap: () => ({}),
    showUpdate: true,
  });

  const { t } = useI18n();

  const alertSeverity = ref<number[]>([]);
  const noticeWays = ref<string[]>([]);

  const indicatorList = computed(() => {
    if (!props.clusterTypes.length || !Object.keys(props.metricsMap).length) {
      return [];
    }

    return props.clusterTypes.map((type) => {
      const item = props.metricsMap[type];
      return {
        list: item.list,
        title: item.displayName,
      };
    });
  });

  const defaultChecked = true;

  const initData = () => {
    alertSeverity.value = [1, 2, 3];
    noticeWays.value = ['weixin', 'mail', 'sms'];
  };

  initData();

  defineExpose<Exposes>({
    getData() {
      return {
        alert_level: alertSeverity.value,
        notice_ways: noticeWays.value,
      };
    },
    reset: initData,
  });
</script>
<style lang="less">
  .edit-content-main {
    height: 600px;
    padding: 16px 24px;
    overflow-y: auto;
    font-family: 'Microsoft YaHei', Arial, sans-serif;

    .alert-main {
      margin-bottom: 16px;
      color: #4d4f56;

      .bk-alert-title {
        line-height: 20px;
      }
    }

    .major-title {
      margin-bottom: 16px;
      font-size: 20px;
      color: #313238;
    }

    .title-main {
      display: flex;
      align-items: center;
      margin-bottom: 12px;

      .title {
        font-size: 14px;
        font-weight: 700;
        color: #313238;
      }

      .sub-title {
        margin-left: 3px;
        font-size: 12px;
        color: #979ba5;
      }
    }

    .edit-items-main {
      font-family: 'Microsoft YaHei', Arial, sans-serif;

      .title-main {
        display: flex;
        align-items: center;
        margin-bottom: 12px;

        .title {
          font-size: 14px;
          font-weight: 700;
          color: #313238;
        }

        .sub-title {
          margin-left: 3px;
          font-size: 12px;
          color: #979ba5;
        }
      }

      .indicator-list {
        .indicator-item {
          padding: 8px 18px 0;
          margin-bottom: 8px;
          font-size: 12px;
          background: #f5f7fa;

          .item-title {
            font-weight: 700;
            color: #313238;
          }

          .item-list {
            display: flex;
            flex-wrap: wrap;
            margin-top: 10px;

            .name-item {
              display: flex;
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
    }
  }
</style>
