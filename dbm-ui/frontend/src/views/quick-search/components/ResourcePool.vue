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

  import DbResourceModel from '@services/model/db-resource/DbResource';

  import {
    useCopy,
    useLocation,
    useTableSettings,
  } from '@hooks';

  import { UserPersonalSettings } from '@common/const';

  import DiskPopInfo from '@components/disk-pop-info/DiskPopInfo.vue';
  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';
  import HostAgentStatus from '@components/host-agent-status/Index.vue';
  import HightLightText from '@components/system-search/components/search-result/render-result/components/HightLightText.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

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
  const copy = useCopy();
  const location = useLocation();

  const pagination = ref({
    count: props.data.length,
    limit: 10,
  });

  const filterMap = computed(() => {
    const currentBizNameMap = props.bizIdNameMap;
    const bizNameMap: Props['bizIdNameMap'] = {};
    const resourceTypesSet = new Set<string>();
    const deviceClassSet = new Set<string>();

    props.data.forEach((dataItem) => {
      if (!bizNameMap[dataItem.for_biz.bk_biz_id]) {
          bizNameMap[dataItem.for_biz.bk_biz_id] = currentBizNameMap[dataItem.for_biz.bk_biz_id];
        }

      if(dataItem.resource_type) {
        resourceTypesSet.add(dataItem.resource_type);
      }

      if (dataItem.device_class) {
        deviceClassSet.add(dataItem.device_class);
      }
    });

    return {
      bizNameMap,
      resourceTypesSet,
      deviceClassSet,
    };
  });

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
      label: t('云区域'),
      field: 'bk_cloud_id',
      render: ({ data }: { data: DbResourceModel }) => data.bk_cloud_id || '--',
    },
    {
      label: t('Agent状态'),
      field: 'agent_status',
      width: 100,
      filter: {
        list: [
          {
            value: 0,
            text: t('异常'),
          },
          {
            value: 1,
            text: t('正常'),
          },
        ],
      },
      render: ({ data }: { data: DbResourceModel }) => <HostAgentStatus data={data.agent_status} />,
    },
    {
      label: t('所属业务'),
      field: 'for_biz',
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
      render: ({ data }: { data: DbResourceModel }) => data.for_biz.bk_biz_id ? <bk-tag>{data.for_biz.bk_biz_name}</bk-tag> : t('无限制'),
    },
    {
      label: t('所属DB类型'),
      field: 'resource_type',
      filter: {
        list: Array.from(filterMap.value.resourceTypesSet).map(resourceTypeItem => ({
          value: resourceTypeItem,
          text: resourceTypeItem,
        })),
        filterFn: (checked: string[], row: DbResourceModel) => {
          if (checked.length === 0) {
            return true;
          }
          return checked.some(checkedItem => row.resource_type === checkedItem);
        },
      },
      render: ({ data }: { data: DbResourceModel }) => data.resource_type ? <bk-tag>{data.resource_type}</bk-tag> : t('无限制'),
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
      render: ({ data }: { data: DbResourceModel }) => data.device_class || '--',
    },
    {
      label: t('地域'),
      field: 'city',
      render: ({ data }: { data: DbResourceModel }) => data.city || '--',
    },
    {
      label: t('园区'),
      field: 'sub_zone',
      render: ({ data }: { data: DbResourceModel }) => data.sub_zone || '--',
    },
    {
      label: t('CPU(核)'),
      field: 'bk_cpu',
      render: ({ data }: { data: DbResourceModel }) => data.bk_cpu || '--',
    },
    {
      label: t('内存(G)'),
      field: 'bkMemText',
      render: ({ data }: { data: DbResourceModel }) => data.bkMemText || '0 M',
    },
    {
      label: t('磁盘容量(G)'),
      field: 'bk_disk',
      width: 100,
      render: ({ data }: { data: DbResourceModel }) => (
        <DiskPopInfo data={data.storage_device}>
          <span style="line-height: 40px; color: #3a84ff;">
            {data.bk_disk}
          </span>
        </DiskPopInfo>
      ),
    },
  ]);

  // 设置用户个人表头信息
  const defaultSettings = {
    fields: (columns.value || []).filter(item => item.field).map(item => ({
      label: item.label,
      field: item.field,
      disabled: item.field === 'id',
    })),
    checked: [
      'ip',
      'bk_cloud_id',
      'agent_status',
      'for_biz',
      'resource_type',
      'device_class',
      'city',
      'sub_zone',
      'bk_cpu',
      'bkMemText',
      'bk_disk',
    ],
  };

  const {
    settings: tableSetting,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.QUICK_SEARCH_RESOURCE_POOL, defaultSettings);

  const handleCopy = (content: string) => {
    copy(content);
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
