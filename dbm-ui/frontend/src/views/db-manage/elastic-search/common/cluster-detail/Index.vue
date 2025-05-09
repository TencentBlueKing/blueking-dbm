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
      <DisplayBox :data="data">
        <a
          v-db-console="'es.clusterManage.manage'"
          class="ml-8"
          :href="data.access_url"
          target="_blank">
          <BkButton size="small"> Kibana </BkButton>
        </a>
        <AuthButton
          v-db-console="'es.clusterManage.getAccess'"
          action-id="es_access_entry_view"
          class="ml-8"
          :disabled="data.isOffline"
          :permission="data.permission.es_access_entry_view"
          :resource="data.id"
          size="small"
          @click="handleShowPassword">
          {{ t('获取访问方式') }}
        </AuthButton>
        <BkDropdown placement="bottom-start">
          <BkButton
            v-bk-tooltips="t('复制')"
            class="ml-8"
            size="small"
            style="padding: 0 6px">
            <DbIcon type="copy-2" />
          </BkButton>
          <template #content>
            <BkDropdownItem @click="handleCopyClusterMasterDomainAndLink">
              {{ t('集群域名 + 集群链接') }}
            </BkDropdownItem>
            <BkDropdownItem @click="handleCopyLink">{{ t('集群链接') }}</BkDropdownItem>
          </template>
        </BkDropdown>
        <MoreActionExtend trigger="hover">
          <template #handler>
            <BkButton
              v-bk-tooltips="t('更多操作')"
              class="ml-8"
              size="small"
              style="padding: 0 6px">
              <DbIcon type="more" />
            </BkButton>
          </template>
          <BkDropdownItem v-db-console="'es.clusterManage.scaleUp'">
            <OperationBtnStatusTips :data="data">
              <AuthButton
                action-id="es_scale_up"
                :disabled="data.operationDisabled"
                :permission="data.permission.es_scale_up"
                :resource="data.id"
                text
                @click="handleShowExpandsion">
                {{ t('扩容') }}
              </AuthButton>
            </OperationBtnStatusTips>
          </BkDropdownItem>
          <BkDropdownItem v-db-console="'es.clusterManage.scaleDown'">
            <OperationBtnStatusTips :data="data">
              <AuthButton
                action-id="es_shrink"
                :disabled="data.operationDisabled"
                :permission="data.permission.es_shrink"
                :resource="data.id"
                text
                @click="handleShowShrink">
                {{ t('缩容') }}
              </AuthButton>
            </OperationBtnStatusTips>
          </BkDropdownItem>
          <BkDropdownItem
            v-if="data.isOffline"
            v-db-console="'es.clusterManage.enable'">
            <AuthButton
              action-id="es_enable_disable"
              :disabled="data.isStarting"
              :permission="data.permission.es_enable_disable"
              :resource="data.id"
              text
              @click="handleEnableCluster([data])">
              {{ t('启用') }}
            </AuthButton>
          </BkDropdownItem>
          <BkDropdownItem
            v-else
            v-db-console="'es.clusterManage.disable'">
            <OperationBtnStatusTips :data="data">
              <AuthButton
                action-id="es_enable_disable"
                :disabled="Boolean(data.operationTicketId)"
                :permission="data.permission.es_enable_disable"
                :resource="data.id"
                text
                @click="handleDisableCluster([data])">
                {{ t('禁用') }}
              </AuthButton>
            </OperationBtnStatusTips>
          </BkDropdownItem>
          <BkDropdownItem v-db-console="'es.clusterManage.delete'">
            <OperationBtnStatusTips :data="data">
              <AuthButton
                v-bk-tooltips="{
                  disabled: data.isOffline,
                  content: t('请先禁用集群'),
                }"
                action-id="es_destroy"
                :disabled="data.isOnline || Boolean(data.operationTicketId)"
                :permission="data.permission.es_destroy"
                :resource="data.id"
                text
                @click="handleDeleteCluster([data])">
                {{ t('删除') }}
              </AuthButton>
            </OperationBtnStatusTips>
          </BkDropdownItem>
        </MoreActionExtend>
        <RouterLink
          v-if="!isDetailPage"
          style="margin-left: auto"
          target="_blank"
          :to="{
            name: 'esDetail',
            params: {
              clusterId,
            },
          }">
          <DbIcon
            class="mr-4"
            type="link" />
          {{ t('新窗口打开') }}
        </RouterLink>
      </DisplayBox>
      <ActionPanel
        :cluster-data="data"
        :cluster-role-node-group="clusterRoleNodeGroup"
        :cluster-type="ClusterTypes.ES">
        <template #infoContent>
          <BaseInfo :data="data" />
        </template>
      </ActionPanel>
      <DbSideslider
        v-model:is-show="isShowExpandsion"
        background-color="#F5F7FA"
        class="es-manage-sideslider"
        :title="t('xx扩容【name】', { title: 'ES', name: data?.cluster_name })"
        :width="960">
        <ClusterExpansion
          v-if="data"
          :data="data" />
      </DbSideslider>
      <DbSideslider
        v-model:is-show="isShowShrink"
        background-color="#F5F7FA"
        class="es-manage-sideslider"
        :title="t('xx缩容【name】', { title: 'ES', name: data?.cluster_name })"
        :width="960">
        <ClusterShrink
          v-if="data"
          :cluster-id="data.id"
          :data="data"
          :node-list="[]" />
      </DbSideslider>
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
  import { useRoute, useRouter } from 'vue-router';

  import EsModel from '@services/model/es/es';
  import { getEsDetail } from '@services/source/es';

  import { ClusterTypes, DBTypes } from '@common/const';

  import MoreActionExtend from '@components/more-action-extend/Index.vue';

  import ActionPanel from '@views/db-manage/common/cluster-details/ActionPanel.vue';
  import DisplayBox from '@views/db-manage/common/cluster-details/DisplayBox.vue';
  import { useOperateClusterBasic } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import RenderPassword from '@views/db-manage/common/RenderPassword.vue';
  import ClusterExpansion from '@views/db-manage/elastic-search/common/expansion/Index.vue';

  import { execCopy, getSelfDomain } from '@utils';

  import BaseInfo from './components/BaseInfo.vue';

  interface Props {
    clusterId: number;
  }

  type Emits = (e: 'change') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();

  const isDetailPage = 'esDetail' === (route.name as string);

  const data = ref<EsModel>();

  const isShowExpandsion = ref(false);
  const isShowShrink = ref(false);
  const isShowPassword = ref(false);

  const clusterRoleNodeGroup = computed(() => {
    /* eslint-disable perfectionist/sort-objects */
    return {
      [t('Master 节点')]: data.value?.es_master || [],
      [t('Client 节点')]: data.value?.es_client || [],
      [t('热节点')]: data.value?.es_datanode_hot || [],
      [t('冷节点')]: data.value?.es_datanode_cold || [],
    };
    /* eslint-enable perfectionist/sort-objects */
  });

  const { loading: isLoading, run: fetchClusterDetail } = useRequest(getEsDetail, {
    manual: true,
    onSuccess(result: EsModel) {
      data.value = result;
    },
  });

  const { handleDeleteCluster, handleDisableCluster, handleEnableCluster } = useOperateClusterBasic(
    ClusterTypes.TENDBHA,
    {
      onSuccess: () => {
        fetchClusterDetail({
          id: props.clusterId,
        });
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
      fetchClusterDetail({
        id: props.clusterId,
      });
    },
    {
      immediate: true,
    },
  );

  // 扩容
  const handleShowExpandsion = () => {
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

  const handleCopyClusterMasterDomainAndLink = () => {
    const { href } = router.resolve({
      name: 'esDetail',
      params: {
        clusterId: props.clusterId,
      },
    });

    execCopy(`${data.value?.master_domain}\n${getSelfDomain()}${href}`);
  };

  const handleCopyLink = () => {
    const { href } = router.resolve({
      name: 'esDetail',
      params: {
        clusterId: props.clusterId,
      },
    });
    execCopy(`${getSelfDomain()}${href}`);
  };
</script>

<style lang="less">
  .cluster-detail-dialog-mode {
    height: 100%;
    min-height: 500px;
    background: #fff;
  }
</style>
