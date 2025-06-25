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
    v-bkloading="{ loading: isLoading }"
    class="cluster-detail-dialog-mode">
    <template v-if="data">
      <DisplayBox
        cluster-detail-router-name="tendbHaDetail"
        :data="data">
        <BkButton
          v-db-console="'mysql.haClusterList.authorize'"
          class="ml-4"
          :disabled="data.isOffline"
          size="small"
          @click="handleShowAuthorize">
          {{ t('授权') }}
        </BkButton>
        <AuthRouterLink
          v-db-console="'mysql.haClusterList.webconsole'"
          action-id="mysql_webconsole"
          class="ml-4"
          :permission="data.permission.mysql_webconsole"
          :resource="data.id"
          target="_blank"
          :to="{
            name: 'MySQLWebconsole',
            query: {
              clusterId: props.clusterId,
            },
          }">
          <BkButton
            :disabled="data.isOffline"
            size="small">
            Webconsole
          </BkButton>
        </AuthRouterLink>
        <BkButton
          class="ml-4"
          :disabled="data.isOffline"
          size="small"
          @click="handleShowDataExportSlider">
          {{ t('导出数据') }}
        </BkButton>
        <MoreActionExtend trigger="click">
          <template #handler>
            <BkButton
              v-bk-tooltips="t('更多操作')"
              class="ml-4"
              size="small"
              style="padding: 0 6px">
              <DbIcon type="more" />
            </BkButton>
          </template>
          <BkDropdownItem
            v-if="isShowDumperEntry"
            v-db-console="'mysql.dataSubscription'">
            <div style="display: inline-block">
              <AuthButton
                action-id="tbinlogdumper_install"
                :disabled="data.isOffline"
                :permission="data.permission.tbinlogdumper_install"
                :resource="data.id"
                text
                @click="handleShowCreateSubscribeRuleSlider">
                {{ t('数据订阅') }}
              </AuthButton>
            </div>
          </BkDropdownItem>
          <BkDropdownItem
            v-if="!data.isOnlineCLB"
            v-db-console="'common.clb'">
            <OperationBtnStatusTips
              :data="data"
              :disabled="!data.isOffline">
              <AuthButton
                action-id="mysql_add_clb"
                :disabled="data.isOffline"
                :permission="data.permission.mysql_add_clb"
                :resource="data.id"
                text
                @click="() => handleAddClb({ details: { cluster_id: data.id, bk_cloud_id: data.bk_cloud_id } })">
                {{ t('启用接入层负载均衡（CLB）') }}
              </AuthButton>
            </OperationBtnStatusTips>
          </BkDropdownItem>
          <BkDropdownItem
            v-if="data.isOnlineCLB"
            v-db-console="'common.clb'">
            <OperationBtnStatusTips
              :data="data"
              :disabled="!data.isOffline">
              <AuthButton
                action-id="mysql_clb_bind_domain"
                :disabled="data.isOffline"
                :permission="data.permission.mysql_clb_bind_domain"
                :resource="data.id"
                text
                @click="
                  () =>
                    handleBindOrUnbindClb(
                      { details: { cluster_id: data.id, bk_cloud_id: data.bk_cloud_id } },
                      data.dns_to_clb,
                    )
                ">
                {{ data.dns_to_clb ? t('恢复主域名直连接入层') : t('配置主域名指向负载均衡器（CLB）') }}
              </AuthButton>
            </OperationBtnStatusTips>
          </BkDropdownItem>
          <BkDropdownItem
            v-if="data.isOnline"
            v-db-console="'mysql.haClusterList.disable'">
            <OperationBtnStatusTips :data="data">
              <AuthButton
                action-id="mysql_enable_disable"
                :disabled="Boolean(data.operationTicketId)"
                :permission="data.permission.mysql_enable_disable"
                :resource="data.id"
                text
                @click="handleDisableCluster([data])">
                {{ t('禁用') }}
              </AuthButton>
            </OperationBtnStatusTips>
          </BkDropdownItem>
          <BkDropdownItem
            v-if="data.isOffline"
            v-db-console="'mysql.haClusterList.enable'">
            <OperationBtnStatusTips :data="data">
              <AuthButton
                action-id="mysql_enable_disable"
                :disabled="data.isStarting"
                :permission="data.permission.mysql_enable_disable"
                :resource="data.id"
                text
                @click="handleEnableCluster([data])">
                {{ t('启用') }}
              </AuthButton>
            </OperationBtnStatusTips>
          </BkDropdownItem>
          <BkDropdownItem v-db-console="'mysql.haClusterList.delete'">
            <OperationBtnStatusTips :data="data">
              <AuthButton
                v-bk-tooltips="{
                  disabled: data.isOffline,
                  content: t('请先禁用集群'),
                }"
                action-id="mysql_destroy"
                :disabled="data.isOnline || Boolean(data.operationTicketId)"
                :permission="data.permission.mysql_destroy"
                :resource="data.id"
                text
                @click="handleDeleteCluster([data])">
                {{ t('删除') }}
              </AuthButton>
            </OperationBtnStatusTips>
          </BkDropdownItem>
          <BkDropdownItem>
            <ClusterDomainDnsRelation :data="data" />
          </BkDropdownItem>
        </MoreActionExtend>
      </DisplayBox>
      <ActionPanel
        :cluster-data="data"
        :cluster-role-node-group="clusterRoleNodeGroup"
        :cluster-type="ClusterTypes.TENDBHA">
        <template #infoContent>
          <BaseInfo
            :data="data"
            @refresh="fetchDetailData" />
        </template>
      </ActionPanel>
      <ClusterAuthorize
        v-model="isAuthorizeShow"
        :account-type="AccountTypes.MYSQL"
        :cluster-types="[ClusterTypes.TENDBHA, 'tendbhaSlave']"
        :selected="[data]" />
      <ClusterExportData
        v-model:is-show="isShowDataExport"
        :data="data"
        :ticket-type="TicketTypes.MYSQL_DUMP_DATA" />
      <CreateSubscribeRuleSlider
        v-model="isShowCreateSubscribeRule"
        :selected-clusters="[data]"
        show-tab-panel />
    </template>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import type { MySQLFunctions } from '@services/model/function-controller/functionController';
  import TendbhaModel from '@services/model/mysql/tendbha';
  import { getTendbhaDetail } from '@services/source/tendbha';

  import { useFunController } from '@stores';

  import { AccountTypes, ClusterTypes, TicketTypes } from '@common/const';

  import MoreActionExtend from '@components/more-action-extend/Index.vue';

  import ClusterAuthorize from '@views/db-manage/common/cluster-authorize/Index.vue';
  import { ActionPanel, DisplayBox } from '@views/db-manage/common/cluster-details';
  import ClusterDomainDnsRelation from '@views/db-manage/common/cluster-domain-dns-relation/Index.vue';
  import ClusterExportData from '@views/db-manage/common/cluster-export-data/Index.vue';
  import { useAddClb, useBindOrUnbindClb, useOperateClusterBasic } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import CreateSubscribeRuleSlider from '@views/db-manage/mysql/dumper/components/create-rule/Index.vue';

  import BaseInfo from './components/BaseInfo.vue';

  interface Props {
    clusterId: number;
  }

  type Emits = (e: 'change') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const funControllerStore = useFunController();
  const { handleAddClb } = useAddClb<{
    bk_cloud_id: number;
    cluster_id: number;
  }>(ClusterTypes.TENDBHA);
  const { handleBindOrUnbindClb } = useBindOrUnbindClb<{
    bk_cloud_id: number;
    cluster_id: number;
  }>(ClusterTypes.TENDBHA);

  const data = ref<TendbhaModel>();

  /** 集群授权 */
  const isAuthorizeShow = ref(false);
  const isShowDataExport = ref(false);
  const isShowCreateSubscribeRule = ref(false);

  const clusterRoleNodeGroup = computed(() => {
    /* eslint-disable perfectionist/sort-objects */
    return {
      Proxy: data.value?.proxies || [],
      Master: data.value?.masters || [],
      Slave: (data.value?.slaves || []).map((item) => ({
        ...item,
        isStandBy: item.is_stand_by,
      })),
    };
    /* eslint-enable perfectionist/sort-objects */
  });

  const isShowDumperEntry = computed(() => {
    const currentKey = `dumper_biz_${window.PROJECT_CONFIG.BIZ_ID}` as MySQLFunctions;
    return funControllerStore.funControllerData.mysql.children[currentKey];
  });

  const { loading: isLoading, run: fetchClusterDetail } = useRequest(getTendbhaDetail, {
    manual: true,
    onSuccess(result) {
      data.value = result;
    },
  });

  const fetchDetailData = () => {
    fetchClusterDetail({
      id: props.clusterId,
    });
  };

  const { handleDeleteCluster, handleDisableCluster, handleEnableCluster } = useOperateClusterBasic(
    ClusterTypes.TENDBHA,
    {
      onSuccess: () => {
        fetchDetailData();
        emits('change');
      },
    },
  );

  watch(
    () => props.clusterId,
    () => {
      if (!props.clusterId) {
        return;
      }
      fetchDetailData();
    },
    {
      immediate: true,
    },
  );

  const handleShowAuthorize = () => {
    isAuthorizeShow.value = true;
  };

  const handleShowDataExportSlider = () => {
    isShowDataExport.value = true;
  };

  const handleShowCreateSubscribeRuleSlider = () => {
    isShowCreateSubscribeRule.value = true;
  };
</script>

<style lang="less">
  .cluster-detail-dialog-mode {
    height: 100%;
    min-height: 500px;
    background: #fff;
  }
</style>
