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
        cluster-detail-router-name="riakDetail"
        :data="data">
        <OperationBtnStatusTips
          v-db-console="'riak.clusterManage.addNodes'"
          :data="data">
          <AuthButton
            action-id="riak_cluster_scale_in"
            class="ml-4"
            :disabled="data.isOffline"
            :permission="data.permission.riak_cluster_scale_in"
            :resource="data.id"
            size="small"
            @click="handleAddNodes">
            {{ t('添加节点') }}
          </AuthButton>
        </OperationBtnStatusTips>
        <OperationBtnStatusTips
          v-db-console="'riak.clusterManage.deleteNodes'"
          :data="data">
          <AuthButton
            action-id="riak_cluster_scale_out"
            class="ml-4"
            :disabled="data.isOffline"
            :permission="data.permission.riak_cluster_scale_out"
            :resource="data.id"
            size="small"
            @click="handleDeleteNodes">
            {{ t('删除节点') }}
          </AuthButton>
        </OperationBtnStatusTips>
        <OperationBtnStatusTips
          v-db-console="'riak.clusterManage.disable'"
          :data="data">
          <AuthButton
            action-id="riak_enable_disable"
            class="ml-4"
            :disabled="data.isOffline || Boolean(data.operationTicketId)"
            :permission="data.permission.riak_enable_disable"
            :resource="data.id"
            size="small"
            @click="handleDisableCluster([data])">
            {{ t('禁用') }}
          </AuthButton>
        </OperationBtnStatusTips>
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
          <BkDropdownItem v-db-console="'riak.clusterManage.enable'">
            <OperationBtnStatusTips :data="data">
              <AuthButton
                action-id="riak_enable_disable"
                :disabled="data.isOnline || data.isStarting"
                :permission="data.permission.riak_enable_disable"
                :resource="data.id"
                text
                @click="handleEnableCluster([data])">
                {{ t('启用') }}
              </AuthButton>
            </OperationBtnStatusTips>
          </BkDropdownItem>
          <BkDropdownItem v-db-console="'riak.clusterManage.delete'">
            <OperationBtnStatusTips :data="data">
              <AuthButton
                v-bk-tooltips="{
                  disabled: data.isOffline,
                  content: t('请先禁用集群'),
                }"
                action-id="riak_cluster_destroy"
                :disabled="data.isOnline || Boolean(data.operationTicketId)"
                :permission="data.permission.riak_cluster_destroy"
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
        :cluster-type="ClusterTypes.RIAK">
        <template #infoContent>
          <BaseInfo
            :data="data"
            @refresh="fetchDetailData" />
        </template>
      </ActionPanel>
    </template>

    <DbSideslider
      v-if="data"
      v-model:is-show="isShowAddNode"
      quick-close
      :title="t('添加节点【xx】', [data.cluster_name])"
      :width="960">
      <AddNodes :data="data" />
    </DbSideslider>
    <DbSideslider
      v-if="data"
      v-model:is-show="isShowDeleteNode"
      :title="t('删除节点【xx】', [data.cluster_name])"
      :width="960">
      <DeleteNodes :data="data" />
    </DbSideslider>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import RiakModel from '@services/model/riak/riak';
  import { getRiakDetail } from '@services/source/riak';

  import { ClusterTypes } from '@common/const';

  import MoreActionExtend from '@components/more-action-extend/Index.vue';

  import { ActionPanel, DisplayBox } from '@views/db-manage/common/cluster-details';
  import ClusterDomainDnsRelation from '@views/db-manage/common/cluster-domain-dns-relation/Index.vue';
  import { useOperateClusterBasic } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import AddNodes from '@views/db-manage/riak/common/AddNodes.vue';
  import DeleteNodes from '@views/db-manage/riak/common/DeleteNodes.vue';

  import BaseInfo from './components/BaseInfo.vue';

  interface Props {
    clusterId: number;
  }

  type Emits = (e: 'change') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const data = ref<RiakModel>();
  const isShowAddNode = ref(false);
  const isShowDeleteNode = ref(false);

  const clusterRoleNodeGroup = computed(() => {
    return {
      [t('节点')]: data.value?.riak_node || [],
    };
  });

  const { loading: isLoading, run: fetchClusterDetail } = useRequest(getRiakDetail, {
    manual: true,
    onSuccess(result: RiakModel) {
      data.value = result;
    },
  });

  const fetchDetailData = () => {
    fetchClusterDetail({
      id: props.clusterId,
    });
  };

  const { handleDeleteCluster, handleDisableCluster, handleEnableCluster } = useOperateClusterBasic(ClusterTypes.RIAK, {
    onSuccess: () => {
      fetchDetailData();
      emits('change');
    },
  });

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

  const handleAddNodes = () => {
    isShowAddNode.value = true;
  };

  const handleDeleteNodes = () => {
    isShowDeleteNode.value = true;
  };
</script>

<style lang="less">
  .cluster-detail-dialog-mode {
    height: 100%;
    min-height: 500px;
    background: #fff;
  }
</style>
