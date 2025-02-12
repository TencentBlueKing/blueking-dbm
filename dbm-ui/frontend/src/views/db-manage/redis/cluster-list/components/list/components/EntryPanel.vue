<template>
  <BkPopover
    ext-cls="redis-list-entry-panel-popover"
    placement="top"
    theme="light"
    :width="panelWidth"
    :z-index="10"
    @after-show="handlePanelAfterShow">
    <slot />
    <template #content>
      <BkLoading :loading="loading">
        <div class="redis-list-entry-panel">
          <div class="panel-title">
            {{ dataObj[entryType].panelTitle }}
          </div>
          <div
            v-for="(item, index) in dataObj[entryType].list"
            :key="index"
            class="item-box">
            <div
              class="item-title"
              :style="{ width: isLongTitle ? '96px' : '65px' }">
              {{ item.title }}：
            </div>
            <div class="item-content">
              <span
                v-overflow-tips
                class="text-overflow">
                {{ item.value }}
              </span>
              <DbIcon
                class="icon"
                type="copy"
                @click="() => execCopy(item.value, t('复制成功，共n条', { n: 1 }))" />
              <DbIcon
                v-if="item.shareLink"
                class="icon"
                type="link"
                @click="() => handleNavigateTo(item.shareLink)" />
            </div>
          </div>
        </div>
      </BkLoading>
    </template>
  </BkPopover>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import ClusterEntryDetailModel, {
    type ClbPolarisTargetDetails,
  } from '@services/model/cluster-entry/cluster-entry-details';
  import { getClusterEntries } from '@services/source/clusterEntry';

  import { useGlobalBizs } from '@stores';

  import { execCopy } from '@utils';

  interface Props {
    entryType: 'clb' | 'polaris';
    clusterId: number;
    panelWidth?: number;
  }

  const props = withDefaults(defineProps<Props>(), {
    panelWidth: 250,
  });

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const dataObj = reactive({
    clb: {
      panelTitle: t('腾讯云负载均衡（CLB）'),
      list: [
        {
          title: 'IP',
          value: '',
          shareLink: '',
        },
        {
          title: t('CLB域名'),
          value: '',
          shareLink: '',
        },
      ],
    },
    polaris: {
      panelTitle: t('CL5与北极星'),
      list: [
        {
          title: 'CL5',
          value: '',
          shareLink: '',
        },
        {
          title: t('北极星服务名称'),
          value: '',
          shareLink: '',
        },
      ],
    },
  });

  const isLongTitle = computed(() => props.entryType === 'polaris');

  const { loading, run: runGetClusterEntries } = useRequest(getClusterEntries, {
    manual: true,
    onSuccess: (res) => {
      const entryItem = res[0];
      if (entryItem.isClb) {
        const targetDetailItem = (entryItem as ClusterEntryDetailModel<ClbPolarisTargetDetails>).target_details[0];
        dataObj.clb.list[0].value = targetDetailItem.clb_ip;
        dataObj.clb.list[1].value = targetDetailItem.clb_domain;
      } else if (entryItem.isPolaris) {
        const targetDetailItem = (entryItem as ClusterEntryDetailModel<ClbPolarisTargetDetails>).target_details[0];
        dataObj.polaris.list[0].value = targetDetailItem.polaris_l5;
        dataObj.polaris.list[1].value = targetDetailItem.polaris_name;
        dataObj.polaris.list[0].shareLink = targetDetailItem.url;
      }
    },
  });

  const handlePanelAfterShow = () => {
    runGetClusterEntries({
      cluster_id: props.clusterId,
      bk_biz_id: currentBizId,
      entry_type: props.entryType,
    });
  };

  const handleNavigateTo = (url: string) => {
    window.open(url);
  };
</script>

<style lang="less">
  .redis-list-entry-panel-popover {
    padding: 12px 16px !important;

    .redis-list-entry-panel {
      display: flex;
      width: 100%;
      flex-direction: column;

      .panel-title {
        margin-bottom: 10px;
        font-size: 12px;
        font-weight: 700;
        color: #313238;
      }

      .item-box {
        display: flex;
        width: 100%;
        height: 28px;
        align-items: center;
        font-size: 12px;

        .item-title {
          color: #63656e;
          text-align: right;
        }

        .item-content {
          display: flex;
          overflow: hidden;
          color: #313238;
          flex: 1;
          align-items: center;

          .icon {
            margin-left: 6px;
            color: #3a84ff;
            cursor: pointer;
          }
        }
      }
    }
  }
</style>
