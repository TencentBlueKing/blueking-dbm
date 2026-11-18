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
        :selected="selected"
        @batch-edit="handleHostBatchEdit" />
      <RoleColumn :host="item.host" />
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
        v-model:slave-versions="item.slave_current_versions"
        :cluster-id="item.host.related_clusters.length ? item.host.related_clusters[0].id : 0"
        :host="item.host"
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
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import { type Redis } from '@services/model/ticket/ticket';

  import { useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import { type HostModel } from '@components/host-selector/Index.vue';

  import BatchInput from '@views/db-manage/common/batch-input/Index.vue';

  import { random } from '@utils';

  import TargetVersionColumn from '../common/TargetVersionByIpColumn.vue';

  import CurrentVersionColumn from './components/CurrentVersionColumn.vue';
  import HostColumn from './components/HostColumn.vue';
  import RoleColumn from './components/RoleColumn.vue';

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
    host: ComponentProps<typeof HostColumn>['modelValue'];
    slave_current_versions: string[];
    target_version: number | undefined; // db_version_id
    target_version_name?: string; // 批量导入的版本名
  }

  const props = defineProps<Props>();

  const createRowData = (values = {} as Partial<IDataRow>): IDataRow => ({
    current_versions: values?.current_versions || ([] as string[]),
    host: Object.assign(
      {
        bk_cloud_id: 0,
        bk_host_id: 0,
        cluster_type: '',
        instance_role: '',
        ip: '',
        pair_machine: {
          bk_host_id: 0,
          ip: '',
          related_clusters: [] as IDataRow['host']['pair_machine']['related_clusters'],
        },
        related_clusters: [] as IDataRow['host']['related_clusters'],
      },
      values.host,
    ),
    slave_current_versions: values?.slave_current_versions || ([] as string[]),
    target_version: values?.target_version,
    target_version_name: values?.target_version_name,
  });

  const { t } = useI18n();

  const editableTableRef = useTemplateRef('editableTable');

  useTicketDetail<Redis.VersionUpdateOnline>(TicketTypes.REDIS_VERSION_UPDATE_ONLINE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { infos } = details;

      // 新协议：每台机器独立一条 target_versions 记录；同一 ip 只保留一条（一台主机可关联多个集群）；旧协议按 version 兜底，回填版本名由目标版本列映射成 id
      const targetIpSet = new Set<string>();
      tableData.value = infos
        .flatMap((infoItem) =>
          infoItem.target_versions.filter((targetItem) => {
            if (targetIpSet.has(targetItem.ip)) {
              return false;
            }
            targetIpSet.add(targetItem.ip);
            return true;
          }),
        )
        .map((targetItem) =>
          createRowData({
            host: {
              ip: targetItem.ip,
            } as IDataRow['host'],
            target_version: targetItem.db_version_id,
            target_version_name: targetItem.version_name || targetItem.version,
          }),
        );
    },
  });

  const batchInputConfig = [
    {
      case: '192.168.10.2',
      key: 'ip',
      label: t('目标主机'),
    },
    {
      case: 'redis-6.2.21',
      key: 'version',
      label: t('目标版本'),
    },
  ];

  const tableData = ref([createRowData()]);
  const tableKey = ref(random());

  const selected = computed(() =>
    tableData.value
      .filter((item) => item.host.bk_host_id)
      .flatMap((item) => {
        if (item.host.pair_machine.ip) {
          return [item.host, item.host.pair_machine];
        }
        return [item.host];
      }),
  );

  const handleHostBatchEdit = (list: HostModel<ClusterTypes.REDIS>[]) => {
    const newList: IDataRow[] = [];
    list.forEach((item) => {
      newList.push(
        createRowData({
          host: {
            ip: item.ip,
          } as IDataRow['host'],
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
        const clusterMap: Record<string, Awaited<ReturnType<Exposes['getValue']>>[number]> = {};

        tableData.value.forEach((tableItem) => {
          tableItem.host.related_clusters.forEach((clusterItem) => {
            const clusterId = clusterItem.id;
            const targetVersionItem = {
              db_version_id: tableItem.target_version as number,
              instance_role: tableItem.host.instance_role,
              ip: tableItem.host.ip,
              related_clusters: tableItem.host.related_clusters.map((item) => item.immute_domain),
              slave_ip: tableItem.host.instance_role === 'redis_master' ? tableItem.host.pair_machine.ip : '',
            };
            if (clusterMap[clusterId]) {
              clusterMap[clusterId].target_versions.push(targetVersionItem);
            } else {
              Object.assign(clusterMap, {
                [clusterId]: {
                  cluster_id: clusterId,
                  current_versions: tableItem.current_versions,
                  node_type: props.nodeType,
                  slave_current_versions: [],
                  target_versions: [targetVersionItem],
                },
              });
            }
          });
          if (tableItem.host.pair_machine.ip) {
            tableItem.host.pair_machine.related_clusters.forEach((pairClusterItem) => {
              const clusterId = pairClusterItem.id;
              const targetVersionItem = {
                db_version_id: tableItem.target_version as number,
                instance_role: 'redis_slave',
                ip: tableItem.host.pair_machine.ip,
                related_clusters: tableItem.host.related_clusters.map((item) => item.immute_domain),
                slave_ip: '',
              };
              if (clusterMap[clusterId]) {
                clusterMap[clusterId].slave_current_versions = tableItem.slave_current_versions;
                clusterMap[clusterId].target_versions.push(targetVersionItem);
              } else {
                Object.assign(clusterMap, {
                  [clusterId]: {
                    cluster_id: clusterId,
                    current_versions: tableItem.current_versions,
                    node_type: props.nodeType,
                    slave_current_versions: tableItem.slave_current_versions,
                    target_versions: [targetVersionItem],
                  },
                });
              }
            });
          }
        });

        return Object.values(clusterMap);
      }),
    resetTable: () => {
      tableData.value = [createRowData()];
    },
  });
</script>
