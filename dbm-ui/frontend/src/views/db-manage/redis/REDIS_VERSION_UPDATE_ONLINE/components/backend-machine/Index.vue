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
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import { type Redis } from '@services/model/ticket/ticket';

  import { useTicketDetail } from '@hooks';

  import { TicketTypes } from '@common/const';

  import { type IValue } from '@components/instance-selector/Index.vue';

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
    host: ComponentProps<typeof HostColumn>['modelValue'];
    slave_current_versions: string[];
    target_version: string;
  }

  const props = defineProps<Props>();

  const createRowData = (values = {} as Partial<IDataRow>) => ({
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
    target_version: values?.target_version || '',
  });

  const { t } = useI18n();

  const editableTableRef = useTemplateRef('editableTable');

  useTicketDetail<Redis.VersionUpdateOnline>(TicketTypes.REDIS_VERSION_UPDATE_ONLINE, {
    onSuccess(ticketDetail) {
      const { details } = ticketDetail;
      const { infos } = details;

      const ipMap: Record<string, Redis.VersionUpdateOnline['infos'][number]['target_versions'][number]> = {};
      const pairSlaveIpMap: Record<string, boolean> = {};
      infos.forEach((infoItem) => {
        infoItem.target_versions.forEach((targetItem) => {
          if (pairSlaveIpMap[targetItem.ip]) {
            return;
          }

          ipMap[targetItem.ip] = targetItem;
          if (targetItem.slave_ip) {
            pairSlaveIpMap[targetItem.slave_ip] = true;
          }
        });
      });

      tableData.value = Object.values(ipMap).map((item) => {
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
  const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.ip, true])));

  const handleHostBatchEdit = (list: IValue[]) => {
    const newList: IDataRow[] = [];
    list.forEach((item) => {
      if (!selectedMap.value[item.ip]) {
        newList.push(
          createRowData({
            host: {
              ip: item.ip,
            } as IDataRow['host'],
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
          const clusterMap: Record<string, Awaited<ReturnType<Exposes['getValue']>>[number]> = {};

          tableData.value.forEach((tableItem) => {
            tableItem.host.related_clusters.forEach((clusterItem) => {
              const clusterId = clusterItem.id;
              const targetVersionItem = {
                instance_role: tableItem.host.instance_role,
                ip: tableItem.host.ip,
                related_clusters: tableItem.host.related_clusters.map((item) => item.immute_domain),
                slave_ip: tableItem.host.instance_role === 'redis_master' ? tableItem.host.pair_machine.ip : '',
                version: tableItem.target_version,
              };
              if (clusterMap[clusterId]) {
                clusterMap[clusterId].target_versions.concat(targetVersionItem);
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
                  instance_role: 'redis_slave',
                  ip: tableItem.host.pair_machine.ip,
                  related_clusters: tableItem.host.related_clusters.map((item) => item.immute_domain),
                  slave_ip: '',
                  version: tableItem.target_version,
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
        }
        return Promise.reject([]);
      }),
    resetTable: () => {
      tableData.value = [createRowData()];
    },
  });
</script>
