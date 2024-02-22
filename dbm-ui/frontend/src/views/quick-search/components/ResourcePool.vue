<template>
  <DbCard
    class="search-result-machine search-result-card"
    mode="collapse"
    :title="t('资源池主机')">
    <template #desc>
      <I18nT
        class="ml-8"
        keypath="共n条"
        style="color: #63656E;"
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
      :settings="tableSetting"
      @setting-change="updateTableSettings" />
  </DbCard>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import DbResourceModel from '@services/model/db-resource/DbResource';

  import {
    useCopy,
    useTableSettings,
  } from '@hooks';

  import { UserPersonalSettings } from '@common/const';

  import HostAgentStatus from '@components/cluster-common/HostAgentStatus.vue';
  import DiskPopInfo from '@components/disk-pop-info/DiskPopInfo.vue';
  import HightLightText from '@components/system-search/components/search-result/render-result/components/HightLightText.vue';

  interface Props {
    keyword: string,
    data: DbResourceModel[],
    bizIdNameMap: Record<number, string>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const copy = useCopy();

  const filterMap = computed(() => {
    const currentBizNameMap = props.bizIdNameMap;
    const bizNameMap: Props['bizIdNameMap'] = {};
    const resourceTypesSet = new Set<string>();
    const deviceClassSet = new Set<string>();

    props.data.forEach((dataItem) => {
      dataItem.for_bizs.forEach((forBizItem) => {
        if (!bizNameMap[forBizItem.bk_biz_id]) {
          bizNameMap[forBizItem.bk_biz_id] = currentBizNameMap[forBizItem.bk_biz_id];
        }
      });

      dataItem.resource_types.forEach((resourceTypesItem) => {
        resourceTypesSet.add(resourceTypesItem);
      });

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
        <>
          <HightLightText
            keyWord={props.keyword}
            text={data.ip}
            highLightColor='#FF9C01' />
          <bk-button
            class="ml-4"
            text
            theme="primary"
            onclick={() => handleCopy(data.ip)}>
            <db-icon type="copy" />
          </bk-button>
        </>
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
      label: t('专用业务'),
      field: 'for_bizs',
      width: 100,
      filter: {
        list: Object.entries(filterMap.value.bizNameMap).reduce((prevList, bizItem) => [...prevList, {
          value: Number(bizItem[0]),
          text: bizItem[1],
        }], [] as {
          value: number,
          text: string
        }[]),
        filterFn: (checked: number[], row: DbResourceModel) => {
          if (checked.length === 0) {
            return true;
          }
          return checked.some(checkedItem => row.for_bizs.some(forBizItem => forBizItem.bk_biz_id === checkedItem));
        },
      },
      render: ({ data }: { data: DbResourceModel }) => {
        if (data.for_bizs.length < 1) {
          return t('无限制');
        }
        return data.for_bizs.map(item => <bk-tag>{item.bk_biz_name}</bk-tag>);
      },
    },
    {
      label: t('专用DB'),
      field: 'resource_types',
      filter: {
        list: Array.from(filterMap.value.resourceTypesSet).map(resourceTypeItem => ({
          value: resourceTypeItem,
          text: resourceTypeItem,
        })),
        filterFn: (checked: string[], row: DbResourceModel) => {
          if (checked.length === 0) {
            return true;
          }
          return checked.some(checkedItem => row.resource_types
            .some(resourceTypeItem => resourceTypeItem === checkedItem));
        },
      },
      render: ({ data }: { data: DbResourceModel }) => {
        if (data.resource_types.length < 1) {
          return t('无限制');
        }
        return data.resource_types.map(typeItem => <bk-tag>{typeItem}</bk-tag>);
      },
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
      'for_bizs',
      'resource_types',
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
</script>

<style lang="less" scoped>
@import "../style/table-card.less";
</style>

