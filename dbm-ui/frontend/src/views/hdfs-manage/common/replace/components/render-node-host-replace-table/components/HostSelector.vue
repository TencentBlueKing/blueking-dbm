<template>
  <div class="replace-host-selector">
    <div
      v-show="data.hostList.length > 0"
      class="selector-value">
      <div
        v-for="hostItem in data.hostList"
        :key="hostItem.host_id"
        class="ip-tag">
        <span>{{ hostItem.ip }}</span>
        <DbIcon
          class="remove-btn"
          type="close"
          @click="handleRemoveHost(hostItem)" />
      </div>
      <div
        v-if="data.hostList.length > 0"
        class="ip-tag ip-edit-btn"
        @click="handleShowIpSelector">
        <DbIcon type="edit" />
      </div>
    </div>
    <div
      v-show="data.hostList.length < 1"
      class="selector-box">
      <IpSelector
        v-model:show-dialog="isShowIpSelector"
        :biz-id="currentBizId"
        :cloud-info="cloudInfo"
        :disable-dialog-submit-method="disableDialogSubmitMethod"
        :disable-host-method="disableHostMethod"
        :show-view="false"
        @change="handleHostChange">
        <template #submitTips="{ hostList: resultHostList }">
          <I18nT
            keypath="需n台_已选n台"
            style="font-size: 14px; color: #63656e;"
            tag="span">
            <span
              class="number"
              style="color: #2dcb56;">
              {{ data.nodeList.length }}
            </span>
            <span
              class="number"
              style="color: #3a84ff;">
              {{ resultHostList.length }}
            </span>
          </I18nT>
        </template>
      </IpSelector>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { useGlobalBizs } from '@stores';

  import IpSelector from '@components/ip-selector/IpSelector.vue';

  import type { TNodeInfo } from '../../../Index.vue';

  interface Props {
    data: TNodeInfo,
    disableHostMethod?: (params: Props['data']['hostList'][0]) => string | boolean
  }

  const props = defineProps<Props>();
  const modelValue = defineModel<TNodeInfo['hostList']>({
    required: true,
  });

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const cloudInfo = computed(() => {
    const [firstItem] = props.data.nodeList;
    if (firstItem) {
      return {
        id: firstItem.bk_cloud_id,
        name: firstItem.bk_cloud_name,
      };
    }
    return undefined;
  });

  const disableDialogSubmitMethod = (hostList: Props['data']['hostList']) => (
    hostList.length === props.data.nodeList.length
      ? false
      : t('需n台', { n: props.data.nodeList.length })
  );

  const isShowIpSelector = ref(false);

  // 添加新IP
  const handleHostChange = (hostList: Props['data']['hostList']) => {
    modelValue.value = hostList;
  };

  // 移除替换的主机
  const handleRemoveHost = (host: Props['data']['hostList'][0]) => {
    modelValue.value = modelValue.value.reduce((result, item) => {
      if (item.host_id !== host.host_id) {
        result.push(item);
      }
      return result;
    }, [] as Props['data']['hostList']);
  };

  const handleShowIpSelector = () => {
    isShowIpSelector.value = true;
  };
</script>
<style lang="less" scoped>
  .replace-host-selector {
    position: absolute;
    inset: 43px 0 1px 50%;

    .selector-value{
      display: flex;
      height: 100%;
      align-items: center;
      padding: 0 24px;
    }

    .selector-box{
      display: flex;
      align-items: center;
      justify-content: center;
      height: 100%;
    }
  }
</style>
