<template>
  <BatchInput
    :config="batchInputConfig"
    @change="handleBatchInput" />
  <EditableTable
    :key="tableKey"
    ref="editableTable"
    class="mt-16 mb-16"
    :model="tableData">
    <EditableRow
      v-for="(item, index) in tableData"
      :key="index">
      <HostColumn
        v-model="item.host"
        :cluster-types="['RedisHost']"
        hide-manual-input
        :label="t('目标主机')"
        :selected="selected"
        :tab-list-config="tabListConfig"
        @batch-edit="handleHostBatchEdit" />
      <EditableColumn
        :label="t('所属集群')"
        readonly
        :width="200">
        <EditableBlock :placeholder="t('输入集群后自动生成')">
          {{ item.host.related_clusters?.[0]?.immute_domain }}
        </EditableBlock>
      </EditableColumn>
      <CurrentVersionColumn
        v-model="item.current_versions"
        :cluster-id="item.host.related_clusters.length ? item.host.related_clusters[0].id : 0"
        :ip="item.host.ip"
        :node-type="nodeType" />
      <TargetVersionColumn
        v-model="item.target_version"
        :cluster-id="item.host.related_clusters.length ? item.host.related_clusters[0].id : 0"
        :current-versions="item.current_versions"
        :ip="item.host.ip"
        :node-type="nodeType" />
      <OperationColumn
        :create-row-method="createRowData"
        :table-data="tableData" />
    </EditableRow>
  </EditableTable>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';
  import { type Redis } from '@services/model/ticket/ticket';
  import { getRedisClusterList } from '@services/source/redis';

  import { useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import { type IValue, type PanelListType } from '@components/instance-selector/Index.vue';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import HostColumn from '@views/db-manage/redis/common/toolbox-field/host-column/Index.vue';

  import { random } from '@utils';

  import CurrentVersionColumn from '../common/CurrentVersionByIpColumn.vue';
  import TargetVersionColumn from '../common/TargetVersionByIpColumn.vue';

  interface Props {
    nodeType: string;
  }

  interface Exposes {
    getValue: () => Promise<
      {
        cluster_id: number;
        current_versions: string[];
        node_type: string;
        slave_current_versions: string[]; // 回显
        target_versions: {
          instance_role: string; // 回显
          ip: string;
          related_clusters: string[]; // 回显
          slave_ip: string; // 回显
          version: string;
        }[];
      }[]
    >;
    resetTable: () => void;
  }

  interface IDataRow {
    current_versions: string[];
    host: {
      bk_host_id: number;
      cluster_type: string;
      ip: string;
      related_clusters: {
        id: number;
        immute_domain: string;
      }[];
    };
    target_version: string;
  }

  const props = defineProps<Props>();

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    current_versions: values?.current_versions || ([] as string[]),
    host: Object.assign(
      {
        bk_host_id: 0,
        cluster_type: '',
        ip: '',
        related_clusters: [] as IDataRow['host']['related_clusters'],
      },
      values.host,
    ),
    target_version: values?.target_version || '',
  });

  const { t } = useI18n();

  const editableTableRef = useTemplateRef('editableTable');

  useTicketDetail<Redis.VersionUpdateOnline>(TicketTypes.REDIS_VERSION_UPDATE_ONLINE, {
    onSuccess(ticketDetail) {
      const { infos } = ticketDetail.details;
      const targerVersionList = infos.flatMap((item) => item.target_versions);
      tableData.value = targerVersionList.map((item) => {
        return createRowData({
          host: {
            ip: item.ip,
          } as IDataRow['host'],
          target_version: item.version,
        });
      });
    },
  });

  const batchInputConfig = [
    {
      case: '192.168.10.2',
      key: 'ip',
      label: t('目标主机'),
    },
    {
      case: 'Redis-6',
      key: 'version',
      label: t('目标版本'),
    },
  ];

  const tabListConfig = {
    RedisHost: [
      {
        name: t('接入层主机'),
        tableConfig: {
          firsrColumn: {
            field: 'ip',
            label: 'IP',
            role: 'proxy',
          },
        },
        topoConfig: {
          countFunc: (clusterItem: { proxy: { ip: string }[] }) => {
            const ipList = clusterItem.proxy.map((hostItem) => hostItem.ip);
            return new Set(ipList).size;
          },
          getTopoList: (params: ServiceParameters<typeof getRedisClusterList>) =>
            getRedisClusterList({
              ...params,
              cluster_type: [
                ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
                ClusterTypes.PREDIXY_REDIS_CLUSTER,
                ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
                ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
              ].join(','),
            }),
          totalCountFunc: (dataList: RedisModel[]) => {
            const ipSet = new Set<string>();
            dataList.forEach((dataItem) => dataItem.proxy.forEach((masterItem) => ipSet.add(masterItem.ip)));
            return ipSet.size;
          },
        },
      },
    ],
  } as unknown as Record<ClusterTypes, PanelListType>;

  const tableData = ref([createRowData()]);
  const tableKey = ref(random());

  const selected = computed(() => tableData.value.filter((item) => item.host.bk_host_id).map((item) => item.host));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  const handleHostBatchEdit = (list: IValue[]) => {
    const newList: IDataRow[] = [];
    list.forEach((item) => {
      if (!selectedMap.value[item.ip]) {
        newList.push(
          createRowData({
            host: {
              bk_host_id: item.bk_host_id,
              cluster_type: item.cluster_type,
              ip: item.ip,
              related_clusters: item.related_clusters,
            },
          }),
        );
      }
    });
    tableData.value = [...(selected.value.length ? tableData.value : []), ...newList];
    window.changeConfirm = true;
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const newList = data.reduce<IDataRow[]>((acc, item) => {
      acc.push(
        createRowData({
          host: {
            ip: item.ip,
          } as IDataRow['host'],
          target_version: item.version,
        }),
      );
      return acc;
    }, []);

    if (isClear) {
      tableKey.value = random();
      tableData.value = [...newList];
    } else {
      tableData.value = [...(selected.value.length ? tableData.value : []), ...newList];
    }

    setTimeout(() => {
      editableTableRef.value!.validate();
    }, 200);
  };

  defineExpose<Exposes>({
    getValue: () =>
      editableTableRef.value!.validate().then((validateResult) => {
        if (validateResult) {
          const clusterMap = tableData.value.reduce<Record<string, Awaited<ReturnType<Exposes['getValue']>>[number]>>(
            (prev, item) => {
              const clusterId = item.host.related_clusters[0].id;
              const targetVersionItem = {
                instance_role: '',
                ip: item.host.ip,
                related_clusters: item.host.related_clusters.map((item) => item.immute_domain),
                slave_ip: '',
                version: item.target_version,
              };
              if (prev[clusterId]) {
                return Object.assign(prev, {
                  [clusterId]: {
                    ...prev[clusterId],
                    target_versions: prev[clusterId].target_versions.concat(targetVersionItem),
                  },
                });
              } else {
                return Object.assign(prev, {
                  [clusterId]: {
                    cluster_id: clusterId,
                    current_versions: item.current_versions,
                    node_type: props.nodeType,
                    slave_current_versions: [],
                    target_versions: [targetVersionItem],
                  },
                });
              }
            },
            {},
          );

          return Object.values(clusterMap);
        }
        return Promise.reject([]);
      }),
    resetTable: () => {
      tableData.value = [createRowData()];
    },
  });
</script>
