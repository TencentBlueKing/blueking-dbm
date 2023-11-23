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
  <div class="config-biz-details">
    <BkTab
      v-model:active="state.activeTab"
      class="top-tabs"
      type="unborder-card">
      <BkTabPanel
        v-for="tab of tabs"
        :key="tab.name"
        v-bind="tab" />
    </BkTab>
    <div class="details-content db-scroll-y">
      <template v-if="state.activeTab === 'publish'">
        <PublishRecord :fetch-params="fetchParams" />
      </template>
      <template v-else>
        <DetailsBase
          :data="state.data"
          :fetch-params="fetchParams"
          :level="ConfLevels.APP"
          :loading="state.loading"
          :sticky-top="-26"
          @update-info="handleUpdateInfo" />
      </template>
    </div>
  </div>
  <Teleport to="#dbContentTitleAppend">
    <span> - {{ state.data.name }}</span>
  </Teleport>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getLevelConfig } from '@services/source/configs';

  import {  ConfLevels } from '@common/const';

  import DetailsBase from '../components/DetailsBase.vue';
  import PublishRecord from '../components/PublishRecord.vue';
  import { useLevelParams } from '../hooks/useLevelParams';

  interface Props {
    clusterType: string,
    confType: string,
    version: string,
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const state = reactive({
    loading: false,
    activeTab: 'base',
    data: {} as ServiceReturnType<typeof getLevelConfig>,
  });

  // 获取业务层级相关参数
  const levelParams = useLevelParams(false);
  const fetchParams = computed(() => ({
    meta_cluster_type: props.clusterType,
    conf_type: props.confType,
    version: props.version,
    ...levelParams.value,
  }));

  /**
   * 顶部 tabs
   */
  const tabs = reactive([{
    label: t('基础信息'),
    name: 'base',
  }, {
    label: t('发布记录'),
    name: 'publish',
  }]);

  /**
   * 查询配置详情
   */
  const fetchLevelConfig = () => {
    state.loading = true;
    getLevelConfig(fetchParams.value)
      .then((res) => {
        state.data = res;
      })
      .finally(() => {
        state.loading = false;
      });
  };
  fetchLevelConfig();

  // 更新基础信息
  function handleUpdateInfo({ key, value }: { key: string, value: string }) {
    Object.assign(state.data, { [key]: value });
  }
</script>

<style lang="less">
  @import "@styles/mixins.less";

  .config-biz-details{
    .top-tabs{
      background: #fff;
      box-shadow: 0 3px 4px 0 rgb(0 0 0 / 4%);

      .bk-tab-content{
        display: none;
      }
    }

    .config-biz-details {
      height: 100%;

      .base-card {
        margin-bottom: 16px;
      }
    }

    .details-content {
      height: calc(100vh - 152px);
      padding: 24px;

      .details-base {
        height: 100%;
      }
    }
  }

</style>
