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

  import QuickSearchClusterDomainModel from '@services/model/quiker-search/quick-search-cluster-domain';

  import {
    useCopy,
    useLocation,
    useTableSettings,
  } from '@hooks';

  import { UserPersonalSettings } from '@common/const';

  import RenderClusterStatus from '@components/cluster-common/RenderStatus.vue';
  import HightLightText from '@components/system-search/components/search-result/render-result/components/HightLightText.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { exportExcelFile } from '@utils';

  import { formatCluster } from '../common/utils';

  interface Props {
    keyword: string
    data: QuickSearchClusterDomainModel[],
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

  const renderData = computed(() => formatCluster<QuickSearchClusterDomainModel>(props.data));
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
            field: 'immute_domain',
            width: 160,
            render: ({ data }: { data: QuickSearchClusterDomainModel }) => (
              <TextOverflowLayout>
                {{
                  default: () => (
                    <bk-button
                      text
                      theme="primary"
                      onclick={() => handleToCluster(data)}>
                      <HightLightText
                        keyWord={props.keyword}
                        text={data.immute_domain}
                        highLightColor='#FF9C01' />
                    </bk-button>
                  ),
                  append: () => (
                    <bk-button
                      class="ml-4"
                      text
                      theme="primary"
                      onclick={() => handleCopy(data.immute_domain)}>
                      <db-icon type="copy" />
                    </bk-button>
                  ),
                }}
              </TextOverflowLayout>
            ),
          },
          {
            label: t('集群名称'),
            field: 'name',
            minWidth: 220,
            render: ({ data }: { data: QuickSearchClusterDomainModel }) => data.name || '--',
          },
          {
            label: t('管控区域'),
            field: 'bk_cloud_id',
            render: ({ data }: { data: QuickSearchClusterDomainModel }) => data.bk_cloud_id || '--',
          },
          {
            label: t('状态'),
            field: 'status',
            sort: true,
            render: ({ data }: { data: QuickSearchClusterDomainModel }) => <RenderClusterStatus data={data.status} />,
          },
          // {
          //   label: t('实例'),
          //   field: 'bk_idc_name',
          //   render: ({ data }: { data: QuickSearchClusterDomainModel } ) => data.bk_idc_name || '--',
          // },
          {
            label: t('所属DB模块'),
            field: 'cluster_type',
            width: 120,
            render: ({ data }: { data: QuickSearchClusterDomainModel }) => data.cluster_type || '--',
          },
          {
            label: t('业务'),
            field: 'bk_biz_id',
            filter: {
              list: bizList,
            },
            render: ({ data }: { data: QuickSearchClusterDomainModel }) => props.bizIdNameMap[data.bk_biz_id] || '--',
          },
          {
            label: t('创建人'),
            field: 'creator',
            sort: true,
            render: ({ data }: { data: QuickSearchClusterDomainModel }) => data.creator || '--',
          },
          {
            label: t('创建时间'),
            field: 'create_at',
            width: 150,
            sort: true,
            render: ({ data }: { data: QuickSearchClusterDomainModel }) => data.createAtDisplay || '--',
          },
        ],
      });
    }, {} as Record<string, Array<Column>>);
  });

  // 设置用户个人表头信息
  const defaultSettings = {
    fields: (Object.values(columnsMap.value)[0] || []).filter(item => item.field).map(item => ({
      label: item.label,
      field: item.field,
      disabled: item.field === 'immute_domain',
    })),
    checked: [
      'immute_domain',
      'name',
      'bk_cloud_id',
      'status',
      'cluster_type',
      'bk_biz_id',
      'creator',
      'create_at',
    ],
  };

  const {
    settings: tableSetting,
    updateTableSettings,
  } = useTableSettings(UserPersonalSettings.QUICK_SEARCH_CLUSTER_DOMAIN, defaultSettings);

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

  const handleExport = (clusterType: string, dataList: QuickSearchClusterDomainModel[]) => {
    const formatData = dataList.map(dataItem => ({
      [t('集群ID')]: String(dataItem.id),
      [t('集群名称')]: dataItem.name,
      [t('集群别名')]: dataItem.alias,
      [t('集群类型')]: dataItem.cluster_type,
      [t('主域名')]: dataItem.immute_domain,
      [t('主版本')]: dataItem.major_version,
      [t('地域')]: dataItem.region,
      [t('容灾等级')]: dataItem.disaster_tolerance_level,
    }));
    const colsWidths = [
      { width: 10 },
      { width: 16 },
      { width: 16 },
      { width: 24 },
      { width: 24 },
      { width: 16 },
      { width: 10 },
      { width: 10 },
    ];

    exportExcelFile(formatData, colsWidths, clusterType, `${clusterType}.xlsx`);
  };

  const handleCopy = (content: string) => {
    copy(content);
  };

  const handleToCluster = (data: QuickSearchClusterDomainModel) => {
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
      riak: 'RiakList',
    } as Record<string, string>;

    if (!routerNameMap[data.cluster_type]) {
      return;
    }

    location({
      name: routerNameMap[data.cluster_type],
      query: {
        id: data.id,
      },
    }, data.bk_biz_id);
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
