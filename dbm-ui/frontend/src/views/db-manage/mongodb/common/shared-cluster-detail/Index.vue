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
        cluster-detail-router-name="MongoDBSharedClusterDetail"
        :data="data">
        <template v-if="data.isOnline">
          <AuthButton
            v-db-console="'mongodb.sharedClusterList.importAuthorize'"
            action-id="mongodb_priv_manage"
            class="ml-4"
            :permission="data.permission.mongodb_priv_manage"
            size="small"
            @click="handleShowAuthorize">
            {{ t('授权') }}
          </AuthButton>
          <AuthButton
            v-db-console="'mongodb.sharedClusterList.getAccess'"
            action-id="mongodb_access_entry_view"
            class="ml-4"
            :permission="data.permission.mongodb_access_entry_view"
            :resource="data.id"
            size="small"
            @click="handleShowAccessEntry">
            {{ t('获取访问方式') }}
          </AuthButton>
          <AuthRouterLink
            v-db-console="'mongodb.sharedClusterList.webconsole'"
            action-id="mongodb_webconsole"
            class="ml-4"
            :permission="data.permission.mongodb_webconsole"
            :resource="data.id"
            target="_blank"
            :to="{
              name: 'MongodbWebconsole',
              query: {
                clusterId: props.clusterId,
              },
            }">
            <BkButton size="small"> Webconsole </BkButton>
          </AuthRouterLink>
        </template>
        <MoreActionExtend>
          <template #trigger>
            <BkButton
              class="ml-4"
              size="small"
              style="padding: 0 6px">
              <DbIcon type="more" />
            </BkButton>
          </template>
          <template v-if="data.isOnline">
            <div v-db-console="'mongodb.sharedClusterList.queryAccessSource'">
              <OperationBtnStatusTips
                :data="data"
                :disabled="!data.isOffline">
                <AuthButton
                  action-id="mongodb_source_access_view"
                  :permission="data.permission.mongodb_source_access_view"
                  :resource="data.id"
                  style="width: 100%; height: 32px"
                  text
                  @click="handleGoQueryAccessSourcePage(data.master_domain)">
                  {{ t('查询访问来源') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
            <div
              v-if="!data.isOnlineCLB"
              v-db-console="'common.clb'">
              <OperationBtnStatusTips
                :data="data"
                :disabled="!data.isOffline">
                <AuthButton
                  action-id="mongodb_loadbalance_manage"
                  :permission="data.permission.mongodb_loadbalance_manage"
                  :resource="data.id"
                  text
                  @click="handleAddClb({ details: { cluster_id: data.id } })">
                  {{ t('启用CLB') }}
                </AuthButton>
              </OperationBtnStatusTips>
            </div>
          </template>
          <div
            v-if="data.isOnline"
            v-db-console="'mongodb.sharedClusterList.disable'">
            <OperationBtnStatusTips :data="data">
              <AuthButton
                action-id="mongodb_enable_disable"
                :disabled="Boolean(data.operationTicketId)"
                :permission="data.permission.mongodb_enable_disable"
                :resource="data.id"
                text
                @click="handleDisableCluster([data])">
                {{ t('禁用') }}
              </AuthButton>
            </OperationBtnStatusTips>
          </div>
          <div
            v-else
            v-db-console="'mongodb.sharedClusterList.enable'">
            <OperationBtnStatusTips :data="data">
              <AuthButton
                action-id="mongodb_enable_disable"
                :disabled="data.isStarting"
                :permission="data.permission.mongodb_enable_disable"
                :resource="data.id"
                text
                @click="handleEnableCluster([data])">
                {{ t('启用') }}
              </AuthButton>
            </OperationBtnStatusTips>
          </div>
          <div v-db-console="'mongodb.sharedClusterList.delete'">
            <OperationBtnStatusTips :data="data">
              <AuthButton
                v-bk-tooltips="{
                  disabled: data.isOffline,
                  content: t('删除前需先禁用集群'),
                }"
                action-id="mongodb_destroy"
                :disabled="data.isOnline || Boolean(data.operationTicketId)"
                :permission="data.permission.mongodb_destroy"
                :resource="data.id"
                text
                @click="handleDeleteCluster([data])">
                {{ t('删除') }}
              </AuthButton>
            </OperationBtnStatusTips>
          </div>
          <ClusterDomainDnsRelation
            v-if="data.isOnline"
            :data="data" />
        </MoreActionExtend>
      </DisplayBox>
      <ActionPanel
        :cluster-data="data"
        :cluster-role-node-group="clusterRoleNodeGroup"
        :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER">
        <template #infoContent>
          <BaseInfo
            :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER"
            :data="data"
            @refresh="fetchDetailData">
            <template #clbMaster>
              <ClbInfo
                :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER"
                :data="data" />
            </template>
          </BaseInfo>
        </template>
        <template #instanceContent>
          <InstanceList
            :cluster-id="data.id"
            :cluster-type="ClusterTypes.MONGO_SHARED_CLUSTER" />
        </template>
      </ActionPanel>
      <!-- 集群授权 -->
      <ClusterAuthorize
        v-model="isAuthorizeShow"
        :account-type="AccountTypes.MONGODB"
        :cluster-types="[ClusterTypes.MONGO_SHARED_CLUSTER]"
        :selected="[data]" />
      <AccessEntry
        v-model:is-show="isShowAccessEntryInfo"
        :data="data" />
    </template>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRouter } from 'vue-router';

  import MongodbDetailModel from '@services/model/mongodb/mongodb-detail';
  import { getMongoClusterDetails } from '@services/source/mongodb';

  import { AccountTypes, ClusterTypes } from '@common/const';

  import MoreActionExtend from '@components/more-action-extend/Index.vue';

  import ClusterAuthorize from '@views/db-manage/common/cluster-authorize/Index.vue';
  import { ActionPanel, BaseInfo, BaseInfoField, DisplayBox } from '@views/db-manage/common/cluster-details';
  import ClusterDomainDnsRelation from '@views/db-manage/common/cluster-domain-dns-relation/Index.vue';
  import { useAddClb, useOperateClusterBasic } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import AccessEntry from '@views/db-manage/mongodb/common/cluster-operations/AccessEntry.vue';
  import InstanceList from '@views/db-manage/mongodb/common/ClusterDetailInstanceList.vue';

  interface Props {
    clusterId: number;
  }

  type Emits = (e: 'change') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { ClbInfo } = BaseInfoField;

  const { t } = useI18n();
  const router = useRouter();

  const data = ref<MongodbDetailModel>();

  const isAuthorizeShow = ref(false);
  const isShowAccessEntryInfo = ref(false);

  const clusterRoleNodeGroup = computed(() => {
    return {
      ConfigSvr: data.value?.mongo_config || [],
      Mongos: data.value?.mongos || [],
      ShardSvr: data.value?.mongodb || [],
    };
  });

  const { loading: isLoading, run: fetchClusterDetail } = useRequest(getMongoClusterDetails, {
    manual: true,
    onSuccess(result: MongodbDetailModel) {
      data.value = result;
    },
  });

  const fetchDetailData = () => {
    fetchClusterDetail({
      cluster_id: props.clusterId,
    });
  };

  const { handleDeleteCluster, handleDisableCluster, handleEnableCluster } = useOperateClusterBasic(
    ClusterTypes.MONGODB,
    {
      onSuccess: () => {
        fetchDetailData();
        emits('change');
      },
    },
  );

  const { handleAddClb } = useAddClb<{ cluster_id: number }>(ClusterTypes.MONGO_SHARED_CLUSTER);

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

  const handleGoQueryAccessSourcePage = (masterDomain: string) => {
    const routeInfo = router.resolve({
      name: 'MongodbQueryAccessSource',
      query: {
        masterDomain,
      },
    });
    window.open(routeInfo.href, '_blank');
  };

  const handleShowAuthorize = () => {
    isAuthorizeShow.value = true;
  };

  const handleShowAccessEntry = () => {
    isShowAccessEntryInfo.value = true;
  };
</script>

<style lang="less">
  .cluster-detail-dialog-mode {
    height: 100%;
    min-height: 500px;
    background: #fff;
  }
</style>
