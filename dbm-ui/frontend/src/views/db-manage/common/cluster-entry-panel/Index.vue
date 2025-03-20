<template>
  <BkPopover
    ext-cls="cluster-entry-panel-popover"
    placement="top"
    theme="light"
    :width="panelWidth"
    :z-index="10"
    @after-show="handlePanelAfterShow">
    <BkTag
      class="ml-4"
      :class="[tagInfoMap[entryType].className]"
      size="small">
      {{ tagInfoMap[entryType].text }}
    </BkTag>
    <template #content>
      <BkLoading :loading="loading">
        <div class="cluster-entry-panel">
          <template v-if="entryInfo">
            <div class="panel-title">
              {{ entryInfo.title }}
            </div>
            <div
              v-for="(item, index) in entryInfo.list"
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
          </template>
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

  import { execCopy } from '@utils';

  interface Props {
    clusterId: number;
    entryType: 'clb' | 'polaris';
    panelWidth?: number;
  }

  const props = withDefaults(defineProps<Props>(), {
    panelWidth: 250,
  });

  const { t } = useI18n();

  const entryInfo = shallowRef<{
    list: {
      shareLink?: string;
      title: string;
      value: string;
    }[];
    title: string;
  }>();

  const tagInfoMap: Record<
    string,
    {
      className: string;
      text: string;
    }
  > = {
    clb: {
      className: 'cluster-entry-panel-tag-clb',
      text: 'CLB',
    },
    polaris: {
      className: 'cluster-entry-panel-tag-polaris',
      text: t('北极星'),
    },
  };

  const isLongTitle = computed(() => props.entryType === 'polaris');

  const { loading, run: runGetClusterEntries } = useRequest(getClusterEntries, {
    manual: true,
    onSuccess: (res) => {
      const entryItem = res[0];
      if (entryItem.isClb) {
        const targetDetailItem = (entryItem as ClusterEntryDetailModel<ClbPolarisTargetDetails>).target_details[0];
        const clbInfo = {
          list: [
            {
              title: 'IP',
              value: targetDetailItem.clb_ip,
            },
            {
              title: t('CLB域名'),
              value: targetDetailItem.clb_domain,
            },
          ],
          title: t('腾讯云负载均衡（CLB）'),
        };
        entryInfo.value = clbInfo;
      } else if (entryItem.isPolaris) {
        const targetDetailItem = (entryItem as ClusterEntryDetailModel<ClbPolarisTargetDetails>).target_details[0];
        const polarisInfo = {
          list: [
            {
              title: 'CL5',
              value: targetDetailItem.polaris_l5,
            },
            {
              shareLink: targetDetailItem.url,
              title: t('北极星服务名称'),
              value: targetDetailItem.polaris_name,
            },
          ],
          title: t('CL5与北极星'),
        };
        entryInfo.value = polarisInfo;
      }
    },
  });

  const handlePanelAfterShow = () => {
    runGetClusterEntries({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      cluster_id: props.clusterId,
      entry_type: props.entryType,
    });
  };

  const handleNavigateTo = (url: string) => {
    window.open(url);
  };
</script>

<style lang="less" scoped>
  .cluster-entry-panel-tag-clb {
    color: #8e3aff;
    background-color: #f2edff;
  }

  .cluster-entry-panel-tag-polaris {
    color: #3a84ff;
    background-color: #edf4ff;
  }
</style>

<style lang="less">
  .cluster-entry-panel-popover {
    padding: 12px 16px !important;

    .cluster-entry-panel {
      min-height: 80px;

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
