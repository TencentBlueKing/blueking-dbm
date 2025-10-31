<template>
  <BkDialog
    v-model:is-show="isShow"
    class="batch-delete-subscription-dialog"
    :esc-close="false"
    :quick-close="false"
    :width="480">
    <div class="content-main">
      <div class="title">{{ t('确定批量删除n个集群的告警订阅？', { n: selected.length }) }}</div>
      <div class="tip-main">{{ t('已订阅的集群将停止发送订阅通知并删除配置，未订阅的将忽略') }}</div>
      <div class="list-main">
        <div class="count-main">
          <I18nT
            keypath="共n个"
            style="font-size: 14px">
            <span
              class="mr-4 ml-4"
              style="font-weight: 700">
              {{ selected.length }}
            </span>
          </I18nT>
          <template v-if="showUpdate">
            <template v-if="countInfo.delete">
              <span class="mr-4 ml-4">,</span>
              <span class="mr-4">{{ t('删除') }}</span>
              <span style="font-weight: 700; color: #ea3636">{{ countInfo.delete }}</span>
            </template>
            <template v-if="countInfo.ignore">
              <span class="mr-4 ml-4">,</span>
              <span class="mr-4">{{ t('忽略') }}</span>
              <span style="font-weight: 700; color: #f59500">{{ countInfo.ignore }}</span>
            </template>
          </template>
        </div>
        <div class="cluster-list">
          <div
            v-for="item in domainList"
            :key="item.master_domain"
            class="domain-item">
            <div
              v-overflow-tips
              class="domain-name">
              {{ item.master_domain }}
            </div>
            <BkTag
              v-if="showUpdate"
              class="status-tag"
              size="small"
              :theme="item.isSubscribed ? 'danger' : 'warning'">
              {{ item.isSubscribed ? t('删除') : t('忽略') }}
            </BkTag>
          </div>
        </div>
      </div>
      <div class="operation-main">
        <BkButton
          class="w-88"
          :disabled="!countInfo.delete"
          :loading="deleteLoading"
          theme="danger"
          @click="handleConfirm">
          {{ t('删除') }}
        </BkButton>
        <BkButton
          class="w-88 ml-8"
          @click="handleCancel">
          {{ t('取消') }}
        </BkButton>
      </div>
    </div>
  </BkDialog>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { deleteSubscribe } from '@services/source/monitorSubscribe';

  import { useAlarmSubscribe } from '@stores';

  import { messageSuccess } from '@utils';

  interface Props {
    selected?: {
      master_domain: string;
    }[];
    showUpdate?: boolean;
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
      isSubscribed: boolean;
      master_domain: string;
    }[]
  >([]);
  const countInfo = ref({
    delete: 0,
    ignore: 0,
  });
  const domainSubscribeIdMap = ref<Record<string, number>>({});

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
        domainSubscribeIdMap.value = subscribedDomainInfo.dataList.reduce<Record<string, number>>(
          (dataMap, item) =>
            Object.assign(dataMap, {
              [item.master_domain]: item.id,
            }),
          {},
        );

        domainList.value = [];
        countInfo.value = {
          delete: 0,
          ignore: 0,
        };
        props.selected.forEach((item) => {
          const isSubscribed = checkIsDomainSubscribe(item.master_domain);
          domainList.value.push({
            isSubscribed,
            master_domain: item.master_domain,
          });
          if (isSubscribed) {
            countInfo.value.delete++;
          } else {
            countInfo.value.ignore++;
          }
        });
      }
    },
    { immediate: true },
  );

  const checkIsDomainSubscribe = (domain: string) => subscribedDomainInfo.dataSet.has(domain);

  const handleConfirm = () => {
    const ids = props.selected.map((item) => domainSubscribeIdMap.value[item.master_domain]).filter((item) => !!item);
    runDeleteSubscribe({ ids });
  };

  const handleCancel = () => {
    isShow.value = false;
  };
</script>
<style lang="less">
  .batch-delete-subscription-dialog {
    .bk-dialog-header {
      height: 16px;
      padding: 0;
    }

    .bk-modal-close {
      font-size: 26px;
      color: #c4c6cc;
    }

    .bk-dialog-content {
      padding: 0;
      margin: 0;
    }

    .bk-modal-footer {
      display: none;
    }

    .content-main {
      padding: 32px 32px 24px;
      font-family: MicrosoftYaHei, Arial, sans-serif;

      .title {
        width: 100%;
        font-size: 20px;
        color: #313238;
        text-align: center;
      }

      .tip-main {
        padding: 12px 16px;
        margin: 16px 0;
        font-size: 14px;
        color: #4d4f56;
        background: #f5f7fa;
        border-radius: 2px;
      }

      .list-main {
        display: flex;
        height: 192px;
        overflow: hidden;
        border: 1px solid #eaebf0;
        border-radius: 2px;
        flex-direction: column;

        .count-main {
          display: flex;
          height: 32px;
          padding-left: 16px;
          background: #f0f1f5;
          align-items: center;
        }

        .cluster-list {
          overflow-y: auto;
          font-size: 12px;
          color: #4d4f56;
          flex: 1;

          .domain-item {
            display: flex;
            height: 32px;
            padding: 0 12px 0 16px;
            background: #fff;
            align-items: center;

            &:nth-child(even) {
              background: #fafbfd;
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

      .operation-main {
        display: flex;
        justify-content: center;
        margin-top: 22px;
      }
    }
  }
</style>
