<template>
  <div
    v-bkloading="{ loading: isLoading }"
    class="cluster-detail-instance-table-view">
    <div
      v-for="groupName in Object.keys(hostGroup)"
      :key="groupName"
      class="role-item">
      <div class="role-name">
        <span>{{ groupName }} ({{ hostGroup[groupName].length }})</span>
      </div>
      <div class="host-wrapper">
        <div
          v-for="(hostItem, index) in hostGroup[groupName]"
          :key="hostItem.bk_host_id">
          <HostAgentStatus :data="hostItem?.host_info?.alive || 0">
            {{ hostItem.ip }}
            <BkButton
              v-if="index === 0"
              v-bk-tooltips="t('复制IP')"
              class="ml-4 cell-copy-btn"
              text
              theme="primary"
              @click="handleCopyHost(hostGroup[groupName])">
              <DbIcon type="copy" />
            </BkButton>
          </HostAgentStatus>
        </div>
        <span v-if="hostGroup[groupName].length < 1">--</span>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import HostAgentStatus from '@components/host-agent-status/Index.vue';

  import useClusterMachineList from '@views/db-manage/hooks/useClusterMachineList';

  import { execCopy } from '@utils';

  type IMachineList = ServiceReturnType<ReturnType<typeof useClusterMachineList>>['results'][number][];

  interface Props {
    clusterId: number;
    clusterType: Parameters<typeof useClusterMachineList>[0];
  }

  interface Expose {
    getAllHostList: () => IMachineList;
    getNotAliveHostList: () => IMachineList;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const requestHandler = useClusterMachineList(props.clusterType);

  let machineListMemo: IMachineList = [];

  const hostGroup = shallowRef<Record<string, IMachineList>>({});

  const { loading: isLoading } = useRequest(requestHandler, {
    defaultParams: [
      {
        cluster_ids: `${props.clusterId}`,
        limit: -1,
      },
    ],
    onSuccess(data) {
      machineListMemo = data.results;
      hostGroup.value = data.results.reduce<UnwrapRef<typeof hostGroup>>((result, hostItem) => {
        if (!result[hostItem.instance_role]) {
          Object.assign(result, {
            [hostItem.instance_role]: [],
          });
        }
        result[hostItem.instance_role].push(hostItem);
        return result;
      }, {});
    },
  });

  const handleCopyHost = (hostList: ValueOf<UnwrapRef<typeof hostGroup>>) => {
    const ipList = hostList.map((item) => item.ip);

    execCopy(
      ipList.join('\n'),
      t('复制成功，共n条', {
        n: ipList.length,
      }),
    );
  };

  defineExpose<Expose>({
    getAllHostList() {
      return machineListMemo;
    },
    getNotAliveHostList() {
      return machineListMemo.filter((item) => !item.host_info?.alive);
    },
  });
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
  }
</style>
