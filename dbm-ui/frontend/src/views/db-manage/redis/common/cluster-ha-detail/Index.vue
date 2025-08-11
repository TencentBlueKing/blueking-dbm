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
        cluster-detail-router-name="redisClusterHaDetail"
        :data="data">
        <OperationBtnStatusTips
          v-bk-tooltips="{
            content: t('暂不支持跨管控区域提取Key'),
            disabled: data.bk_cloud_id === undefined,
          }"
          v-db-console="'redis.haClusterManage.extractKey'"
          :data="data"
          :disabled="!data.isOffline">
          <AuthButton
            action-id="redis_keys_extract"
            class="ml-4"
            :disabled="data.isOffline"
            :permission="data.permission.redis_keys_extract"
            :resource="data.id"
            size="small"
            @click="handleToToolbox(TicketTypes.REDIS_KEYS_EXTRACT, [data])">
            {{ t('提取Key') }}
          </AuthButton>
        </OperationBtnStatusTips>
        <OperationBtnStatusTips
          v-bk-tooltips="{
            content: t('暂不支持跨管控区域删除Key'),
            disabled: data.bk_cloud_id === undefined,
          }"
          v-db-console="'redis.haClusterManage.deleteKey'"
          :data="data"
          :disabled="!data.isOffline">
          <AuthButton
            action-id="redis_keys_delete"
            class="ml-4"
            :disabled="data.isOffline"
            :permission="data.permission.redis_keys_delete"
            :resource="data.id"
            size="small"
            @click="handleToToolbox(TicketTypes.REDIS_KEYS_DELETE, [data])">
            {{ t('删除Key') }}
          </AuthButton>
        </OperationBtnStatusTips>
        <AuthRouterLink
          action-id="redis_webconsole"
          class="ml-4"
          :permission="data.permission.redis_webconsole"
          :resource="data.id"
          target="_blank"
          :to="{
            name: 'RedisWebconsole',
            query: {
              clusterId: data.id,
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
          <BkDropdownItem v-db-console="'redis.haClusterManage.backup'">
            <OperationBtnStatusTips
              :data="data"
              :disabled="!data.isOffline">
              <AuthButton
                action-id="redis_backup"
                :disabled="data.isOffline"
                :permission="data.permission.redis_backup"
                :resource="data.id"
                style="width: 100%; height: 32px"
                text
                @click="handleToToolbox(TicketTypes.REDIS_BACKUP, [data])">
                {{ t('备份') }}
              </AuthButton>
            </OperationBtnStatusTips>
          </BkDropdownItem>
          <BkDropdownItem v-db-console="'redis.haClusterManage.dbClear'">
            <OperationBtnStatusTips
              :data="data"
              :disabled="!data.isOffline">
              <AuthButton
                action-id="redis_purge"
                :disabled="data.isOffline"
                :permission="data.permission.redis_purge"
                :resource="data.id"
                style="width: 100%; height: 32px"
                text
                @click="handleToToolbox(TicketTypes.REDIS_PURGE, [data])">
                {{ t('清档') }}
              </AuthButton>
            </OperationBtnStatusTips>
          </BkDropdownItem>
          <BkDropdownItem v-db-console="'redis.haClusterManage.getAccess'">
            <OperationBtnStatusTips
              :data="data"
              :disabled="!data.isOffline">
              <AuthButton
                action-id="redis_access_entry_view"
                :disabled="data.isOffline"
                :permission="data.permission.redis_access_entry_view"
                :resource="data.id"
                style="width: 100%; height: 32px"
                text
                @click="handleShowPassword(data.id)">
                {{ t('获取访问方式') }}
              </AuthButton>
            </OperationBtnStatusTips>
          </BkDropdownItem>
          <BkDropdownItem v-db-console="'redis.haClusterManage.queryAccessSource'">
            <OperationBtnStatusTips
              :data="data"
              :disabled="!data.isOffline">
              <AuthButton
                action-id="redis_source_access_view"
                :disabled="data.isOffline"
                :permission="data.permission.redis_source_access_view"
                :resource="data.id"
                style="width: 100%; height: 32px"
                text
                @click="handleGoQueryAccessSourcePage(data.master_domain)">
                {{ t('查询访问来源') }}
              </AuthButton>
            </OperationBtnStatusTips>
          </BkDropdownItem>
          <BkDropdownItem
            v-if="data.isOnline"
            v-db-console="'redis.haClusterManage.disable'">
            <OperationBtnStatusTips :data="data">
              <AuthButton
                action-id="redis_open_close"
                :disabled="Boolean(data.operationTicketId)"
                :permission="data.permission.redis_open_close"
                :resource="data.id"
                style="width: 100%; height: 32px"
                text
                @click="handleDisableCluster([data])">
                {{ t('禁用') }}
              </AuthButton>
            </OperationBtnStatusTips>
          </BkDropdownItem>
          <BkDropdownItem
            v-if="data.isOffline"
            v-db-console="'redis.haClusterManage.enable'">
            <OperationBtnStatusTips :data="data">
              <AuthButton
                action-id="redis_open_close"
                :disabled="data.isStarting"
                :permission="data.permission.redis_open_close"
                :resource="data.id"
                style="width: 100%; height: 32px"
                text
                @click="handleEnableCluster([data])">
                {{ t('启用') }}
              </AuthButton>
            </OperationBtnStatusTips>
          </BkDropdownItem>
          <BkDropdownItem v-db-console="'redis.haClusterManage.delete'">
            <OperationBtnStatusTips :data="data">
              <AuthButton
                v-bk-tooltips="{
                  disabled: data.isOffline,
                  content: t('请先禁用集群'),
                }"
                action-id="redis_destroy"
                :disabled="data.isOnline || Boolean(data.operationTicketId)"
                :permission="data.permission.redis_destroy"
                :resource="data.id"
                style="width: 100%; height: 32px"
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
        :cluster-type="ClusterTypes.REDIS_INSTANCE">
        <template #infoContent>
          <BaseInfo
            :cluster-type="ClusterTypes.REDIS_INSTANCE"
            :data="data"
            @refresh="fetchDetailData">
            <template #slaveDomain>
              <SlaveDomain
                :cluster-type="ClusterTypes.REDIS_INSTANCE"
                :data="data.slaveEntryList" />
            </template>
            <template #moduleNames>
              <TagBlock :data="data.module_names" />
            </template>
          </BaseInfo>
        </template>
      </ActionPanel>
    </template>
    <ClusterPassword
      v-model:is-show="passwordState.isShow"
      :fetch-params="passwordState.fetchParams"
      :show-clb="false" />
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';
  import { useRouter } from 'vue-router';

  import RedisDetailModel from '@services/model/redis/redis-detail';
  import { getRedisDetail } from '@services/source/redis';

  import { ClusterTypes, DBTypes, TicketTypes } from '@common/const';

  import MoreActionExtend from '@components/more-action-extend/Index.vue';
  import TagBlock from '@components/tag-block/Index.vue';

  import { ActionPanel, BaseInfo, DisplayBox, SlaveDomain } from '@views/db-manage/common/cluster-details';
  import ClusterDomainDnsRelation from '@views/db-manage/common/cluster-domain-dns-relation/Index.vue';
  import { useOperateClusterBasic, useRedisClusterListToToolbox } from '@views/db-manage/common/hooks';
  import OperationBtnStatusTips from '@views/db-manage/common/OperationBtnStatusTips.vue';
  import ClusterPassword from '@views/db-manage/redis/common/cluster-oprations/ClusterPassword.vue';

  interface Props {
    clusterId: number;
  }

  type Emits = (e: 'change') => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const router = useRouter();

  const { handleToToolbox } = useRedisClusterListToToolbox();

  const data = ref<RedisDetailModel>();

  const passwordState = reactive({
    fetchParams: {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      cluster_id: -1,
      db_type: DBTypes.REDIS,
      type: DBTypes.REDIS,
    },
    isShow: false,
  });

  const clusterRoleNodeGroup = computed(() => {
    return {
      Master: data.value?.redis_master || [],
      Slave: data.value?.redis_slave || [],
    };
  });

  const { loading: isLoading, run: fetchClusterDetail } = useRequest(getRedisDetail, {
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
    ClusterTypes.REDIS_INSTANCE,
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

  const handleGoQueryAccessSourcePage = (domain: string) => {
    const url = router.resolve({
      name: 'RedisQueryAccessSource',
      query: {
        domain,
      },
    });
    window.open(url.href);
  };

  const handleShowPassword = (id: number) => {
    passwordState.isShow = true;
    passwordState.fetchParams.cluster_id = id;
  };
</script>

<style lang="less">
  .cluster-detail-dialog-mode {
    height: 100%;
    min-height: 500px;
    background: #fff;
  }
</style>
