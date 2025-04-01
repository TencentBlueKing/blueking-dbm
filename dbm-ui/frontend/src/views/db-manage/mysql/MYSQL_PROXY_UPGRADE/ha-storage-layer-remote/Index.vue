<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <SmartAction>
    <EditableTable
      ref="table"
      class="mb-20"
      :model="formData.tableData"
      :rules="rules">
      <EditableRow
        v-for="(item, index) in formData.tableData"
        :key="index">
        <WithRelatedClustersColumn
          v-model="item.cluster"
          :selected="selected"
          @batch-edit="handleBatchEdit" />
        <EditableColumn
          :label="t('主从主机')"
          :min-width="200">
          <EditableBlock v-if="item.cluster.master_host?.bk_host_id">
            <div class="host-item">
              <div class="host-tag host-tag-master">M</div>
              {{ item.cluster.master_host.ip }}
            </div>
            <div class="host-item">
              <div class="host-tag host-tag-slave">S</div>
              {{ item.cluster.slave_host.ip }}
            </div>
          </EditableBlock>
          <EditableBlock
            v-else
            :placeholder="t('自动生成')" />
        </EditableColumn>
        <EditableColumn
          :label="t('只读主机')"
          :min-width="200">
          <EditableBlock
            v-if="!item.cluster.id"
            :placeholder="t('自动生成')" />
          <EditableBlock
            v-else-if="item.cluster.id && !item.cluster.readonly_host"
            :placeholder="t('无只读主机')" />
          <EditableBlock
            v-else
            v-model="item.cluster.readonly_host.ip" />
        </EditableColumn>
        <CurrentVersionColumn :cluster="item.cluster" />
        <TargetVersionColumn
          v-model="item.target_version"
          :cluster="item.cluster"
          higher-major-version />
        <MultipleResourceHostColumn
          v-model="item.new_master_slave_host"
          field="new_master_slave_host"
          :label="t('新主从主机')"
          :limit="2"
          :min-width="200"
          :params="{
            for_bizs: [currentBizId, 0],
            resource_types: [DBTypes.MYSQL, 'PUBLIC'],
          }" />
        <NewReadonlyHostColumn
          v-model="item.new_readonly_host"
          :cluster="item.cluster" />
        <OperationColumn
          v-model:table-data="formData.tableData"
          :create-row-method="createTableRow" />
      </EditableRow>
    </EditableTable>
    <IgnoreBiz
      v-model="formData.force"
      v-bk-tooltips="t('如忽略_有连接的情况下也会执行')" />
    <BackupSource v-model="formData.backup_source" />
    <TicketPayload v-model="formData.payload" />
    <template #action>
      <BkButton
        class="mr-8 w-88"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <DbPopconfirm
        :confirm-handler="handleReset"
        :content="t('重置将会情况当前填写的所有内容_请谨慎操作')"
        :title="t('确认重置页面')">
        <BkButton
          class="ml8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>
<script lang="ts" setup>
  import { useTemplateRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import type { Mysql } from '@services/model/ticket/ticket';
  import { BackupSourceType } from '@services/types';

  import { useCreateTicket } from '@hooks';

  import { DBTypes, TicketTypes } from '@common/const';

  import MultipleResourceHostColumn from '@views/db-manage/common/toolbox-field/column/multiple-resource-host-column/Index.vue';
  import BackupSource from '@views/db-manage/common/toolbox-field/form-item/backup-source/Index.vue';
  import IgnoreBiz from '@views/db-manage/common/toolbox-field/form-item/ignore-biz/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import WithRelatedClustersColumn from '@views/db-manage/mysql/common/edit-table-column/WithRelatedClustersColumn.vue';

  import CurrentVersionColumn from '../components/CurrentVersionColumn.vue';
  import TargetVersionColumn from '../components/TargetVersionColumn.vue';

  import NewReadonlyHostColumn from './components/NewReadonlyHostColumn.vue';

  interface IHostData {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    ip: string;
  }

  interface RowData {
    cluster: {
      bk_cloud_id: number;
      cluster_type: string;
      current_version: string;
      db_module_id: number;
      db_module_name: string;
      id: number;
      master_domain: string;
      master_host: IHostData;
      package_version: string;
      readonly_host: IHostData;
      related_clusters: {
        id: number;
        master_domain: string;
      }[];
      slave_host: IHostData;
    };
    new_master_slave_host: IHostData[];
    new_readonly_host: IHostData;
    target_version: {
      charset: string;
      new_db_module_id: number;
      pkg_id: number;
      target_module_name: string;
      target_package: string;
      target_version: string;
    };
  }

  interface Props {
    ticketDetails?: Mysql.ResourcePool.MigrateUpgrade;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const initHostData = () => ({
    bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
    bk_cloud_id: 0,
    bk_host_id: 0,
    ip: '',
  });

  const createTableRow = (data = {} as Partial<RowData>) => ({
    cluster: data.cluster || {
      bk_cloud_id: 0,
      cluster_type: '',
      current_version: '',
      db_module_id: 0,
      db_module_name: '',
      id: 0,
      master_domain: '',
      master_host: initHostData(),
      package_version: '',
      readonly_host: initHostData(),
      readonly_slaves: [],
      related_clusters: [],
      slave_host: initHostData(),
    },
    new_master_slave_host: data.new_master_slave_host || ([] as IHostData[]),
    new_readonly_host: data.new_readonly_host || initHostData(),
    target_version: data.target_version || {
      charset: '',
      new_db_module_id: 0,
      pkg_id: 0,
      target_module_name: '',
      target_package: '',
      target_version: '',
    },
  });

  const defaultData = () => ({
    backup_source: BackupSourceType.REMOTE,
    force: false,
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const formData = reactive(defaultData());

  const selected = computed(() => formData.tableData.filter((item) => item.cluster.id).map((item) => item.cluster));
  const clusterMap = computed(() => {
    return formData.tableData.reduce<Record<string, string>>((acc, cur) => {
      Object.assign(acc, {
        [cur.cluster.master_domain]: cur.cluster.master_domain,
      });
      cur.cluster.related_clusters.forEach((item) => {
        Object.assign(acc, {
          [item.master_domain]: cur.cluster.master_domain, // 关联集群映射到所属集群
        });
      });
      return acc;
    }, {});
  });

  const rules = {
    'cluster.master_domain': [
      {
        message: '',
        trigger: 'blur',
        validator: (value: string) => {
          const target = clusterMap.value[value];
          if (target && target !== value) {
            return t('目标集群是集群target的关联集群_请勿重复添加', { target });
          }
          return true;
        },
      },
    ],
  };

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    backup_source: string;
    force: boolean;
    infos: {
      cluster_ids: number[];
      display_info: {
        charset: string;
        cluster_type: string;
        current_module_name: string;
        current_package: string;
        current_version: string;
        old_master_slave: string[];
        target_module_name: string;
        target_package: string;
        target_version: string;
      };
      new_db_module_id: number;
      pkg_id: number;
      read_only_slaves: {
        new_slave: IHostData;
        old_slave: IHostData;
      }[];
      resource_spec: {
        new_master: {
          hosts: IHostData[];
          spec_id: 0;
        };
        new_slave: {
          hosts: IHostData[];
          spec_id: 0;
        };
      };
    }[];
    ip_source: 'resource_pool';
  }>(TicketTypes.MYSQL_MIGRATE_UPGRADE, {
    ticketTypeRoute: TicketTypes.MYSQL_PROXY_UPGRADE,
  });

  watch(
    () => props.ticketDetails,
    () => {
      if (props.ticketDetails) {
        const { clusters, infos } = props.ticketDetails;
        if (infos.length > 0) {
          formData.tableData = infos.map((item) => {
            const clusterInfo = clusters[item.cluster_ids[0]];
            return createTableRow({
              cluster: {
                bk_cloud_id: clusterInfo.bk_cloud_id,
                cluster_type: clusterInfo.cluster_type,
                current_version: item.display_info.current_version,
                db_module_id: clusterInfo.db_module_id,
                db_module_name: item.display_info.current_module_name,
                id: clusterInfo.id,
                master_domain: clusterInfo.immute_domain,
                master_host: {
                  bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
                  bk_cloud_id: 0,
                  bk_host_id: 0,
                  ip: item.display_info.old_master_slave[0],
                },
                package_version: item.display_info.current_package,
                readonly_host: item.read_only_slaves[0].old_slave,
                related_clusters: [],
                slave_host: {
                  bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
                  bk_cloud_id: 0,
                  bk_host_id: 0,
                  ip: item.display_info.old_master_slave[1],
                },
              },
              new_master_slave_host: [item.resource_spec.new_master.hosts[0], item.resource_spec.new_slave.hosts[0]],
              new_readonly_host: item.read_only_slaves[0].new_slave,
              target_version: {
                charset: item.display_info.charset,
                new_db_module_id: item.new_db_module_id,
                pkg_id: item.pkg_id,
                target_module_name: item.display_info.target_module_name,
                target_package: item.display_info.target_package,
                target_version: item.display_info.target_version as string,
              },
            });
          });
        }
      }
    },
  );

  const handleBatchEdit = (list: TendbhaModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!clusterMap.value[item.master_domain]) {
        acc.push(
          createTableRow({
            cluster: {
              bk_cloud_id: item.bk_cloud_id,
              cluster_type: item.cluster_type,
              current_version: item.major_version,
              db_module_id: item.db_module_id,
              db_module_name: item.db_module_name,
              id: item.id,
              master_domain: item.master_domain,
              master_host: item.masters[0],
              package_version: item.masters[0]?.version || '',
              readonly_host: item.slaves.filter((item) => !item.is_stand_by)[0],
              related_clusters: [],
              slave_host: item.slaves.filter((item) => item.is_stand_by)[0],
            },
          }),
        );
      }
      return acc;
    }, []);
    formData.tableData = [...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList];
  };

  const handleSubmit = async () => {
    const result = await tableRef.value?.validate();
    if (result) {
      createTicketRun({
        details: {
          backup_source: formData.backup_source,
          force: formData.force,
          infos: formData.tableData.map((item) => ({
            cluster_ids: [item.cluster.id, ...item.cluster.related_clusters.map((item) => item.id)],
            display_info: {
              charset: item.target_version.charset,
              cluster_type: item.cluster.cluster_type,
              current_module_name: item.cluster.db_module_name,
              current_package: item.cluster.package_version,
              current_version: item.cluster.current_version,
              old_master_slave: [item.cluster.master_host.ip, item.cluster.slave_host.ip],
              target_module_name: item.target_version.target_module_name,
              target_package: item.target_version.target_package,
              target_version: item.target_version.target_version,
            },
            new_db_module_id: item.target_version.new_db_module_id,
            pkg_id: item.target_version.pkg_id,
            read_only_slaves: item.cluster.readonly_host
              ? [
                  {
                    new_slave: item.new_readonly_host,
                    old_slave: item.cluster.readonly_host,
                  },
                ]
              : [],
            resource_spec: {
              new_master: {
                hosts: [item.new_master_slave_host[0]],
                spec_id: 0,
              },
              new_slave: {
                hosts: [item.new_master_slave_host[1]],
                spec_id: 0,
              },
            },
          })),
          ip_source: 'resource_pool',
        },
        ...formData.payload,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };
</script>
<style lang="less" scoped>
  .host-item {
    display: flex;
    align-items: center;

    .host-tag {
      width: 16px;
      height: 16px;
      margin-right: 4px;
      font-size: @font-size-mini;
      font-weight: bolder;
      line-height: 16px;
      text-align: center;
    }

    .host-tag-master {
      color: @primary-color;
      background-color: #cad7eb;
    }

    .host-tag-slave {
      color: #2dcb56;
      background-color: #c8e5cd;
    }
  }
</style>
