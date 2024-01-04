<template>
  <div
    v-bkloading="{loading: isLoading}"
    class="instance-details">
    <BkTab
      v-model:active="activePanel"
      class="content-tabs"
      type="card-tab">
      <BkTabPanel
        :label="t('基本信息')"
        name="info" />
      <BkTabPanel
        :label="t('参数配置')"
        name="config" />
    </BkTab>
    <div class="content-wrapper">
      <BaseInfo
        v-if="activePanel === 'info' && data"
        :data="data" />
      <Config
        v-if="activePanel === 'config'"
        :payload="payload" />
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type { PayloadType } from '@services/source/instanceview';
  import { getInstanceDetail } from '@services/source/instanceview';

  import { useGlobalBizs } from '@stores';

  import BaseInfo from './components/BaseInfo.vue';
  import Config from './components/Config.vue';
  interface Props {
    instanceData: {
      instanceAddress: string,
      clusterId: number
    },
    payload:PayloadType
  }

  const props = defineProps<Props>();

  type GetDetailType = ServiceReturnType <typeof getInstanceDetail>

  const globalBizsStore = useGlobalBizs();
  const { t } = useI18n();
  const activePanel = ref('info');
  const data = ref<GetDetailType>();
  const {
    loading: isLoading,
    run: fetchInstDetails,
  } = useRequest(getInstanceDetail, {
    manual: true,
    onSuccess(result) {
      data.value = result;
    },
  });

  watch(() => props.instanceData, () => {
    if (props) {
      fetchInstDetails({
        bk_biz_id: globalBizsStore.currentBizId,
        instance_address: props.instanceData.instanceAddress,
        cluster_id: props.instanceData.clusterId,
      });
    }
  }, {
    immediate: true,
  });
</script>

<style lang="less" scoped>
.instance-details {
  height: 100%;
  background: #fff;

  .content-tabs {
    :deep(.bk-tab-content) {
      padding: 0;
    }
  }

  .content-wrapper {
    height: 100%;
    padding: 0 24px;
    overflow: auto;
  }
}
</style>
