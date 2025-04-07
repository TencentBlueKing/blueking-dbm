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
      <I18nT keypath="共n台_共nGB">
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
    <BkTable :data="hostList">
      <BkTableColumn
        field="ip"
        :label="t('节点 IP')"
        :min-width="100" />
      <BkTableColumn
        v-if="!isClientNode"
        field="instance_num"
        :label="t('每台主机实例数量')"
        :min-width="150">
        <template #default="{ data }">
          <EditHostInstance
            :model-value="data.instance_num"
            @change="(value: number) => handleInstanceNumChange(value, data)" />
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="agent_status"
        :label="t('Agent状态')"
        :min-width="120">
        <template #default="{ data }">
          <HostAgentStatus :data="data.agent_status" />
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="bk_disk"
        :label="t('磁盘_GB')"
        :min-width="100" />
      <BkTableColumn
        fixed="right"
        :label="t('操作')"
        :min-width="100">
        <template #default="{ data }">
          <BkButton
            text
            theme="primary"
            @click="handleRemoveHost(data.bk_host_id)">
            {{ t('删除') }}
          </BkButton>
        </template>
      </BkTableColumn>
    </BkTable>
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
      const item = {
        agent_status: hostItem.agent_status,
        bk_biz_id: hostItem.dedicated_biz,
        bk_cloud_id: hostItem.bk_cloud_id,
        bk_disk: hostItem.bk_disk,
        bk_host_id: hostItem.bk_host_id,
        ip: hostItem.ip,
      };
      if (!isClientNode.value) {
        return Object.assign({}, item, {
          instance_num: 1,
        });
      }
      return item;
    });
  };

  const handleInstanceNumChange = (value: number, data: TExpansionNode['hostList'][number]) => {
    hostList.value = hostList.value.map((item) => {
      if (item.bk_host_id === data.bk_host_id) {
        return {
          ...item,
          instance_num: value,
        };
      }
      return item;
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
