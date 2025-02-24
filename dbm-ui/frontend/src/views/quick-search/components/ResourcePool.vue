<template>
  <div>
    <DbCard
      v-if="data.length"
      class="search-result-machine search-result-card"
      mode="collapse"
      :title="t('资源池主机')">
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
        :columns="columns"
        :data="data"
        :pagination="pagination"
        :settings="tableSetting"
        @setting-change="updateTableSettings" />
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
  import { useRequest } from 'vue-request';

  import DbResourceModel from '@services/model/db-resource/DbResource';
  import { fetchDbTypeList } from '@services/source/infras';

  import { useLocation, useTableSettings } from '@hooks';

  import { UserPersonalSettings } from '@common/const';

  import DiskPopInfo from '@components/disk-pop-info/DiskPopInfo.vue';
  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';
  import HostAgentStatus from '@components/host-agent-status/Index.vue';
  import HightLightText from '@components/system-search/components/search-result/render-result/components/HightLightText.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { execCopy } from '@utils';

  interface Props {
    bizIdNameMap: Record<number, string>;
    data: DbResourceModel[];
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

  const filterMap = computed(() => {
    const currentBizNameMap: Props['bizIdNameMap'] = {
      0: t('公共资源池'),
      ...props.bizIdNameMap,
    };
    const bizNameMap: Props['bizIdNameMap'] = {};

    const deviceClassSet = new Set<string>();

    props.data.forEach((dataItem) => {
      if (!bizNameMap[dataItem.for_biz.bk_biz_id]) {
        bizNameMap[dataItem.for_biz.bk_biz_id] = currentBizNameMap[dataItem.for_biz.bk_biz_id];
      }
      if (dataItem.device_class) {
        deviceClassSet.add(dataItem.device_class);
      }
    });

    return {
      bizNameMap,
      deviceClassSet,
    };
  });

  const resourceTypeMap = computed(() => {
    const currentTypeMap: Record<string, string> = {};
    const typeList = [
      {
        id: 'PUBLIC',
        name: t('通用'),
      },
    ].concat(dbTypeList.value || []);
    const originMap = typeList.reduce<Record<string, string>>(
      (prev, dbTypeItem) => Object.assign({}, prev, { [dbTypeItem.id]: dbTypeItem.name }),
      {},
    );
    props.data.forEach((dataItem) => {
      if (!currentTypeMap[dataItem.resource_type]) {
        currentTypeMap[dataItem.resource_type] = originMap[dataItem.resource_type];
      }
    });
    return currentTypeMap;
  });

  const columns = computed(() => [
    {
      field: 'ip',
      label: 'IP',
      render: ({ data }: { data: DbResourceModel }) => (
        <TextOverflowLayout>
          {{
            append: () => (
              <bk-button
                class='ml-4'
                theme='primary'
                text
                onclick={() => handleCopy(data.ip)}>
                <db-icon type='copy' />
              </bk-button>
            ),
            default: () => (
              <bk-button
                text
                onclick={() => handleGo(data)}>
                <HightLightText
                  keyWord={props.keyword}
                  highLightColor='#FF9C01'
                  text={data.ip}
                />
              </bk-button>
            ),
          }}
        </TextOverflowLayout>
      ),
      width: 160,
    },
    {
      field: 'bk_cloud_name',
      label: t('管控区域'),
      with: 120,
    },
    {
      field: 'agent_status',
      label: t('Agent 状态'),
      render: ({ data }: { data: DbResourceModel }) => <HostAgentStatus data={data.agent_status} />,
      with: 100,
    },
    {
      field: 'forBizDisplay',
      filter: {
        filterFn: (checked: number[], row: DbResourceModel) => {
          if (checked.length === 0) {
            return true;
          }
          return checked.some((checkedItem) => row.for_biz.bk_biz_id === checkedItem);
        },
        list: Object.entries(filterMap.value.bizNameMap).map((bizItem) => ({
          text: bizItem[1],
          value: Number(bizItem[0]),
        })),
      },
      label: t('所属业务'),
      render: ({ data }: { data: DbResourceModel }) => data.forBizDisplay || '--',
      width: 100,
    },
    {
      field: 'resourceTypeDisplay',
      filter: {
        filterFn: (checked: string[], row: DbResourceModel) => {
          if (checked.length === 0) {
            return true;
          }
          return checked.some((checkedItem) => row.resource_type === checkedItem);
        },
        list: Object.entries(resourceTypeMap.value).map((resourceTypeItem) => ({
          text: resourceTypeItem[1],
          value: resourceTypeItem[0],
        })),
      },
      label: t('所属DB类型'),
      minWidth: 150,
      render: ({ data }: { data: DbResourceModel }) => data.resourceTypeDisplay || '--',
    },
    {
      field: 'rack_id',
      label: t('机架'),
      render: ({ data }: { data: DbResourceModel }) => data.rack_id || '--',
    },
    {
      field: 'device_class',
      filter: {
        list: Array.from(filterMap.value.deviceClassSet).map((ticketTypeItem) => ({
          text: ticketTypeItem,
          value: ticketTypeItem,
        })),
      },
      label: t('机型'),
      render: ({ data }: { data: DbResourceModel }) => data.device_class || '--',
    },
    {
      field: 'os_type',
      label: t('操作系统类型'),
      render: ({ data }: { data: DbResourceModel }) => data.os_type || '--',
    },
    {
      field: 'city',
      label: t('地域'),
      render: ({ data }: { data: DbResourceModel }) => data.city || '--',
    },
    {
      field: 'sub_zone',
      label: t('园区'),
      render: ({ data }: { data: DbResourceModel }) => data.sub_zone || '--',
    },
    {
      field: 'bk_cpu',
      label: t('CPU(核)'),
    },
    {
      field: 'bkMemText',
      label: t('内存'),
      render: ({ data }: { data: DbResourceModel }) => data.bkMemText || '0 M',
    },
    {
      field: 'bk_disk',
      label: t('磁盘容量(G)'),
      minWidth: 120,
      render: ({ data }: { data: DbResourceModel }) => (
        <DiskPopInfo data={data.storage_device}>
          <span style='line-height: 40px; color: #3a84ff;'>{data.bk_disk}</span>
        </DiskPopInfo>
      ),
    },
  ]);

  const { data: dbTypeList } = useRequest(fetchDbTypeList);

  // 设置用户个人表头信息
  const defaultSettings = {
    checked: [
      'ip',
      'bk_cloud_name',
      'agent_status',
      'forBizDisplay',
      'resourceTypeDisplay',
      'rack_id',
      'device_class',
      'city',
      'sub_zone',
      'bk_cpu',
      'bk_mem',
      'bk_disk',
      'os_type',
    ],
    fields: (columns.value || [])
      .filter((item) => item.field)
      .map((item) => ({
        disabled: ['forBizDisplay', 'ip', 'resource_type'].includes(item.field),
        field: item.field,
        label: item.label,
      })),
    trigger: 'manual' as const,
  };

  const { settings: tableSetting, updateTableSettings } = useTableSettings(
    UserPersonalSettings.QUICK_SEARCH_RESOURCE_POOL,
    defaultSettings,
  );

  const handleCopy = (content: string) => {
    execCopy(content, t('复制成功，共n条', { n: 1 }));
  };

  const handleGo = (data: DbResourceModel) => {
    location({
      name: 'resourcePool',
      query: {
        hosts: data.ip,
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
