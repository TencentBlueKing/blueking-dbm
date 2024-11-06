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
  <DbCard
    v-model:collapse="collapseActive.targetCluster"
    class="openarea-card"
    :is-active="collapseActive.targetCluster"
    mode="collapse"
    :title="t('开区目标集群')">
    <TargetCluster :ticket-details="ticketDetails" />
  </DbCard>
  <BkLoading :loading="isLoading">
    <DbCard
      v-model:collapse="collapseActive.cloneRule"
      class="openarea-card"
      :is-active="collapseActive.cloneRule"
      mode="collapse"
      :title="t('克隆的规则')">
      <template #desc>
        <span>
          <I18nT
            keypath="(开区模板：t，源集群：c，共克隆 n 个 DB)"
            style="font-size: 12px; color: #63656e"
            tag="span">
            <BkButton
              class="template-name"
              text
              theme="primary"
              @click="handleGoToolbox">
              {{ templateDetail?.config_name }}
            </BkButton>
            <span>{{ templateDetail?.source_cluster.immute_domain }}</span>
            <span style="font-weight: bold">{{ templateDetail?.config_rules.length }}</span>
          </I18nT>
        </span>
      </template>
      <CloneRule :config-rules="templateDetail?.config_rules" />
    </DbCard>
    <DbCard
      v-model:collapse="collapseActive.permissonRule"
      class="openarea-card"
      :is-active="collapseActive.permissonRule"
      mode="collapse"
      :title="t('权限规则')">
      <template #desc>
        <span>
          <I18nT
            keypath="(开区模板：t，源集群：c，共克隆 n 个 DB)"
            style="font-size: 12px; color: #63656e"
            tag="span">
            <BkButton
              class="template-name"
              text
              theme="primary"
              @click="handleGoToolbox">
              {{ templateDetail?.config_name }}
            </BkButton>
            <span>{{ templateDetail?.source_cluster.immute_domain }}</span>
            <span style="font-weight: bold">{{ templateDetail?.config_rules.length }}</span>
          </I18nT>
        </span>
      </template>
      <PermissionRule
        :template-detail="templateDetail"
        :ticket-details="ticketDetails" />
    </DbCard>
  </BkLoading>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type { MysqlOpenAreaDetails } from '@services/model/ticket/details/mysql';
  import TicketModel from '@services/model/ticket/ticket';
  import { getDetail } from '@services/source/openarea';

  import { TicketTypes } from '@common/const';

  import CloneRule from './components/CloneRule.vue';
  import PermissionRule from './components/PermissionRule.vue';
  import TargetCluster from './components/TargetCluster.vue';

  interface Props {
    ticketDetails: TicketModel<MysqlOpenAreaDetails>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const router = useRouter();

  const collapseActive = reactive({
    targetCluster: true,
    cloneRule: true,
    permissonRule: true,
  });

  const {
    run: getTemplateDetail,
    loading: isLoading,
    data: templateDetail,
  } = useRequest(getDetail, {
    manual: true,
  });

  watch(
    () => props.ticketDetails,
    () => {
      getTemplateDetail({
        id: props.ticketDetails.details.config_id,
      });
    },
    {
      immediate: true,
    },
  );

  const handleGoToolbox = () => {
    const ticketTypeRouteNameMap: Record<string, string> = {
      [TicketTypes.MYSQL_OPEN_AREA]: 'MySQLOpenareaTemplate', // Mysql 新建开区
      [TicketTypes.TENDBCLUSTER_OPEN_AREA]: 'spiderOpenareaTemplate', // Spider 开区
    };
    const url = router.resolve({
      name: ticketTypeRouteNameMap[props.ticketDetails.ticket_type],
      query: {
        config_name: templateDetail.value?.config_name,
      },
    });
    window.open(url.href, '_blank');
  };
</script>

<style lang="less" scoped>
  .openarea-card {
    padding: 0 24px 24px;

    :deep(.db-card__desc) {
      color: #313238;
    }

    :deep(.db-card__icon) {
      transform: rotate(-90deg);
    }

    &[is-active='true'] {
      :deep(.db-card__icon) {
        transform: rotate(0);
      }
    }

    .template-name {
      font-size: 12px;
      font-weight: bold;
    }
  }
</style>
