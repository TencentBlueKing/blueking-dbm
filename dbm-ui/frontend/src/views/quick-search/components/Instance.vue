<template>
  <div :key="settingChangeKey">
    <DbCard
      v-for="(item, index) in renderData.dataList"
      :key="item.clusterType"
      class="search-result-cluster search-result-card"
      mode="collapse"
      :title="item.clusterType">
      <template #desc>
        <I18nT
          class="ml-8"
          keypath="共n条"
          style="color: #63656e"
          tag="span">
          <template #n>
            <strong>{{ item.dataList.length }}</strong>
          </template>
        </I18nT>
        <BkButton
          class="ml-8"
          text
          theme="primary"
          @click.stop="handleExport(item.clusterType, item.dataList)">
          <DbIcon
            class="export-button-icon"
            type="daochu" />
          <span class="export-button-text">{{ t('导出') }}</span>
        </BkButton>
      </template>
      <DbOriginalTable
        class="search-result-table mt-14 mb-8"
        :columns="columnsMap[item.clusterType]"
        :data="item.dataList"
        :pagination="pagination[index]"
        :settings="tableSetting"
        @setting-change="updateTableSettings" />
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
    useTableSettings,
  } from '@hooks';

  import {
    type ClusterInstStatus,
    clusterInstStatus,
    UserPersonalSettings,
  } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';
  import HightLightText from '@components/system-search/components/search-result/render-result/components/HightLightText.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

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

  const settingChangeKey = ref(1);
  const pagination = ref<{
    count: number,
    limit: number
  }[]>([]);

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
            render: ({ data }: { data: QuickSearchInstanceModel }) => (
              <TextOverflowLayout>
                {{
                  default: () => (
                    <bk-button
                      text
                      theme="primary"
                      onclick={() => handleToInstance(data)}>
                      <span>{data.cluster_domain}</span>
                    </bk-button>
                  ),
                  append: () => (
                    <bk-button
                      class="ml-4"
                      text
                      theme="primary"
                      onclick={() => handleCopy(data.cluster_domain)}>
                      <db-icon type="copy" />
                    </bk-button>
                  ),
                }}
              </TextOverflowLayout>
            ),
          },
          {
            label: t('集群名称'),
            field: 'cluster_name',
            render: ({ data }: { data: QuickSearchInstanceModel }) => data.cluster_name || '--',
          },
          // {
          //   label: t('管控区域'),
          //   field: 'bk_idc_name',
          //   render: ({ data }: { data: QuickSearchInstanceModel }) => data.bk_idc_name || '--',
          // },
          {
            label: t('状态'),
            field: 'bk_idc_name',
            sort: true,
            render: ({ data }: { data: QuickSearchInstanceModel }) => {
              const info = clusterInstStatus[data.status as ClusterInstStatus] || clusterInstStatus.unavailable;
              return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
            },
          },
          {
            label: t('实例'),
            field: 'instance',
            render: ({ data }: { data: QuickSearchInstanceModel }) => (
              <TextOverflowLayout>
                {{
                  default: () => (
                    <HightLightText
                      keyWord={props.keyword}
                      text={data.instance}
                      highLightColor='#FF9C01' />
                  ),
                  append: () => (
                    <bk-button
                      class="ml-4"
                      text
                      theme="primary"
                      onclick={() => handleCopy(data.instance)}>
                      <db-icon type="copy" />
                    </bk-button>
                  ),
                }}
              </TextOverflowLayout>
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

  // 设置用户个人表头信息
  const defaultSettings = {
    fields: (Object.values(columnsMap.value)[0] || []).filter(item => item.field).map(item => ({
      label: item.label,
      field: item.field,
      disabled: ['cluster_domain', 'instance'].includes(item.field as string),
    })),
    checked: [
      'cluster_domain',
      'cluster_name',
      'bk_idc_name',
      'instance',
      'cluster_type',
      'bk_biz_id',
    ],
  };

  const {
    settings: tableSetting,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.QUICK_SEARCH_INSTANCE, defaultSettings);

  watch(tableSetting, () => {
    // 修改字段显示设置时，重新渲染所有表格。否则只有当前操作的表格会重新渲染
    settingChangeKey.value = settingChangeKey.value + 1;
  });

  watch(renderData, (newRenderData) => {
    pagination.value = newRenderData.dataList.map(dataItem => ({
      count: dataItem.dataList.length,
      limit: 10,
    }));
  }, {
    immediate: true,
  });

  const handleExport = (clusterType: string, dataList: QuickSearchInstanceModel[]) => {
    const formatData = dataList.map(dataItem => ({
      [t('主机ID')]: String(dataItem.bk_host_id),
      [t('云区域ID')]: String(dataItem.bk_cloud_id),
      [t('IP')]: dataItem.ip,
      [t('IP端口')]: String(dataItem.port),
      [t('实例角色')]: dataItem.role,
      [t('城市')]: dataItem.bk_idc_area,
      [t('机房')]: dataItem.bk_idc_name,
      [t('集群ID')]: dataItem.cluster_id,
      [t('集群名称')]: dataItem.cluster_name,
      [t('集群别名')]: dataItem.cluster_alias,
      [t('集群类型')]: dataItem.cluster_type,
      [t('主域名')]: dataItem.cluster_domain,
      [t('主版本')]: dataItem.major_version,
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
  @import '../style/table-card.less';

  .search-result-cluster {
    .export-button-icon {
      font-size: 14px;
    }

    .export-button-text {
      margin-left: 4px;
      font-size: 12px;
    }
  }
</style>
