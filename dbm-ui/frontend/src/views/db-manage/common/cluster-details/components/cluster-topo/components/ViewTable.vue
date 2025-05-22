<template>
  <div class="cluster-detail-instance-table-view">
    <div
      v-for="groupName in Object.keys(clusterRoleNodeGroup)"
      :key="groupName"
      class="role-item">
      <div class="role-name">
        <span>{{ groupName }} ({{ clusterRoleNodeGroup[groupName].length }})</span>
        <PopoverCopy>
          <div @click="handleCopyHost(clusterRoleNodeGroup[groupName])">{{ t('复制IP') }}</div>
          <div @click="handleCopyInstance(clusterRoleNodeGroup[groupName])">{{ t('复制实例') }}</div>
        </PopoverCopy>
      </div>
      <div class="host-wrapper">
        <div
          v-for="nodeItem in clusterRoleNodeGroup[groupName]"
          :key="`${nodeItem.bk_instance_id}#${nodeItem.instance}`"
          style="display: flex; align-items: center">
          <ClusterInstanceStatus
            :data="nodeItem.status"
            :show-text="false" />
          <div class="ml-4">
            {{ nodeItem.displayInstance || nodeItem.instance }}
          </div>
          <BkTag
            v-if="(nodeItem as TendbhaModel['slaves'][number]).is_stand_by"
            class="is-stand-by ml-4"
            size="small">
            Standby
          </BkTag>
          <BkTag
            v-if="nodeItem.status === 'unavailable'"
            class="ml-4"
            size="small">
            {{ t('不可用') }}
          </BkTag>
        </div>
        <span v-if="clusterRoleNodeGroup[groupName].length < 1">--</span>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import type { ClusterListNode } from '@services/types';

  import ClusterInstanceStatus from '@components/cluster-instance-status/Index.vue';
  import PopoverCopy from '@components/popover-copy/Index.vue';

  import { execCopy, messageWarn } from '@utils';

  interface Props {
    clusterRoleNodeGroup: Record<string, ({ displayInstance?: string } & ClusterListNode)[]>;
  }

  defineProps<Props>();

  const { t } = useI18n();

  const handleCopyHost = (nodeList: ClusterListNode[]) => {
    const ipList = _.uniq(nodeList.map((item) => item.ip));
    if (ipList.length < 1) {
      messageWarn(t('没有可复制 IP'));
      return;
    }

    execCopy(
      ipList.join('\n'),
      t('复制成功，共n条', {
        n: ipList.length,
      }),
    );
  };

  const handleCopyInstance = (nodeList: ClusterListNode[]) => {
    const instanceList = nodeList.map((item) => item.instance);

    if (instanceList.length < 1) {
      messageWarn(t('没有可复制实例'));
      return;
    }

    execCopy(
      instanceList.join('\n'),
      t('复制成功，共n条', {
        n: instanceList.length,
      }),
    );
  };
</script>
<style lang="less">
  .cluster-detail-instance-table-view {
    display: flex;
    min-height: 80px;
    font-size: 12px;
    border-bottom: 1px solid #dcdee5;

    .role-item {
      flex: 1;
      display: flex;
      flex-direction: column;

      .role-name {
        display: flex;
        height: 36px;
        padding: 0 12px;
        color: #313238;
        background: #f0f1f5;
        align-items: center;
        border-bottom: 1px solid #dcdee5;
      }

      .host-wrapper {
        padding: 8px 12px;
        line-height: 20px;
        color: #4d4f56;
        flex: 1;

        &:hover {
          background: #f5f7fa;

          .cell-copy-btn {
            visibility: visible;
          }
        }

        .cell-copy-btn {
          visibility: hidden;
        }
      }
    }

    .is-stand-by {
      color: #531dab !important;
      background: #f9f0ff !important;
    }
  }
</style>
