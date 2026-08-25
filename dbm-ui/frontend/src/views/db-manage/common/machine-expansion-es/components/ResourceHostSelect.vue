<template>
  <BkButton @click="handleShowSelector">
    <i class="db-icon-add" />
    {{ t('添加服务器') }}
  </BkButton>
  <ResourceHostSelector
    v-model:is-show="showSelector"
    :disable-host-method="disableHostMethod"
    :params="{
      for_bizs: [currentBizId, 0],
      resource_types: [DBTypes.ES, 'PUBLIC'],
    }"
    @change="handleHostChange" />
  <div
    v-if="hostList.length > 0"
    class="data-preview-table">
    <div class="data-preview-header">
      <I18nT
        keypath="共n台_共nGB"
        scope="global">
        <span
          class="number"
          style="color: #3a84ff">
          {{ hostList.length }}
        </span>
        <span
          class="number"
          style="color: #2dcb56">
          {{ calcSelectHostDisk }}
        </span>
      </I18nT>
    </div>
    <PrimaryTable
      :data="hostList"
      row-key="bk_host_id">
      <TableColumn
        col-key="ip"
        :min-width="100"
        :title="t('节点 IP')" />
      <TableColumn
        v-if="!isClientNode"
        col-key="instance_num"
        :min-width="150"
        :title="t('每台主机实例数量')">
        <template #default="{ row }">
          <EditHostInstance
            :model-value="row.instance_num"
            @change="(value: number) => handleInstanceNumChange(value, row)" />
        </template>
      </TableColumn>
      <TableColumn
        col-key="agent_status"
        :min-width="120"
        :title="t('Agent状态')">
        <template #default="{ row }">
          <HostAgentStatus :data="row.agent_status" />
        </template>
      </TableColumn>
      <TableColumn
        col-key="bk_disk"
        :min-width="100"
        :title="t('磁盘_GB')" />
      <TableColumn
        col-key="operation"
        fixed="right"
        :min-width="100"
        :title="t('操作')">
        <template #default="{ row }">
          <BkButton
            text
            theme="primary"
            @click="handleRemoveHost(row.bk_host_id)">
            {{ t('删除') }}
          </BkButton>
        </template>
      </TableColumn>
    </PrimaryTable>
  </div>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import { DBTypes } from '@common/const';

  import HostAgentStatus from '@components/host-agent-status/Index.vue';
  import ResourceHostSelector, { type IValue } from '@components/resource-host-selector/Index.vue';

  import EditHostInstance from '@views/db-manage/common/big-data-host-table/es-host-table/components/EditHostInstance.vue';

  import type { TExpansionNode } from '../Index.vue';

  interface Props {
    data: TExpansionNode;
    disableHostMethod?: (params: TExpansionNode['hostList'][number]) => string | boolean;
  }

  const props = defineProps<Props>();

  const hostList = defineModel<TExpansionNode['hostList']>('hostList', {
    required: true,
  });

  const expansionDisk = defineModel<number>('expansionDisk', {
    required: true,
  });

  const { t } = useI18n();

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const showSelector = ref(false);

  const isClientNode = computed(() => props.data.role === 'es_client');
  const calcSelectHostDisk = computed(() =>
    hostList.value.reduce((result, hostItem) => result + ~~Number(hostItem.bk_disk), 0),
  );

  watch(calcSelectHostDisk, () => {
    expansionDisk.value = calcSelectHostDisk.value;
  });

  const handleShowSelector = () => {
    showSelector.value = true;
  };

  const handleRemoveHost = (hostId: number) => {
    hostList.value = hostList.value.filter((item) => item.bk_host_id !== hostId);
  };

  const handleHostChange = (data: IValue[]) => {
    hostList.value = data.map((hostItem) => {
      if (!isClientNode.value) {
        return Object.assign({}, hostItem, {
          instance_num: 1,
        });
      }
      return hostItem;
    });
  };

  const handleInstanceNumChange = (value: number, data: TExpansionNode['hostList'][number]) => {
    hostList.value = hostList.value.map((hostItem) => {
      if (hostItem.bk_host_id === data.bk_host_id) {
        return Object.assign({}, hostItem, {
          instance_num: 1,
        });
      }
      return hostItem;
    });
  };
</script>
<style lang="less" scoped>
  .data-preview-table {
    margin-top: 16px;

    .data-preview-header {
      display: flex;
      height: 42px;
      padding: 0 16px;
      background: #f0f1f5;
      align-items: center;
    }
  }
</style>
