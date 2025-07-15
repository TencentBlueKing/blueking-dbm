<template>
  <BkButton @click="handleShowSelector">
    <i class="db-icon-add" />
    {{ t('添加服务器') }}
  </BkButton>
  <ResourceHostSelector
    v-model="hostList"
    v-model:is-show="showSelector"
    :params="{
      for_bizs: [currentBizId, 0],
      resource_types: [dbType, 'PUBLIC'],
    }"
    :selected="hostList" />
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
    <BkTable :data="hostList">
      <BkTableColumn
        field="ip"
        :label="t('节点 IP')"
        :min-width="200" />
      <BkTableColumn
        field="agent_status"
        :label="t('Agent状态')"
        :min-width="200">
        <template #default="{ data }">
          <HostAgentStatus :data="data.agent_status" />
        </template>
      </BkTableColumn>
      <BkTableColumn
        field="bk_disk"
        :label="t('磁盘_GB')"
        :min-width="200" />
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

  import HostAgentStatus from '@components/host-agent-status/Index.vue';
  import ResourceHostSelector, { type IValue } from '@components/resource-host-selector/Index.vue';

  interface Props {
    dbType: string;
  }

  defineProps<Props>();

  const hostList = defineModel<IValue[]>('hostList', {
    required: true,
  });

  const expansionDisk = defineModel<number>('expansionDisk', {
    required: true,
  });

  const { t } = useI18n();

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const showSelector = ref(false);

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
