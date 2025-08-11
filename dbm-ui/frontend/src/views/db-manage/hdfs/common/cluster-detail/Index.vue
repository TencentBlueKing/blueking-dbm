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
        cluster-detail-router-name="hdfsDetail"
        :data="data">
        <a
          v-db-console="'hdfs.clusterManage.manage'"
          class="ml-4"
          :href="data.access_url"
          target="_blank">
          <BkButton
            :disabled="data.isOffline"
            size="small">
            WebUI
          </BkButton>
        </a>
        <AuthButton
          v-db-console="'hdfs.clusterManage.getAccess'"
          action-id="hdfs_access_entry_view"
          class="ml-4"
          :disabled="data.isOffline"
          :permission="data.permission.hdfs_access_entry_view"
          :resource="data.id"
          size="small"
          @click="handleShowPassword">
          {{ t('获取访问方式') }}
        </AuthButton>
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
          <BkDropdownItem v-db-console="'hdfs.clusterManage.scaleUp'">
            <OperationBtnStatusTips :data="data">
              <AuthButton
                action-id="hdfs_scale_up"
                :disabled="data.operationDisabled"
                :permission="data.permission.hdfs_scale_up"
                :resource="data.id"
                text
                @click="handleShowExpansion">
                {{ t('扩容') }}
              </AuthButton>
            </OperationBtnStatusTips>
          </BkDropdownItem>
          <BkDropdownItem v-db-console="'hdfs.clusterManage.scaleDown'">
            <OperationBtnStatusTips :data="data">
              <AuthButton
                action-id="hdfs_shrink"
                :disabled="data.operationDisabled"
                :permission="data.permission.hdfs_shrink"
                :resource="data.id"
                text
                @click="handleShowShrink">
                {{ t('缩容') }}
              </AuthButton>
            </OperationBtnStatusTips>
          </BkDropdownItem>
          <BkDropdownItem v-db-console="'hdfs.clusterManage.viewAccessConfiguration'">
            <div style="display: inline-block">
              <AuthButton
                action-id="hdfs_view"
                :disabled="data.isOffline"
                :permission="data.permission.hdfs_view"
                :resource="data.id"
                text
                @click="handleShowSettings">
                {{ t('查看访问配置') }}
              </AuthButton>
            </div>
          </BkDropdownItem>
          <BkDropdownItem
            v-if="data.isOffline"
            v-db-console="'hdfs.clusterManage.enable'">
            <OperationBtnStatusTips :data="data">
              <AuthButton
                action-id="hdfs_enable_disable"
                class="mr-8"
                :disabled="data.isStarting"
                :permission="data.permission.hdfs_enable_disable"
                :resource="data.id"
                text
                @click="handleEnableCluster([data])">
                {{ t('启用') }}
              </AuthButton>
            </OperationBtnStatusTips>
          </BkDropdownItem>
          <BkDropdownItem
            v-else
            v-db-console="'hdfs.clusterManage.disable'">
            <OperationBtnStatusTips :data="data">
              <AuthButton
                action-id="hdfs_enable_disable"
                :disabled="Boolean(data.operationTicketId)"
                :permission="data.permission.hdfs_enable_disable"
                :resource="data.id"
                text
                @click="handleDisableCluster([data])">
                {{ t('禁用') }}
              </AuthButton>
            </OperationBtnStatusTips>
          </BkDropdownItem>
          <BkDropdownItem v-db-console="'hdfs.clusterManage.delete'">
            <OperationBtnStatusTips :data="data">
              <AuthButton
                v-bk-tooltips="{
                  disabled: data.isOffline,
                  content: t('请先禁用集群'),
                }"
                action-id="hdfs_destroy"
                :disabled="data.isOnline || Boolean(data.operationTicketId)"
                :permission="data.permission.hdfs_destroy"
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
        :cluster-type="ClusterTypes.HDFS">
        <template #infoContent>
          <BaseInfo
            :cluster-type="ClusterTypes.HDFS"
            :data="data"
            @refresh="fetchDetailData">
          </BaseInfo>
        </template>
        <template #hostContent>
          <HostList :cluster-data="data" />
        </template>
        <template #instanceContent>
          <BigDataInstanceList
            :cluster-data="data"
            :cluster-type="ClusterTypes.HDFS" />
        </template>
      </ActionPanel>
      <DbSideslider
        v-model:is-show="isShowExpandsion"
        background-color="#F5F7FA"
        class="hdfs-manage-sideslider"
        quick-close
        :title="t('xx扩容【name】', { title: 'HDFS', name: data?.cluster_name })"
        :width="960">
        <ClusterExpansion :data="data" />
      </DbSideslider>
      <DbSideslider
        v-model:is-show="isShowShrink"
        background-color="#F5F7FA"
        class="hdfs-manage-sideslider"
        quick-close
        :title="t('xx缩容【name】', { title: 'HDFS', name: data?.cluster_name })"
        :width="960">
        <ClusterShrink
          :cluster-id="data.id"
          :data="data" />
      </DbSideslider>
      <BkDialog
        v-model:is-show="isShowPassword"
        render-directive="if"
        :title="t('获取访问方式')"
        :width="500">
        <RenderPassword
          v-if="data"
          :cluster-id="data.id"
          :db-type="DBTypes.HDFS" />
        <template #footer>
          <BkButton @click="handleHidePassword">
            {{ t('关闭') }}
          </BkButton>
        </template>
      </BkDialog>
      <BkDialog
        v-model:is-show="isShowPassword"
        render-directive="if"
        :title="t('获取访问方式')"
        :width="500">
        <RenderPassword
          v-if="data"
          :cluster-id="data.id"
          :db-type="DBTypes.ES" />
        <template #footer>
          <BkButton @click="handleHidePassword">
            {{ t('关闭') }}
          </BkButton>
        </template>
      </BkDialog>
    </template>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import HdfsDetailModel from '@services/model/hdfs/hdfs-detail';
  import { getHdfsDetail } from '@services/source/hdfs';

  import { ClusterTypes, DBTypes } from '@common/const';

  import MoreActionExtend from '@components/more-action-extend/Index.vue';

  import { ActionPanel, BaseInfo, BigDataInstanceList, DisplayBox } from '@views/db-manage/common/cluster-details';
  import ClusterDomainDnsRelation from '@views/db-manage/common/cluster-domain-dns-relation/Index.vue';
  import { useOperateClusterBasic } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import RenderPassword from '@views/db-manage/common/RenderPassword.vue';
  import ClusterExpansion from '@views/db-manage/hdfs/common/expansion/Index.vue';
  import ClusterShrink from '@views/db-manage/hdfs/common/shrink/Index.vue';

  import HostList from './components/HostList.vue';

  interface Props {
    clusterId: number;
  }

  type Emits = (e: 'change') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const data = ref<HdfsDetailModel>();

  const isShowExpandsion = ref(false);
  const isShowShrink = ref(false);
  const isShowPassword = ref(false);
  const isShowSettings = ref(false);

  const clusterRoleNodeGroup = computed(() => {
    /* eslint-disable perfectionist/sort-objects */
    return {
      NameNode: data.value?.hdfs_namenode || [],
      Zookeeper: data.value?.hdfs_zookeeper || [],
      Journalnode: data.value?.hdfs_journalnode || [],
      DataNode: data.value?.hdfs_datanode || [],
    };
    /* eslint-enable perfectionist/sort-objects */
  });

  const { loading: isLoading, run: fetchClusterDetail } = useRequest(getHdfsDetail, {
    manual: true,
    onSuccess(result: HdfsDetailModel) {
      data.value = result;
    },
  });

  const fetchDetailData = () => {
    fetchClusterDetail({
      id: props.clusterId,
    });
  };

  const { handleDeleteCluster, handleDisableCluster, handleEnableCluster } = useOperateClusterBasic(ClusterTypes.HDFS, {
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

  // 扩容
  const handleShowExpansion = () => {
    isShowExpandsion.value = true;
  };

  // 缩容
  const handleShowShrink = () => {
    isShowShrink.value = true;
  };

  const handleShowPassword = () => {
    isShowPassword.value = true;
  };

  const handleHidePassword = () => {
    isShowPassword.value = false;
  };

  const handleShowSettings = () => {
    isShowSettings.value = true;
  };
</script>

<style lang="less">
  .cluster-detail-dialog-mode {
    height: 100%;
    min-height: 500px;
    background: #fff;
  }
</style>
