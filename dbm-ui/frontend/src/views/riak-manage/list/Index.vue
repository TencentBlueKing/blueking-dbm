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
  <Teleport to="#dbContentHeaderAppend">
    <div
      v-if="headShow"
      class="riak-breadcrumbs-box">
      <BkTag>{{ detailData.cluster_name }}</BkTag>
      <div class="riak-breadcrumbs-box-status">
        <span>{{ t('状态') }} :</span>
        <RenderClusterStatus
          class="ml-8"
          :data="detailData.status" />
      </div>
      <div class="riak-breadcrumbs-box-button">
        <BkButton
          size="small"
          @click="addNodeShow = true">
          {{ t('添加节点') }}
        </BkButton>
        <BkButton
          class="ml-4"
          size="small"
          @click="deleteNodeShow = true">
          {{ t('删除节点') }}
        </BkButton>
        <BkDropdown
          class="ml-4">
          <BkButton
            class="more-button "
            size="small">
            <DbIcon type="more" />
          </BkButton>
          <template #content>
            <BkDropdownMenu>
              <BkDropdownItem>
                <BkButton
                  :disabled="detailData.operationDisabled"
                  text
                  @click="handleDisabled">
                  {{ t('禁用集群') }}
                </BkButton>
              </BkDropdownItem>
            </BkDropdownMenu>
          </template>
        </BkDropdown>
      </div>
    </div>
  </Teleport>
  <StretchLayout
    :min-left-width="368"
    name="riakClusterList">
    <template #list>
      <List
        ref="listRef"
        v-model:clusterId="clusterId"
        show-add-nodes
        @detail-open-change="handleOpenChange" />
    </template>
    <template
      v-if="clusterId"
      #right>
      <Detail
        ref="detailRef"
        :cluster-id="clusterId"
        @detail-change="handleDetailChange" />
    </template>
  </StretchLayout>
  <DbSideslider
    v-model:is-show="addNodeShow"
    quick-close
    :title="t('添加节点【xx】', [detailData.cluster_name])"
    :width="960">
    <AddNodes
      :id="detailData.id"
      :cloud-id="detailData.bk_cloud_id"
      @submit-success="handleSubmitSuccess" />
  </DbSideslider>
  <DbSideslider
    v-model:is-show="deleteNodeShow"
    :title="t('删除节点【xx】', [detailData.cluster_name])"
    :width="960">
    <DeleteNodes
      :id="detailData.id"
      :cloud-id="detailData.bk_cloud_id"
      @submit-success="handleSubmitSuccess" />
  </DbSideslider>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  import RiakModel from '@services/model/riak/riak';
  import { createTicket } from '@services/source/ticket';

  import { useTicketMessage } from '@hooks';

  import { TicketTypes } from '@common/const';

  import RenderClusterStatus from '@components/cluster-common/RenderStatus.vue';
  import StretchLayout from '@components/stretch-layout/StretchLayout.vue';

  import Detail from './components/detail/Index.vue';
  import List from './components/list/Index.vue';
  import AddNodes from './components/sideslider/AddNodes.vue';
  import DeleteNodes from './components/sideslider/DeleteNodes.vue';

  const { t } = useI18n();
  const ticketMessage = useTicketMessage();

  const listRef = ref();
  const detailRef = ref();
  const clusterId = ref(0);
  const detailData = ref(new RiakModel());
  const addNodeShow = ref(false);
  const deleteNodeShow = ref(false);
  const headShow = ref(false);

  const handleDetailChange = (data: RiakModel) => {
    detailData.value = data;
  };

  const handleOpenChange = (isOpen: boolean) => {
    headShow.value = isOpen;
  };

  const handleSubmitSuccess = () => {
    listRef.value.freshData();
  };

  const handleDisabled = () => {
    const {
      cluster_name: clusterName,
    } = detailData.value;
    InfoBox({
      title: t('确定禁用该集群', { name: clusterName }),
      subTitle: (
        <>
          <p>{ t('集群') }：<span class='info-box-cluster-name'>{ clusterName }</span></p>
          <p>{ t('被禁用后将无法访问，如需恢复访问，可以再次「启用」') }</p>
        </>
      ),
      infoType: 'warning',
      confirmText: t('禁用'),
      cancelText: t('取消'),
      headerAlign: 'center',
      contentAlign: 'center',
      footerAlign: 'center',
      onConfirm: () => {
        createTicket({
          bk_biz_id: detailData.value.bk_biz_id,
          ticket_type: TicketTypes.RIAK_CLUSTER_DISABLE,
          details: {
            cluster_id: clusterId.value,
          },
        })
          .then((createTicketResult) => {
            ticketMessage(createTicketResult.id);
          });
      },
    });
  };
</script>

<style lang="less">
.riak-breadcrumbs-box {
  display: flex;
  width: 100%;
  margin-left: 8px;
  font-size: 12px;
  align-items: center;

  .riak-breadcrumbs-box-status {
    display: flex;
    margin-left: 30px;
    align-items: center;
  }

  .riak-breadcrumbs-box-button {
    display: flex;
    margin-left: auto;
    align-items: center;

    .more-button {
      padding: 3px 6px;
    }
  }
}
</style>
