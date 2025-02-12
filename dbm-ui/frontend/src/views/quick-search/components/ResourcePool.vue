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

  import {
    useLocation,
    useTableSettings,
  } from '@hooks';

  import { UserPersonalSettings } from '@common/const';

  import DiskPopInfo from '@components/disk-pop-info/DiskPopInfo.vue';
  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';
  import HostAgentStatus from '@components/host-agent-status/Index.vue';
  import HightLightText from '@components/system-search/components/search-result/render-result/components/HightLightText.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { execCopy } from '@utils';

  interface Props {
    keyword: string,
    data: DbResourceModel[],
    bizIdNameMap: Record<number, string>
    isAnomalies: boolean,
    isSearching: boolean
  }

  interface Emits {
    (e: 'refresh'): void,
    (e: 'clearSearch'): void
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
      ...props.bizIdNameMap
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
    const currentTypeMap: Record<string, string> = {}
    const typeList = [{
      id: 'PUBLIC',
      name: t('通用'),
    }].concat(dbTypeList.value || [])
    const originMap = typeList.reduce<Record<string, string>>((prev, dbTypeItem) => Object.assign({}, prev, { [dbTypeItem.id]: dbTypeItem.name }), {});
    props.data.forEach((dataItem) => {
      if (!currentTypeMap[dataItem.resource_type]) {
        currentTypeMap[dataItem.resource_type] = originMap[dataItem.resource_type];
      }
    });
    return currentTypeMap
  })

  const columns = computed(() => [
    {
      label: 'IP',
      field: 'ip',
      width: 160,
      render: ({ data }: { data: DbResourceModel }) => (
        <TextOverflowLayout>
          {{
            default: () => (
              <bk-button
                text
                onclick={() => handleGo(data)}>
                <HightLightText
                  keyWord={props.keyword}
                  text={data.ip}
                  highLightColor='#FF9C01' />
              </bk-button>
            ),
            append: () => (
              <bk-button
                class="ml-4"
                text
                theme="primary"
                onclick={() => handleCopy(data.ip)}>
                <db-icon type="copy" />
              </bk-button>
            ),
          }}
        </TextOverflowLayout>
      ),
    },
    {
      label: t('管控区域'),
      field: 'bk_cloud_name',
      with: 120,
    },
    {
      label: t('Agent 状态'),
      field: 'agent_status',
      with: 100,
      render: ({ data }: {data: DbResourceModel}) => <HostAgentStatus data={data.agent_status} />,
    },
    {
      label: t('所属业务'),
      field: 'forBizDisplay',
      width: 100,
      filter: {
        list: Object.entries(filterMap.value.bizNameMap).map(bizItem => ({
          value: Number(bizItem[0]),
          text: bizItem[1],
        })),
        filterFn: (checked: number[], row: DbResourceModel) => {
          if (checked.length === 0) {
            return true;
          }
          return checked.some(checkedItem => row.for_biz.bk_biz_id === checkedItem);
        },
      },
      render: ({ data }: {data: DbResourceModel}) => data.forBizDisplay || '--',
    },
    {
      label: t('所属DB类型'),
      field: 'resourceTypeDisplay',
      minWidth: 150,
      filter: {
        list: Object.entries(resourceTypeMap.value).map(resourceTypeItem => ({
          value: resourceTypeItem[0],
          text: resourceTypeItem[1],
        })),
        filterFn: (checked: string[], row: DbResourceModel) => {
          if (checked.length === 0) {
            return true;
          }
          return checked.some(checkedItem => row.resource_type === checkedItem);
        },
      },
      render: ({ data }: {data: DbResourceModel}) => data.resourceTypeDisplay || '--',
    },
    {
      label: t('机架'),
      field: 'rack_id',
      render: ({ data }: {data: DbResourceModel}) => data.rack_id || '--',
    },
    {
      label: t('机型'),
      field: 'device_class',
      filter: {
        list: Array.from(filterMap.value.deviceClassSet).map(ticketTypeItem => ({
          value: ticketTypeItem,
          text: ticketTypeItem,
        })),
      },
      render: ({ data }: {data: DbResourceModel}) => data.device_class || '--',
    },
    {
      label: t('操作系统类型'),
      field: 'os_type',
      render: ({ data }: {data: DbResourceModel}) => data.os_type || '--',
    },
    {
      label: t('地域'),
      field: 'city',
      render: ({ data }: {data: DbResourceModel}) => data.city || '--',
    },
    {
      label: t('园区'),
      field: 'sub_zone',
      render: ({ data }: {data: DbResourceModel}) => data.sub_zone || '--',
    },
    {
      label: t('CPU(核)'),
      field: 'bk_cpu',
    },
    {
      label: t('内存'),
      field: 'bkMemText',
      render: ({ data }: {data: DbResourceModel}) => data.bkMemText || '0 M',
    },
    {
      label: t('磁盘容量(G)'),
      field: 'bk_disk',
      minWidth: 120,
      render: ({ data }: {data: DbResourceModel}) => (
        <DiskPopInfo data={data.storage_device}>
          <span style="line-height: 40px; color: #3a84ff;">
            {data.bk_disk}
          </span>
        </DiskPopInfo>
      ),
    },
  ]);

  const { data: dbTypeList } = useRequest(fetchDbTypeList);

  // 设置用户个人表头信息
  const defaultSettings = {
    fields: (columns.value || []).filter(item => item.field).map(item => ({
      label: item.label,
      field: item.field,
      disabled: ['ip', 'forBizDisplay', 'resource_type'].includes(item.field)
    })),
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
    trigger: 'manual' as const,
  };

  const {
    settings: tableSetting,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.QUICK_SEARCH_RESOURCE_POOL, defaultSettings);

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
