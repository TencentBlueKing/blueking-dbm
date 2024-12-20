<template>
  <BkDialog
    class="resource-host-selector"
    :close-icon="false"
    :is-show="isShow"
    :width="dialogWidth">
    <template #header>
      <PanelTab v-model="currentPanelTab" />
    </template>
    <div>
      <DbSearchSelect
        v-model="searchSelectValue"
        :data="searchSelectData" />
      <div class="host-list-wrapper mt-16">
        <DbTable
          ref="table"
          :container-height="contentHeight"
          :data-source="dataSource"
          :height="contentHeight">
          <BkTableColumn
            fixed="left"
            :resizable="false"
            :width="60">
            <template #default="{ data }">
              <BkCheckbox
                v-if="multiple"
                label
                :model-value="Boolean(rowSelectMemo[data.bk_host_id])"
                @change="() => handleSelectChange(data)" />
              <BkRadio
                v-else
                label
                :model-value="Boolean(rowSelectMemo[data.bk_host_id])"
                @change="() => handleSelectChange(data)" />
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="ip"
            fixed="left"
            label="IP"
            :min-width="150" />
          <BkTableColumn
            field="bk_cloud_name"
            :label="t('管控区域')"
            :min-width="120" />
          <BkTableColumn
            field="agent_status"
            :label="t('Agent 状态')"
            :min-width="120">
            <template #default="{ data }">
              <HostAgentStatus :data="data.agent_status" />
            </template>
          </BkTableColumn>
          <!-- <BkTableColumn
            field="bk_cpu"
            :label="t('资源归属')"
            :min-width="300">
            <template #default="{ data }">
              <ResourceHostOwner
                v-if="false"
                :data="data" />
            </template>
          </BkTableColumn> -->
          <BkTableColumn
            field="rack_id"
            :label="t('机架')"
            :min-width="120">
            <template #default="{ data }">
              {{ data.rack_id || '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="device_class"
            :label="t('机型')"
            :min-width="120">
            <template #default="{ data }">
              {{ data.device_class || '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="os_type"
            :label="t('操作系统类型')"
            :min-width="120">
            <template #default="{ data }">
              {{ data.os_type || '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="city"
            :label="t('地域')"
            :min-width="120">
            <template #default="{ data }">
              {{ data.city || '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="sub_zone"
            :label="t('园区')"
            :min-width="120">
            <template #default="{ data }">
              {{ data.sub_zone || '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="bk_cpu"
            :label="t('CPU(核)')"
            :min-width="120">
            <template #default="{ data }">
              {{ data.bk_cpu || '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="bkMemText"
            :label="t('内存')"
            :min-width="120">
            <template #default="{ data }">
              {{ data.bkMemText || '--' }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="bk_disk"
            :label="t('磁盘容量(G)')"
            :min-width="100">
            <template #default="{ data }">
              <DiskPopInfo
                :data="data.storage_device"
                trigger="click">
                <BkButton
                  text
                  theme="primary">
                  {{ data.bk_disk }}
                </BkButton>
              </DiskPopInfo>
            </template>
          </BkTableColumn>
        </DbTable>
      </div>
    </div>
    <template #footer>
      <BkButton
        theme="primary"
        @click="handleSubmit">
        {{ t('确定') }}
      </BkButton>
      <BkButton
        class="ml-8"
        @click="handleCancel">
        {{ t('取消') }}
      </BkButton>
    </template>
  </BkDialog>
</template>
<script setup lang="ts">
  import { useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import DbResourceModel from '@services/model/db-resource/DbResource';
  import { fetchList } from '@services/source/dbresourceResource';

  import DiskPopInfo from '@components/disk-pop-info/DiskPopInfo.vue';
  import HostAgentStatus from '@components/host-agent-status/Index.vue';

  // import ResourceHostOwner from '@components/resource-host-owner/Index.vue';
  import PanelTab from './components/PanelTab.vue';
  import useSearchSelectData from './hooks/use-search-select-data';

  export interface IValue {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    ip: string;
  }

  interface Props {
    multiple?: boolean;
    params?: {
      for_biz?: number;
      bk_cloud_ids?: string;
      resource_type?: string;
      os_type?: string;
    };
  }

  interface Emits {
    (e: 'change', value: IValue[]): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    multiple: true,
    params: () => ({}),
  });

  const emits = defineEmits<Emits>();

  const dialogWidth = Math.max(window.innerWidth * 0.8, 800);
  const contentHeight = window.innerHeight * 0.8 - 100;

  const { t } = useI18n();
  const { searchSelectData, value: searchSelectValue, formatSearchValue } = useSearchSelectData(props);
  const isShow = defineModel<boolean>('isShow', {
    default: false,
  });

  const modelValue = defineModel<IValue[]>({
    default: () => [],
  });

  const dbTableRef = useTemplateRef('table');
  const currentPanelTab = ref('host');
  const rowSelectMemo = shallowRef<Record<number, DbResourceModel>>({});

  const dataSource = (params: ServiceParameters<typeof fetchList>) =>
    fetchList({
      ...params,
      ...props.params,
    });

  watch(searchSelectValue, () => {
    dbTableRef.value?.fetchData(formatSearchValue.value);
  });

  watch(isShow, () => {
    if (!isShow.value) {
      return;
    }
    rowSelectMemo.value = modelValue.value.reduce(
      (result, item) =>
        Object.assign(result, {
          [item.bk_host_id]: item,
        }),
      {},
    );
  });

  const handleSelectChange = (data: DbResourceModel) => {
    const latestSelectMemo = { ...rowSelectMemo.value };
    if (props.multiple) {
      if (latestSelectMemo[data.bk_host_id]) {
        delete latestSelectMemo[data.bk_host_id];
      } else {
        latestSelectMemo[data.bk_host_id] = data;
      }
      rowSelectMemo.value = latestSelectMemo;
    } else {
      rowSelectMemo.value = {
        [data.bk_host_id]: data,
      };
    }
  };

  const handleSubmit = () => {
    isShow.value = false;
    const latestValue = Object.values(rowSelectMemo.value).map((item) => ({
      bk_biz_id: item.dedicated_biz,
      bk_cloud_id: item.bk_cloud_id,
      bk_host_id: item.bk_host_id,
      ip: item.ip,
    }));

    modelValue.value = latestValue;

    emits('change', latestValue);
  };

  const handleCancel = () => {
    isShow.value = false;
  };
</script>
<style lang="less">
  .resource-host-selector {
    .bk-dialog-header {
      padding: 0;
    }

    .host-title {
      display: flex;
      height: 32px;
      margin: 0 16px;
      color: #3a84ff;
      background: #e1ecff;
      align-items: center;
    }

    .host-list-wrapper {
      padding: 0;
    }
  }
</style>
