<template>
  <div>
    <DbCard
      v-for="item in renderData.dataList"
      :key="item.clusterType"
      class="search-result-cluster search-result-card"
      mode="collapse"
      :title="item.clusterType">
      <template #desc>
        <span>{{ t('共n条', { n: item.dataList.length }) }}</span>
        <BkButton
          class="ml-16"
          text
          theme="primary"
          @click.stop="handleExport(item.clusterType, item.dataList)">
          <DbIcon type="host-select export-button-icon" />
          <span class="export-button-text">{{ t('导出') }}</span>
        </BkButton>
      </template>
      <DbOriginalTable
        cell-class="custom-table-cell"
        class="search-result-table mt-14 mb-8"
        :columns="columnsMap[item.clusterType]"
        :data="item.dataList" />
    </DbCard>
  </div>
</template>

<script setup lang="tsx">
  import type { Column } from 'bkui-vue/lib/table/props';
  import { useI18n } from 'vue-i18n';

  import QuickSearchInstanceModel from '@services/model/quiker-search/quick-search-instance';

  import {
    useCopy,
    useLocation,
  } from '@hooks';

  import {
    type ClusterInstStatus,
    clusterInstStatus,
  } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';
  import HightLightText from '@components/system-search/components/search-result/render-result/components/HightLightText.vue';

  import { formatCluster } from '../common/utils';

  import { exportExcelFile } from '@/utils';

  interface Props {
    keyword: string,
    data: QuickSearchInstanceModel[],
    bizIdNameMap: Record<number, string>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const copy = useCopy();
  const location = useLocation();

  const renderData = computed(() => formatCluster<QuickSearchInstanceModel>(props.data));
  const columnsMap = computed(() => {
    const {
      dataList,
      bizMap,
    } = renderData.value;
    const { bizIdNameMap } = props;

    return dataList.reduce((prevColumnsMap, dataItem) => {
      const bizList = Array.from(bizMap[dataItem.clusterType]).map(bizId => ({
        value: bizId,
        text: bizIdNameMap[bizId],
      }));

      return Object.assign(prevColumnsMap, {
        [dataItem.clusterType]: [
          {
            label: t('主访问入口'),
            field: 'cluster_domain',
            width: 160,
            render: ({ data }: { data: QuickSearchInstanceModel }) => <>
              <bk-button
                text
                theme="primary"
                onclick={() => handleToInstance(data)}>
                <span>{data.cluster_domain}</span>
              </bk-button>
              <bk-button
                class="copy-button ml-4"
                text
                theme="primary"
                onclick={() => handleCopy(data.cluster_domain)}>
                <db-icon type="copy" />
              </bk-button>
            </>,
          },
          // {
          //   label: t('集群名称'),
          //   field: 'cpu',
          //   render: ({ data }: { data: QuickSearchInstanceModel }) => data || '--',
          // },
          // {
          //   label: t('管控区域'),
          //   field: 'bk_idc_name',
          //   render: ({ data }: { data: QuickSearchInstanceModel }) => data.bk_idc_name || '--',
          // },
          {
            label: t('状态'),
            field: 'bk_idc_name',
            render: ({ data }: { data: QuickSearchInstanceModel }) => {
              const info = clusterInstStatus[data.status as ClusterInstStatus] || clusterInstStatus.unavailable;
              return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
            },
          },
          {
            label: t('实例'),
            field: 'instance',
            render: ({ data }: { data: QuickSearchInstanceModel }) => (
              <>
                <HightLightText
                  keyWord={props.keyword}
                  text={data.instance}
                  highLightColor='#FF9C01' />
                <bk-button
                  class="copy-button ml-4"
                  text
                  theme="primary"
                  onclick={() => handleCopy(data.instance)}>
                  <db-icon type="copy" />
                </bk-button>
              </>
            ),
          },
          {
            label: t('所属DB模块'),
            field: 'cluster_type',
            render: ({ data }: { data: QuickSearchInstanceModel }) => data.cluster_type || '--',
          },
          {
            label: t('业务'),
            field: 'bk_biz_id',
            filter: {
              list: bizList,
            },
            render: ({ data }: { data: QuickSearchInstanceModel }) => props.bizIdNameMap[data.bk_biz_id] || '--',
          },
          // {
          //   label: t('创建人'),
          //   field: 'bk_idc_name',
          //   render: ({ data }: { data: QuickSearchInstanceModel }) => data.bk_idc_name || '--',
          // },
          // {
          //   label: t('创建时间'),
          //   field: 'bk_idc_name',
          //   render: ({ data }: { data: QuickSearchInstanceModel }) => data.bk_idc_name || '--',
          // },
        ],
      });
    }, {} as Record<string, Array<Column>>);
  });

  const handleExport = (clusterType: string, dataList: QuickSearchInstanceModel[]) => {
    // TODO 字段待后端提供
    const formatData = dataList.map(dataItem => ({
      [t('主机ID')]: '',
      [t('云区域ID')]: '',
      [t('IP')]: dataItem.ip,
      [t('IP端口')]: String(dataItem.port),
      [t('实例角色')]: dataItem.role,
      [t('城市')]: '',
      [t('机房')]: '',
      [t('集群ID')]: dataItem.cluster_id,
      [t('集群名称')]: '',
      [t('集群别名')]: '',
      [t('集群类型')]: dataItem.cluster_type,
      [t('主域名')]: dataItem.cluster_domain,
      [t('主版本')]: '',
    }));
    const colsWidths = [
      { width: 10 },
      { width: 10 },
      { width: 16 },
      { width: 24 },
      { width: 20 },
      { width: 10 },
      { width: 10 },
      { width: 10 },
      { width: 16 },
      { width: 16 },
      { width: 24 },
      { width: 24 },
      { width: 16 },
    ];

    exportExcelFile(formatData, colsWidths, clusterType, `${clusterType}.xlsx`);
  };

  const handleCopy = (content: string) => {
    copy(content);
  };

  const handleToInstance = (data: QuickSearchInstanceModel) => {
    const routerNameMap = {
      TwemproxyRedisInstance: 'DatabaseRedisList',
      tendbha: 'DatabaseTendbha',
      tendbsingle: 'DatabaseTendbsingle',
      tendbcluster: 'tendbClusterList',
      es: 'EsList',
      kafka: 'KafkaList',
      hdfs: 'HdfsList',
      pulsar: 'PulsarList',
      redis: 'DatabaseRedisList',
      influxdb: 'InfluxDBInstDetails',
      riak: 'RiakList',
    } as Record<string, string>;

    if (data.cluster_type === 'tendbha') {
      location({
        name: 'DatabaseTendbhaInstance',
        query: {
          ip: data.ip,
        },
      }, data.bk_biz_id);
    } if (data.cluster_type === 'tendbcluster') {
      location({
        name: 'tendbClusterInstance',
        query: {
          ip: data.ip,
        },
      }, data.bk_biz_id);
    } else {
      location({
        name: routerNameMap[data.cluster_type],
        query: {
          id: data.id,
        },
      }, data.bk_biz_id);
    }
  };
</script>

<style lang="less" scoped>
@import "../style/table-card.less";

.search-result-cluster {
  .export-button-icon {
    font-size: 14px;
  }

  .export-button-text {
    margin-left: 4px;
    font-size: 12px;
  }

  .search-result-table {
    :deep(.custom-table-cell) {
      .copy-button {
        display: none;
      }

      &:hover {
        .copy-button {
          display: inline-block;
        }
      }
    }
  }
}
</style>
