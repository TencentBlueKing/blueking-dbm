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
  <UpgradeWrapper
    v-model="wrapperController"
    @change="handleReset">
    <SmartAction class="db-toolbox">
      <EditableTable
        :key="tableKey"
        ref="table"
        class="mb-20"
        :model="formData.tableData"
        :rules="rules">
        <EditableRow
          v-for="(item, index) in formData.tableData"
          :key="index">
          <WithRelatedClustersColumn
            v-model="item.cluster"
            :cluster-types="
              wrapperController.roleType === 'singleStorageLayer' ? [ClusterTypes.TENDBSINGLE] : [ClusterTypes.TENDBHA]
            "
            :selected="selected"
            @batch-edit="handleBatchEdit" />
          <CurrentVersionColumn
            v-model="item.current_version"
            :cluster="item.cluster" />
          <TargetVersionColumn
            v-if="isMajorVersion"
            v-model="item.target_version"
            v-model:new-db-module-id="item.new_db_module_id"
            v-model:pkg-id="item.pkg_id"
            :cluster="item.cluster" />
          <FixedModuleTargetVersionColumn
            v-else
            v-model="item.target_version"
            v-model:new-db-module-id="item.new_db_module_id"
            v-model:pkg-id="item.pkg_id"
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

  import { useCreateTicket, useTicketDetail } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import TicketPayload, {
    createTickePayload,
  } from '@views/db-manage/common/toolbox-field/form-item/ticket-payload/Index.vue';
  import WithRelatedClustersColumn from '@views/db-manage/mysql/common/edit-table-column/WithRelatedClustersColumn.vue';
  import UpgradeWrapper from '@views/db-manage/mysql/MYSQL_LOCAL_UPGRADE/components/UpgradeWrapper.vue';

  import { random } from '@utils';

  import CurrentVersionColumn from './components/CurrentVersionColumn.vue';
  import FixedModuleTargetVersionColumn from './components/FixedModuleTargetVersionColumn.vue';
  import TargetVersionColumn from './components/TargetVersionColumn.vue';

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
    pkg_id: number;
    target_version: ComponentProps<typeof TargetVersionColumn>['modelValue'];
  }

  const { t } = useI18n();
  const route = useRoute();
  const tableRef = useTemplateRef('table');

  const createTableRow = (data: DeepPartial<RowData> = {}) => ({
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
    pkg_id: data.pkg_id || 0,
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
    is_check_process: true,
    payload: createTickePayload(),
    tableData: [createTableRow()],
  });

  const wrapperController = ref({
    roleType: (route.query.roleType as string) || 'haStorageLayer',
    updateType: TicketTypes.MYSQL_LOCAL_UPGRADE,
  });
  const formData = reactive(defaultData());
  const tableKey = ref(random());

  /*
    是否跨版本升级、主从存储层迁移、单节点原地

      1.存储层原地升级：模块不可变、仅包文件可变

      2.存储层迁移升级：模块可变、包文件可变

      3.单节点原地升级：模块可变、包文件可变
  */
  const isMajorVersion = computed(
    () =>
      wrapperController.value.roleType === 'singleStorageLayer' ||
      wrapperController.value.updateType === TicketTypes.MYSQL_MIGRATE_UPGRADE,
  );
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

  useTicketDetail<Mysql.LocalUpgrade>(TicketTypes.MYSQL_LOCAL_UPGRADE, {
    onSuccess(ticketDetail) {
      const { clusters, infos } = ticketDetail.details;
      const isSingle = clusters[infos[0].cluster_ids[0]].cluster_type === (ClusterTypes.TENDBSINGLE as string);
      wrapperController.value.roleType = isSingle ? 'singleStorageLayer' : 'haStorageLayer';
      if (infos.length > 0) {
        Object.assign(formData, {
          ...createTickePayload(ticketDetail),
          is_check_process: ticketDetail.details.is_check_process,
          tableData: ticketDetail.details.infos.map((item) =>
            createTableRow({
              cluster: {
                master_domain: clusters[item.cluster_ids[0]].immute_domain,
              },
              new_db_module_id: item.new_db_module_id,
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
    infos: {
      cluster_ids: number[];
      display_info: {
        charset: string;
        cluster_type: string;
        current_module_name: string;
        current_package: string;
        current_version: string;
        target_package: string;
        target_version: string;
      };
      new_db_module_id: number;
      pkg_id: number;
    }[];
    is_check_process: boolean;
  }>(TicketTypes.MYSQL_LOCAL_UPGRADE);

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
          infos: formData.tableData.map((item) => ({
            cluster_ids: [item.cluster.id, ...item.cluster.related_clusters.map((item) => item.id)],
            display_info: {
              charset: item.target_version.charset,
              cluster_type: item.cluster.cluster_type,
              current_module_name: item.cluster.db_module_name,
              current_package: item.current_version.pkg_name,
              current_version: item.current_version.db_version,
              target_package: item.target_version.pkg_name,
              target_version: item.target_version.db_version,
            },
            new_db_module_id: item.new_db_module_id,
            pkg_id: item.pkg_id,
          })),
          is_check_process: formData.is_check_process,
        },
        ...formData.payload,
      });
    }
  };

  const handleReset = () => {
    Object.assign(formData, defaultData());
    tableKey.value = random();
  };
</script>
