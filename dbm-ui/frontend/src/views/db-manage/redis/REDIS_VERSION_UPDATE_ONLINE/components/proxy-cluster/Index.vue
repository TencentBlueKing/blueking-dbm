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
      <ClusterColumn
        v-model="item.cluster"
        :selected="selected"
        :tab-list-config="tabListConfig"
        @batch-edit="handleClusterBatchEdit" />
      <EditableColumn
        :label="t('架构版本')"
        readonly
        :width="200">
        <EditableBlock :placeholder="t('输入集群后自动生成')">
          {{ item.cluster.cluster_type_name }}
        </EditableBlock>
      </EditableColumn>
      <CurrentVersionColumn
        v-model="item.current_versions"
        :cluster-id="item.cluster.id"
        :node-type="nodeType" />
      <TargetVersionColumn
        v-model="item.target_version"
        :cluster-id="item.cluster.id"
        :current-versions="item.current_versions"
        :node-type="nodeType" />
      <OperationColumn
        :create-row-method="createRowData"
        :table-data="tableData" />
    </EditableRow>
  </EditableTable>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';
  import { type Redis } from '@services/model/ticket/ticket';
  import { getRedisList } from '@services/source/redis';

  import { useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import { type TabItem } from '@components/cluster-selector/Index.vue';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';
  import ClusterColumn from '@views/db-manage/redis/common/toolbox-field/cluster-column/Index.vue';

  import { random } from '@utils';

  import CurrentVersionColumn from '../common/CurrentVersionByClusterColumn.vue';
  import TargetVersionColumn from '../common/TargetVersionByClusterColumn.vue';

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
    cluster: {
      cluster_type: string;
      cluster_type_name: string;
      id: number;
      master_domain: string;
      proxy: RedisModel['proxy'];
    };
    current_versions: string[];
    target_version: string;
  }

  const props = defineProps<Props>();

  const createRowData = (values = {} as Partial<IDataRow>) => ({
    cluster: Object.assign(
      {
        cluster_type: '',
        cluster_type_name: '',
        id: 0,
        master_domain: '',
        proxy: [] as RedisModel['proxy'],
      },
      values.cluster,
    ),
    current_versions: values?.current_versions || ([] as string[]),
    target_version: values?.target_version || '',
  });

  const { t } = useI18n();

  const editableTableRef = useTemplateRef('editableTable');

  useTicketDetail<Redis.VersionUpdateOnline>(TicketTypes.REDIS_VERSION_UPDATE_ONLINE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { clusters, infos } = details;
      tableData.value = infos.map((infoItem) => {
        return createRowData({
          cluster: {
            master_domain: clusters[infoItem.cluster_id].immute_domain,
          } as IDataRow['cluster'],
          target_version: infoItem.target_versions[0].version,
        });
      });
    },
  });

  const batchInputConfig = [
    {
      case: 'redis.test.1.db',
      key: 'master_domain',
      label: t('目标集群'),
    },
    {
      case: 'Redis-6',
      key: 'version',
      label: t('目标版本'),
    },
  ];

  const tabListConfig = {
    [ClusterTypes.REDIS]: {
      getResourceList: (params: ServiceParameters<typeof getRedisList>) =>
        getRedisList({
          cluster_type: [
            ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
            ClusterTypes.PREDIXY_REDIS_CLUSTER,
            ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
            ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
          ].join(','),
          ...params,
        }),
    },
  } as unknown as Record<ClusterTypes, TabItem>;

  const tableData = ref([createRowData()]);
  const tableKey = ref(random());

  const selected = computed(() => tableData.value.filter((item) => item.cluster.id).map((item) => item.cluster));
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

  const handleClusterBatchEdit = (list: RedisModel[]) => {
    const newList: IDataRow[] = [];
    list.forEach((item) => {
      if (!selectedMap.value[item.master_domain]) {
        newList.push(
          createRowData({
            cluster: {
              cluster_type: item.cluster_type,
              cluster_type_name: item.cluster_type_name,
              id: item.id,
              master_domain: item.master_domain,
              proxy: item.proxy,
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
          cluster: {
            master_domain: item.master_domain,
          } as IDataRow['cluster'],
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
          return tableData.value.map((tableItem) => ({
            cluster_id: tableItem.cluster.id,
            current_versions: tableItem.current_versions,
            node_type: props.nodeType,
            slave_current_versions: [],
            target_versions: _.uniqBy(
              tableItem.cluster.proxy.map((proxyItem) => ({
                instance_role: '',
                ip: proxyItem.ip,
                related_clusters: [],
                slave_ip: '',
                version: tableItem.target_version,
              })),
              'ip',
            ),
          }));
        }
        return Promise.reject([]);
      }),
    resetTable: () => {
      tableData.value = [createRowData()];
    },
  });
</script>
