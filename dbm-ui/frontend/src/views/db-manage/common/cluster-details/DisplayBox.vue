<template>
  <div class="cluster-detail-display-box">
    <div class="row-item">
      <div class="cluster-domain">
        {{ data.masterDomain }}
      </div>
      <slot name="clb">
        <div
          v-if="data.isOnlineCLB"
          class="ml-4">
          <ClusterEntryPanel
            :cluster-id="data.id"
            entry-type="clb"
            size="big" />
        </div>
      </slot>
      <div
        v-if="data.isOnlinePolaris"
        class="ml-4">
        <ClusterEntryPanel
          :cluster-id="data.id"
          entry-type="polaris"
          :panel-width="418"
          size="big" />
      </div>
      <CluterRelatedTicket
        v-if="data.operations.length > 0"
        class="ml-4"
        :data="data.operations"
        size="big" />
      <BkTag
        v-if="data.isOffline"
        class="ml-4"
        theme="warning"
        type="stroke">
        {{ t('已禁用') }}
      </BkTag>
      <slot />
      <BkDropdown
        class="ml-4 mr-20"
        placement="bottom-start">
        <div
          v-bk-tooltips="t('复制')"
          style="font-size: 18px; color: #3a84ff">
          <DbIcon type="links" />
        </div>
        <template #content>
          <BkDropdownItem @click="handleCopyClusterMasterDomainAndLink">
            {{ t('集群域名 + 集群链接') }}
          </BkDropdownItem>
          <BkDropdownItem @click="handleCopyDetailPageLink">
            {{ t('集群链接') }}
          </BkDropdownItem>
        </template>
      </BkDropdown>
      <RouterLink
        v-if="!isDetailRouterPage"
        style="margin-left: auto"
        target="_blank"
        :to="{
          name: clusterDetailRouterName,
          params: {
            clusterId: props.data.id,
          },
        }">
        <DbIcon
          class="mr-4"
          type="link" />
        {{ t('新窗口打开') }}
      </RouterLink>
    </div>
    <div class="row-item">
      <div class="item-label pr-4">ID:</div>
      <div>{{ data.id || '--' }}</div>
      <div class="item-label ml-16 pr-4">{{ t('集群名称') }}:</div>
      <div>{{ data.cluster_name || '--' }}</div>
      <div class="item-label ml-16 pr-4">{{ t('状态') }}:</div>
      <div>
        <ClusterRoleStatus :data="data" />
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import type { ClusterListNode } from '@services/types';

  import ClusterEntryPanel from '@views/db-manage/common/cluster-entry-panel/Index.vue';
  import ClusterRoleStatus from '@views/db-manage/common/cluster-role-status/Index.vue';
  import CluterRelatedTicket from '@views/db-manage/common/ClusterDetailRelatedTicket.vue';

  import { execCopy, getSelfDomain } from '@utils';

  interface Props {
    clusterDetailRouterName: string;
    data: {
      isOnlineCLB?: boolean;
      isOnlinePolaris?: boolean;
      roleFailedInstanceInfo: Record<string, ClusterListNode[]>;
    } & Pick<
      TendbhaModel,
      | 'masterDomain'
      | 'cluster_name'
      | 'region'
      | 'operationTagTips'
      | 'id'
      | 'isOffline'
      | 'isStarting'
      | 'operations'
      | 'id'
      | 'status'
    >;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();

  const isDetailRouterPage = props.clusterDetailRouterName === (route.name as string);

  const handleCopyClusterMasterDomainAndLink = () => {
    const { href } = router.resolve({
      name: props.clusterDetailRouterName,
      params: {
        clusterId: props.data.id,
      },
    });

    execCopy(`${props.data.masterDomain}\n${getSelfDomain()}${href}`);
  };

  const handleCopyDetailPageLink = () => {
    const { href } = router.resolve({
      name: props.clusterDetailRouterName,
      params: {
        clusterId: props.data.id,
      },
    });
    execCopy(`${getSelfDomain()}${href}`);
  };
</script>
<style lang="less">
  .cluster-detail-display-box {
    padding: 16px 60px 16px 20px;
    font-size: 12px;
    line-height: 20px;
    color: #313238;
    white-space: nowrap;
    background: #f0f1f5;

    .row-item {
      display: flex;
      align-items: center;

      & ~ .row-item {
        margin-top: 4px;
      }
    }

    .cluster-domain {
      overflow: hidden;
      font-size: 16px;
      font-weight: 700;
      line-height: 24px;
      color: #313238;
      text-overflow: ellipsis;
      word-break: break-all;
    }

    .item-label {
      color: #979ba5;
    }
  }
</style>
