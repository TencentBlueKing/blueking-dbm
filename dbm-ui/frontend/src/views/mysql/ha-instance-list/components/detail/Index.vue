<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

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
        :query-infos="queryConfigInfos" />
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getResourceInstanceDetails } from '@services/clusters';
  import type { InstanceDetails } from '@services/types/clusters';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, DBTypes } from '@common/const';

  import BaseInfo from './components/BaseInfo.vue';
  import Config from './components/Config.vue';

  interface Props {
    instanceData?: {
      instanceAddress: string,
      clusterId: number
    }
  }

  const props = defineProps<Props>();

  const globalBizsStore = useGlobalBizs();
  const { t } = useI18n();

  const activePanel = ref('info');
  const data = ref<InstanceDetails>();
  const queryConfigInfos = computed(() => ({
    dbModuleId: data.value?.db_module_id ?? 0,
    clusterId: props.instanceData ? props.instanceData.clusterId : 0,
    version: data.value?.version ?? '',
  }));

  const {
    loading: isLoading,
    run: fetchInstDetails,
  } = useRequest(getResourceInstanceDetails, {
    manual: true,
    onSuccess(result) {
      data.value = result;
    },
  });

  watch(() => props.instanceData, () => {
    if (props.instanceData) {
      fetchInstDetails({
        dbType: DBTypes.MYSQL,
        bk_biz_id: globalBizsStore.currentBizId,
        type: ClusterTypes.TENDBHA,
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
