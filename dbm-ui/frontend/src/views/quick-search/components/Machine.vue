<template>
  <div>
    <DbCard
      v-if="data.length"
      class="search-result-machine search-result-card"
      mode="collapse"
      :title="t('主机')">
      <template #desc>
        <I18nT
          class="ml-8"
          keypath="共n条"
          style="color: #63656e"
          tag="span">
          <template #n>
            <strong>{{ data.length }}</strong>
          </template>
        </I18nT>
      </template>
      <DbOriginalTable
        class="search-result-table mt-14 mb-8"
        :data="data"
        :pagination="pagination"
        :settings="tableSetting"
        show-settings
        @setting-change="updateTableSettings">
        <BkTableColumn
          field="ip"
          fixed="left"
          label="IP"
          :width="150">
          <template #default="{ data: rowData }: { data: FaultOrRecycleMachineModel }">
            <TextOverflowLayout>
              <BkButton
                text
                @click="() => handleGo(rowData)">
                <TextHighlight
                  high-light-color="#FF9C01"
                  :keyword="props.keyword"
                  :text="rowData.ip" />
              </BkButton>
              <template #append>
                <BkButton
                  class="ml-4"
                  text
                  theme="primary"
                  @click="() => handleCopy(rowData.ip)">
                  <DbIcon type="copy" />
                </BkButton>
              </template>
            </TextOverflowLayout>
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="poolDispaly"
          :label="t('所属池')"
          :width="130">
        </BkTableColumn>
        <BkTableColumn
          field="city"
          :label="t('地域')">
        </BkTableColumn>
        <BkTableColumn
          field="sub_zone"
          :label="t('园区')">
        </BkTableColumn>
        <BkTableColumn
          field="rack_id"
          :label="t('机架')">
        </BkTableColumn>
        <BkTableColumn
          field="os_name"
          :label="t('操作系统')"
          show-overflow="tooltip"
          :width="180">
        </BkTableColumn>
        <BkTableColumn
          field="device_class"
          :label="t('机型')">
        </BkTableColumn>
        <BkTableColumn
          field="bk_cpu"
          :label="t('CPU (核)')"
          :width="160">
        </BkTableColumn>
        <BkTableColumn
          field="bkMemText"
          :label="t('内存')"
          show-overflow
          :width="120">
          <template #default="{ data: rowData }: { data: FaultOrRecycleMachineModel }">
            {{ rowData.bkMemText || '0 M' }}
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="bk_disk"
          :label="t('磁盘 (G)')">
        </BkTableColumn>
      </DbOriginalTable>
    </DbCard>
    <EmptyStatus
      v-else
      class="empty-status"
      :is-anomalies="isAnomalies"
      :is-searching="isSearching"
      @clear-search="handleClearSearch"
      @refresh="handleRefresh" />
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import FaultOrRecycleMachineModel from '@services/model/db-resource/FaultOrRecycleMachine';

  import { useLocation, useTableSettings } from '@hooks';

  import { UserPersonalSettings } from '@common/const';

  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';
  import TextHighlight from '@components/text-highlight/Index.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { execCopy } from '@utils';

  interface Props {
    // bizIdNameMap: Record<number, string>;
    data: FaultOrRecycleMachineModel[];
    isAnomalies: boolean;
    isSearching: boolean;
    keyword: string;
  }

  interface Emits {
    (e: 'refresh'): void;
    (e: 'clearSearch'): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const location = useLocation();

  const pagination = ref({
    count: props.data.length,
    limit: 10,
  });

  const { settings: tableSetting, updateTableSettings } = useTableSettings(
    UserPersonalSettings.QUICK_SEARCH_RESOURCE_POOL,
    {
      checked: [
        'ip',
        'poolDispaly',
        'city',
        'sub_zone',
        'rack_id',
        'os_name',
        'device_class',
        'bk_cpu',
        'bkMemText',
        'bk_disk',
      ],
      disabled: ['ip'],
    },
  );

  const handleCopy = (content: string) => {
    execCopy(content, t('复制成功，共n条', { n: 1 }));
  };

  const handleGo = (data: FaultOrRecycleMachineModel) => {
    location({
      name: 'allHost',
      query: {
        ips: data.ip,
      },
    });
  };

  const handleRefresh = () => {
    emits('refresh');
  };

  const handleClearSearch = () => {
    emits('clearSearch');
  };
</script>

<style lang="less" scoped>
  @import '../style/table-card.less';
</style>
