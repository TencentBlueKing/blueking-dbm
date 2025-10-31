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
  <UpgradeWrapper v-model="wrapperController">
    <SmartAction class="db-toolbox">
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
          <ClusterHostColumn :cluster="item.cluster" />
          <CurrentVersionColumn
            v-model="item.current_version"
            :cluster="item.cluster" />
          <TargetVersionColumn
            v-model="item.target_version"
            v-model:new-db-module-id="item.new_db_module_id"
            v-model:pkg-id="item.pkg_id"
            :cluster="item.cluster" />
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
      <BkFormItem class="mb-8">
        <BkCheckbox
          v-model="formData.is_check_process"
          :false-label="false"
          true-label>
          <span
            v-bk-tooltips="t('存在业务连接时需要人工确认')"
            class="safe-action-text">
            {{ t('检查业务连接') }}
          </span>
        </BkCheckbox>
      </BkFormItem>
      <BackupSource v-model="formData.backup_source" />
      <BkFormItem
        :label="t('数据校验')"
        property="need_checksum">
        <BkSwitcher
          v-model="formData.need_checksum"
          theme="primary" />
      </BkFormItem>
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
            class="ml-8 w-88"
            :disabled="isSubmitting">
            {{ t('重置') }}
          </BkButton>
        </DbPopconfirm>
      </template>
    </SmartAction>
  </UpgradeWrapper>
</template>
<script lang="ts" setup>
  import { useTemplateRef } from 'vue';
  import type { ComponentProps } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import type { Mysql } from '@services/model/ticket/ticket';
  import { BackupSourceType } from '@services/types';

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, DBTypes, TicketTypes } from '@common/const';

  import MultipleResourceHostColumn from '@views/db-manage/common/toolbox-field/column/multiple-resource-host-column/Index.vue';
  import BackupSource from '@views/db-manage/common/toolbox-field/form-item/backup-source/Index.vue';
  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import WithRelatedClustersColumn from '@views/db-manage/mysql/common/edit-table-column/WithRelatedClustersColumn.vue';
  import CurrentVersionColumn from '@views/db-manage/mysql/MYSQL_LOCAL_UPGRADE/components/CurrentVersionColumn.vue';
  import TargetVersionColumn from '@views/db-manage/mysql/MYSQL_LOCAL_UPGRADE/components/TargetVersionColumn.vue';
  import UpgradeWrapper from '@views/db-manage/mysql/MYSQL_LOCAL_UPGRADE/components/UpgradeWrapper.vue';

  import ClusterHostColumn from './components/ClusterHostColumn.vue';
  import NewReadonlyHostColumn from './components/NewReadonlyHostColumn.vue';

  interface IHostData {
    bk_biz_id: number;
    bk_cloud_id: number;
    bk_host_id: number;
    ip: string;
  }

  interface RowData {
    cluster: {
      cluster_type: ClusterTypes;
      id: number;
      master_domain: string;
      related_clusters: {
        id: number;
        master_domain: string;
      }[];
    } & TendbhaModel;
    current_version: ComponentProps<typeof CurrentVersionColumn>['modelValue'];
    new_db_module_id: number;
    new_master_slave_host: IHostData[];
    new_readonly_host: IHostData[];
    pkg_id: number;
    readonly_host: IHostData[];
    target_version: ComponentProps<typeof TargetVersionColumn>['modelValue'];
  }

  const { t } = useI18n();
  const tableRef = useTemplateRef('table');

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  const createTableRow = (data = {} as DeepPartial<RowData>) => ({
    cluster: Object.assign(
      {
        cluster_type: '',
        id: 0,
        master_domain: '',
        related_clusters: [],
      } as unknown as RowData['cluster'],
      data.cluster,
    ),
    current_version: Object.assign(
      {
        charset: '',
        db_module_name: '',
        db_version: '',
        pkg_name: '',
      },
      data.current_version,
    ),
    new_db_module_id: data.new_db_module_id || 0,
    new_master_slave_host: (data.new_master_slave_host as IHostData[]) || [],
    new_readonly_host: (data.new_readonly_host as IHostData[]) || [],
    pkg_id: data.pkg_id || 0,
    readonly_host: (data.readonly_host as IHostData[]) || [],
    target_version: Object.assign(
      {
        charset: '',
        db_module_name: '',
        db_version: '',
        pkg_name: '',
      },
      data.target_version,
    ),
  });

  const defaultData = () => ({
    backup_source: BackupSourceType.REMOTE,
    is_check_process: true,
    need_checksum: true,
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const wrapperController = ref({
    roleType: 'haStorageLayer',
    updateType: TicketTypes.MYSQL_MIGRATE_UPGRADE,
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

  useTicketDetail<Mysql.ResourcePool.MigrateUpgrade>(TicketTypes.MYSQL_MIGRATE_UPGRADE, {
    onSuccess(ticketDetail) {
      const { clusters, infos } = ticketDetail.details;
      if (infos.length > 0) {
        Object.assign(formData, {
          ...createTickePayload(ticketDetail),
          is_check_process: ticketDetail.details.is_check_process,
          need_checksum: ticketDetail.details.need_checksum,
          tableData: ticketDetail.details.infos.map((item) =>
            createTableRow({
              cluster: {
                master_domain: clusters[item.cluster_ids[0]].immute_domain,
              },
              new_db_module_id: item.new_db_module_id,
              new_master_slave_host: [item.resource_spec.new_master.hosts[0], item.resource_spec.new_slave.hosts[0]],
              new_readonly_host: item.read_only_slaves.map((item) => item.new_slave),
              pkg_id: item.pkg_id,
              target_version: {
                charset: item.display_info.charset,
                db_module_name: item.display_info.target_module_name,
                db_version: item.display_info.target_version,
                pkg_name: item.display_info.target_package,
              },
            }),
          ),
        });
      }
    },
  });

  const { loading: isSubmitting, run: createTicketRun } = useCreateTicket<{
    backup_source: string;
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
    is_check_process: boolean;
    need_checksum: boolean;
  }>(TicketTypes.MYSQL_MIGRATE_UPGRADE);

  const handleBatchEdit = (list: TendbhaModel[]) => {
    const dataList = list.reduce<RowData[]>((acc, item) => {
      if (!clusterMap.value[item.master_domain]) {
        acc.push(
          createTableRow({
            cluster: {
              master_domain: item.master_domain,
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
          infos: formData.tableData.map((item) => ({
            cluster_ids: [item.cluster.id, ...item.cluster.related_clusters.map((item) => item.id)],
            display_info: {
              charset: item.target_version.charset,
              cluster_type: item.cluster.cluster_type,
              current_module_name: item.cluster.db_module_name,
              current_package: item.current_version.pkg_name,
              current_version: item.current_version.db_version,
              old_master_slave: [
                item.cluster.masters?.[0]?.ip,
                item.cluster.slaves.filter((slave) => slave.is_stand_by)?.[0]?.ip,
              ],
              target_module_name: item.target_version.db_module_name,
              target_package: item.target_version.pkg_name,
              target_version: item.target_version.db_version,
            },
            new_db_module_id: item.new_db_module_id,
            pkg_id: item.pkg_id,
            read_only_slaves: item.readonly_host.length
              ? item.readonly_host.map((host, index) => ({
                  new_slave: item.new_readonly_host[index],
                  old_slave: host,
                }))
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
          is_check_process: formData.is_check_process,
          need_checksum: formData.need_checksum,
        },
        ...formData.payload,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
  };
</script>
