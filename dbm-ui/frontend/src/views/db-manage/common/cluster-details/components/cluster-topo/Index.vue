<template>
  <div class="cluser-detail-instance-box">
    <div class="action-box">
      <BkRadioGroup
        v-model="viewType"
        type="capsule">
        <BkRadioButton label="table">
          {{ t('表格视图') }}
        </BkRadioButton>
        <BkRadioButton label="topo">
          {{ t('拓扑视图') }}
        </BkRadioButton>
      </BkRadioGroup>
      <BkButton
        style="width: 105px; margin-left: auto"
        @click="handleNotAliveHostIp">
        {{ t('复制异常 IP') }}
      </BkButton>
      <BkButton
        class="ml-8"
        style="width: 105px"
        @click="handleAllHostIp">
        {{ t('复制所有 IP') }}
      </BkButton>
    </div>
    <div v-show="viewType === 'table'">
      <ViewTable :cluster-role-node-group="clusterRoleNodeGroup" />
    </div>
    <ViewTopo
      v-if="viewType === 'topo'"
      :id="clusterId"
      :cluster-type="clusterType"
      :db-type="dbType" />
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import type { ClusterListNode } from '@services/types';

  import { ClusterInstStatusKeys, DBTypes } from '@common/const';

  import useClusterMachineList from '@views/db-manage/hooks/useClusterMachineList';

  import { execCopy, messageWarn } from '@utils';

  import ViewTable from './components/ViewTable.vue';
  import ViewTopo from './components/ViewTopo.vue';

  interface Props {
    clusterId: number;
    clusterRoleNodeGroup: Record<string, ClusterListNode[]>;
    clusterType: Parameters<typeof useClusterMachineList>[0];
    dbType: DBTypes;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const viewType = ref('table');

  const handleNotAliveHostIp = () => {
    const ipList = _.flatten(Object.values(props.clusterRoleNodeGroup)).reduce<string[]>((result, item) => {
      if (item.status === ClusterInstStatusKeys.UNAVAILABLE) {
        result.push(item.instance);
      }
      return result;
    }, []);

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

  const handleAllHostIp = () => {
    const ipList = _.flatten(Object.values(props.clusterRoleNodeGroup)).map((item) => item.ip);
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
</script>
<style lang="less">
  .cluser-detail-instance-box {
    height: 100%;

    .action-box {
      display: flex;
      padding: 20px 0;
    }
  }
</style>
