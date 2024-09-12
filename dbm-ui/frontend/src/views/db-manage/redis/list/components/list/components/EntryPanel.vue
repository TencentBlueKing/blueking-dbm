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
                @click="() => copy(item.value)" />
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

  import { getClusterEntries } from '@services/source/cluster';

  import { useCopy } from '@hooks';

  import { useGlobalBizs } from '@stores';

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
  const copy = useCopy();

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
      if (props.entryType === 'clb') {
        dataObj.clb.list[0].value = res[0].target_details.clb_ip;
        dataObj.clb.list[1].value = res[0].target_details.clb_domain;
      } else if (props.entryType === 'polaris') {
        dataObj.polaris.list[0].value = res[0].target_details.polaris_l5;
        dataObj.polaris.list[1].value = res[0].target_details.polaris_name;
        dataObj.polaris.list[0].shareLink = res[0].target_details.url;
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
