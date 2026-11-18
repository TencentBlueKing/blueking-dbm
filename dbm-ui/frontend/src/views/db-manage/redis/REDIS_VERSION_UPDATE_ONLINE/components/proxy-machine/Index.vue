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
        :cluster-types="[ClusterTypes.REDIS]"
        :data-source-map="dataSourceMap"
        :label="t('目标主机')"
        :selected="selected"
        :tab-name-map="{ [ClusterTypes.REDIS]: t('Proxy 主机') }"
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
        :ip="item.host.ip"
        :node-type="nodeType"
        :version-name="item.target_version_name" />
      <OperationColumn
        :create-row-method="createRowData"
        :table-data="tableData" />
    </EditableRow>
  </EditableTable>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { type Redis } from '@services/model/ticket/ticket';
  import { getRedisMachineList } from '@services/source/redis';

  import { useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import { type HostModel } from '@components/host-selector/Index.vue';

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
          db_version_id: number;
          instance_role: string;
          ip: string;
          related_clusters: string[];
          slave_ip: string;
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
    target_version: number | undefined; // db_version_id
    target_version_name?: string; // 批量导入的版本名
  }

  const props = defineProps<Props>();

  const createRowData = (values = {} as Partial<IDataRow>): IDataRow => ({
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
    target_version: values?.target_version,
    target_version_name: values?.target_version_name,
  });

  const { t } = useI18n();

  const editableTableRef = useTemplateRef('editableTable');

  useTicketDetail<Redis.VersionUpdateOnline>(TicketTypes.REDIS_VERSION_UPDATE_ONLINE, {
    onSuccess(ticketDetail) {
      const { infos } = ticketDetail.details;
      // 同一 ip 只保留一条（一台主机可关联多个集群）；新协议有 db_version_id，旧协议按 version 兜底，回填版本名由目标版本列映射成 id
      const targetIpSet = new Set<string>();
      const targerVersionList = infos
        .flatMap((item) => item.target_versions)
        .filter((item) => {
          if (targetIpSet.has(item.ip)) {
            return false;
          }
          targetIpSet.add(item.ip);
          return true;
        });
      tableData.value = targerVersionList.map((item) => {
        return createRowData({
          host: {
            ip: item.ip,
          } as IDataRow['host'],
          target_version: item.db_version_id,
          target_version_name: item.version_name || item.version,
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
      case: 'twemproxy-0.4.1-v36',
      key: 'version',
      label: t('目标版本'),
    },
  ];

  // 接入层主机：角色过滤 proxy
  const dataSourceMap = {
    [ClusterTypes.REDIS]: (params: ServiceParameters<typeof getRedisMachineList>) =>
      getRedisMachineList({
        ...params,
        instance_role: 'proxy',
      }),
  };

  const tableData = ref([createRowData()]);
  const tableKey = ref(random());

  const selected = computed(() => tableData.value.filter((item) => item.host.bk_host_id).map((item) => item.host));

  const handleHostBatchEdit = (list: HostModel<ClusterTypes.REDIS>[]) => {
    const newList: IDataRow[] = [];
    list.forEach((item) => {
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
    });
    // 追加模式：选择器只回传本次勾选，不按已有对象过滤（重复由主键列校验提示），丢弃主键为空的行
    tableData.value = [...tableData.value.filter((item) => item.host.ip), ...newList];
  };

  const handleBatchInput = (data: Record<string, any>[], isClear: boolean) => {
    const newList = data.reduce<IDataRow[]>((acc, item) => {
      acc.push(
        createRowData({
          host: {
            ip: item.ip,
          } as IDataRow['host'],
          target_version_name: item.version,
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
  };

  defineExpose<Exposes>({
    getValue: () =>
      editableTableRef.value!.validate().then(() => {
        const clusterMap = tableData.value.reduce<Record<string, Awaited<ReturnType<Exposes['getValue']>>[number]>>(
          (prev, item) => {
            const clusterId = item.host.related_clusters[0].id;
            const targetVersionItem = {
              db_version_id: item.target_version as number,
              instance_role: '',
              ip: item.host.ip,
              related_clusters: item.host.related_clusters.map((item) => item.immute_domain),
              slave_ip: '',
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
      }),
    resetTable: () => {
      tableData.value = [createRowData()];
    },
  });
</script>
