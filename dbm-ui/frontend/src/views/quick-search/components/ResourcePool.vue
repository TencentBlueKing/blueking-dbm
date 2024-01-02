<template>
  <DbCard
    class="search-result-machine search-result-card"
    mode="collapse"
    :title="t('资源池主机')">
    <template #desc>
      {{ t('共n条', { n: data.length }) }}
    </template>
    <DbOriginalTable
      class="mt-14 mb-8"
      :columns="columns"
      :data="data" />
  </DbCard>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import DbResourceModel from '@services/model/db-resource/DbResource';

  import { useCopy } from '@hooks';

  import HostAgentStatus from '@components/cluster-common/HostAgentStatus.vue';
  import DiskPopInfo from '@components/disk-pop-info/DiskPopInfo.vue';
  import HightLightText from '@components/system-search/components/search-result/render-result/components/HightLightText.vue';

  interface Column {
    data: DbResourceModel
  }

  interface Props {
    keyword: string,
    data: DbResourceModel[],
    bizIdNameMap: Record<number, string>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const copy = useCopy();

  const renderBizNameMap = computed(() => {
    const currentBizNameMap = props.bizIdNameMap;
    return props.data.reduce((prevBizNameMap, dataItem) => {
      dataItem.for_bizs.forEach((forBizItem) => {
        if (!prevBizNameMap[forBizItem.bk_biz_id]) {
          return Object.assign(prevBizNameMap, {
            [forBizItem.bk_biz_id]: currentBizNameMap[forBizItem.bk_biz_id],
          });
        }
      });

      return prevBizNameMap;
    }, {} as Props['bizIdNameMap']);
  });

  const columns = computed(() => [
    {
      label: 'IP',
      field: 'ip',
      width: 160,
      render: ({ data }: Column) => <>
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
      </>,
    },
    {
      label: t('云区域'),
      field: 'bk_cloud_id',
      render: ({ data }: Column) => data.bk_cloud_id || '--',
    },
    {
      label: t('Agent状态'),
      field: 'agent_status',
      width: 100,
      render: ({ data }: Column) => <HostAgentStatus data={data.agent_status} />,
    },
    {
      label: t('专用业务'),
      field: 'for_bizs',
      width: 100,
      filter: {
        list: Object.entries(renderBizNameMap.value).reduce((prevList, bizItem) => [...prevList, {
          value: Number(bizItem[0]),
          text: bizItem[1],
        }], [] as {
          value: number,
          text: string
        }[]),
      },
      render: ({ data }: Column) => {
        if (data.for_bizs.length < 1) {
          return t('无限制');
        }
        return data.for_bizs.map(item => <bk-tag>{item.bk_biz_name}</bk-tag>);
      },
    },
    {
      label: t('专用DB'),
      field: 'resource_types',
      render: ({ data }: Column) => {
        if (data.resource_types.length < 1) {
          return t('无限制');
        }
        return data.resource_types.map(typeItem => <bk-tag>{typeItem}</bk-tag>);
      },
    },
    {
      label: t('机型'),
      field: 'device_class',
      render: ({ data }: Column) => data.device_class || '--',
    },
    {
      label: t('地域'),
      field: 'city',
      render: ({ data }: Column) => data.city || '--',
    },
    {
      label: t('园区'),
      field: 'sub_zone',
      render: ({ data }: Column) => data.sub_zone || '--',
    },
    {
      label: t('CPU(核)'),
      field: 'bk_cpu',
      render: ({ data }: Column) => data.bk_cpu || '--',
    },
    {
      label: t('内存(G)'),
      field: 'bkMemText',
      render: ({ data }: Column) => data.bkMemText || '0 M',
    },
    {
      label: t('磁盘容量(G)'),
      field: 'bk_disk',
      width: 100,
      render: ({ data }: Column) => (
        <DiskPopInfo data={data.storage_device}>
          <span style="line-height: 40px; color: #3a84ff;">
            {data.bk_disk}
          </span>
        </DiskPopInfo>
      ),
    },
  ]);

  const handleCopy = (content: string) => {
    copy(content);
  };
</script>

<style lang="less" scoped>
@import "../style/table-card.less";
</style>

