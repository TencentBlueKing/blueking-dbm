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
      <ViewTable
        ref="viewTable"
        :cluster-id="clusterId"
        :cluster-type="clusterType" />
    </div>
    <ViewTopo
      v-if="viewType === 'topo'"
      :cluster-id="clusterId"
      :cluster-type="clusterType"
      :db-type="dbType" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { DBTypes } from '@common/const';

  import useClusterMachineList from '@views/db-manage/hooks/useClusterMachineList';

  import { execCopy } from '@utils';

  import ViewTable from './components/ViewTable.vue';
  import ViewTopo from './components/ViewTopo.vue';

  interface Props {
    clusterId: number;
    clusterType: Parameters<typeof useClusterMachineList>[0];
    dbType: DBTypes;
  }

  defineProps<Props>();

  const { t } = useI18n();

  const viewTableRef = useTemplateRef('viewTable');
  const viewType = ref('table');

  const handleNotAliveHostIp = () => {
    const ipList = viewTableRef.value!.getNotAliveHostList().map((item) => item.ip);
    execCopy(
      ipList.join('\n'),
      t('复制成功，共n条', {
        n: ipList.length,
      }),
    );
  };

  const handleAllHostIp = () => {
    const ipList = viewTableRef.value!.getAllHostList().map((item) => item.ip);
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
    display: block;

    .action-box {
      display: flex;
      padding: 20px 0;
    }
  }
</style>
