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
        cluster-detail-router-name="MongoDBReplicaSetDetail"
        :data="data">
        <BkButton
          v-db-console="'mongodb.replicaSetList.authorize'"
          class="ml-4"
          :disabled="data.isOffline"
          size="small"
          @click="handleShowAuthorize">
          {{ t('授权') }}
        </BkButton>
        <BkButton
          v-db-console="'mongodb.replicaSetList.getAccess'"
          class="ml-4"
          :disabled="data.isOffline"
          size="small"
          @click="handleShowAccessEntry">
          {{ t('获取访问方式') }}
        </BkButton>
        <AuthRouterLink
          action-id="mongodb_webconsole"
          class="ml-4"
          :disabled="data.isOffline"
          :permission="data.permission.mongodb_webconsole"
          :resource="data.id"
          target="_blank"
          :to="{
            name: 'MongodbWebconsole',
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
        <MoreActionExtend trigger="hover">
          <template #handler>
            <BkButton
              v-bk-tooltips="t('更多操作')"
              class="ml-4"
              size="small"
              style="padding: 0 6px">
              <DbIcon type="more" />
            </BkButton>
          </template>
          <BkDropdownItem v-db-console="'mongodb.replicaSetList.capacityChange'">
            <OperationBtnStatusTips :data="data">
              <BkButton
                :disabled="Boolean(data.isStructCluster) || data.operationDisabled"
                text
                @click="handleToCapacityChange">
                {{ t('集群容量变更') }}
              </BkButton>
            </OperationBtnStatusTips>
          </BkDropdownItem>
          <BkDropdownItem
            v-if="data.isOffline"
            v-db-console="'mongodb.replicaSetList.enable'">
            <OperationBtnStatusTips :data="data">
              <BkButton
                :disabled="data.isStarting || data.isOnline"
                text
                @click="handleEnableCluster([data])">
                {{ t('启用') }}
              </BkButton>
            </OperationBtnStatusTips>
          </BkDropdownItem>
          <BkDropdownItem
            v-if="data.isOnline"
            v-db-console="'mongodb.replicaSetList.disable'">
            <OperationBtnStatusTips :data="data">
              <BkButton
                :disabled="Boolean(data.operationTicketId)"
                text
                @click="handleDisableCluster([data])">
                {{ t('禁用') }}
              </BkButton>
            </OperationBtnStatusTips>
          </BkDropdownItem>
          <BkDropdownItem v-db-console="'mongodb.replicaSetList.delete'">
            <OperationBtnStatusTips :data="data">
              <BkButton
                v-bk-tooltips="{
                  disabled: data.isOffline,
                  content: t('请先禁用集群'),
                }"
                :disabled="data.isOnline || Boolean(data.operationTicketId)"
                text
                @click="handleDeleteCluster([data])">
                {{ t('删除') }}
              </BkButton>
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
        :cluster-type="ClusterTypes.MONGO_REPLICA_SET">
        <template #infoContent>
          <BaseInfo
            :data="data"
            @refresh="fetchDetailData" />
        </template>
        <template #instanceContent>
          <InstanceList
            :cluster-id="data.id"
            :cluster-type="ClusterTypes.MONGO_REPLICA_SET" />
        </template>
      </ActionPanel>
      <!-- 集群授权 -->
      <ClusterAuthorize
        v-model="isAuthorizeShow"
        :account-type="AccountTypes.MONGODB"
        :cluster-types="[ClusterTypes.MONGO_REPLICA_SET]"
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

  import { AccountTypes, ClusterTypes, TicketTypes } from '@common/const';

  import MoreActionExtend from '@components/more-action-extend/Index.vue';

  import ClusterAuthorize from '@views/db-manage/common/cluster-authorize/Index.vue';
  import { ActionPanel, DisplayBox } from '@views/db-manage/common/cluster-details';
  import ClusterDomainDnsRelation from '@views/db-manage/common/cluster-domain-dns-relation/Index.vue';
  import { useOperateClusterBasic } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import InstanceList from '@views/db-manage/mongodb/common/ClusterDetailInstanceList.vue';
  import AccessEntry from '@views/db-manage/mongodb/components/AccessEntry.vue';

  import BaseInfo from './components/BaseInfo.vue';

  interface Props {
    clusterId: number;
  }

  type Emits = (e: 'change') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const router = useRouter();

  const data = ref<MongodbDetailModel>();

  /** 集群授权 */
  const isAuthorizeShow = ref(false);
  const isShowAccessEntryInfo = ref(false);

  const clusterRoleNodeGroup = computed(() => {
    return {
      [t('节点')]: data.value?.mongodb || [],
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

  const handleToCapacityChange = () => {
    const routeInfo = router.resolve({
      name: TicketTypes.MONGODB_SCALE_UPDOWN,
      query: {
        masterDomain: data.value!.master_domain,
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
