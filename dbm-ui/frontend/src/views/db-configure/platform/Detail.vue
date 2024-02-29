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
  <div class="configure-details-page">
    <BkTab
      v-model:active="state.activeTab"
      class="top-tabs"
      type="unborder-card">
      <BkTabPanel
        v-for="tab of tabs"
        :key="tab.name"
        v-bind="tab" />
    </BkTab>
    <div class="details-content">
      <template v-if="state.activeTab === 'publish'">
        <PublishRecord :fetch-params="publishFetchParams" />
      </template>
      <template v-else>
        <DetailsBase
          :data="state.data"
          :fetch-params="baseParams"
          :loading="state.loading"
          :sticky-top="92"
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
  import { useRoute, useRouter } from 'vue-router';

  import { getConfigBaseDetails } from '@services/source/configs';

  import { ConfLevels } from '@common/const';

  import DetailsBase from '../components/DetailsBase.vue';
  import PublishRecord from '../components/PublishRecord.vue';

  interface Props {
    clusterType: string;
    confType: string;
    version: string;
  }

  const props = defineProps<Props>();

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();

  const state = reactive({
    loading: false,
    activeTab: '',
    data: {} as ServiceReturnType<typeof getConfigBaseDetails>,
    // extraParametersCards: [] as ExtraConfListItem[]
  });
  const baseParams = computed(() => ({
    meta_cluster_type: props.clusterType,
    conf_type: props.confType,
    version: props.version,
  }));
  const publishFetchParams = computed(() => ({
    ...baseParams.value,
    level_name: ConfLevels.PLAT,
    level_value: 0,
    bk_biz_id: 0,
  }));
  // 顶部 tabs
  const tabs = reactive([
    {
      label: t('基础信息'),
      name: 'base',
    },
    {
      label: t('发布记录'),
      name: 'publish',
    },
  ]);

  /**
   * 获取集群通用默认配置 - dbconf
   */

  state.loading = true;
  getConfigBaseDetails(baseParams.value, {
    permission: 'page',
  })
    .then((res) => {
      state.data = res;
    })
    .finally(() => {
      state.loading = false;
    });

  // 更新基础信息
  const handleUpdateInfo = ({ key, value }: { key: string; value: string }) => {
    Object.assign(state.data, { [key]: value });
  };

  defineExpose({
    routerBack() {
      if (!route.query.form) {
        router.push({
          name: 'PlatformDbConfigureList',
        });
        return;
      }
      router.push({
        name: route.query.form as string,
      });
    },
  });
</script>

<style lang="less">
  @import '@styles/mixins.less';

  .configure-details-page {
    .top-tabs {
      background: #fff;
      box-shadow: 0 3px 4px 0 rgb(0 0 0 / 4%);

      .bk-tab-content {
        display: none;
      }
    }

    .operations {
      .flex-center();

      &__button {
        width: 76px;
        margin-left: 8px;
        font-size: @font-size-mini;
      }
    }

    .details-content {
      height: calc(100vh - 105px);
      padding: 24px;
    }
  }
</style>
