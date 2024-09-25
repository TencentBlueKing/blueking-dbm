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
  <div class="cluster-export-data-content">
    <DbForm
      ref="formRef"
      form-type="vertical"
      :model="formData">
      <BkFormItem
        :label="t('目标集群')"
        property="domain"
        required>
        <BkInput
          v-model="formData.domain"
          disabled />
      </BkFormItem>
      <BkFormItem
        class="target-dbs"
        :label="t('目标 DB 名')"
        property="databases"
        required>
        <template #label>
          <span>{{ t('目标 DB 名') }}</span>
          <span class="required-mark">*</span>
          <span class="label-text">({{ t('最多支持 5 个') }})</span>
        </template>
        <BkLoading :loading="isLoading">
          <BkSelect
            v-model="formData.databases"
            class="bk-select"
            filterable
            multiple
            multiple-mode="tag">
            <BkOption
              v-for="(item, index) in databaseSelectList"
              :id="item.value"
              :key="index"
              :disabled="item.disabled"
              :name="item.label" />
          </BkSelect>
        </BkLoading>
      </BkFormItem>
      <TableNameFromItem
        v-model="formData.tables"
        :label="t('目标表名')"
        property="tables"
        required />
      <TableNameFromItem
        v-model="formData.tablesIgnore"
        :label="t('忽略表名')"
        property="tablesIgnore" />
      <BkFormItem :label="t('where 条件')">
        <BkInput
          v-model="formData.where"
          :placeholder="t('请输入 where 条件，如：userId > 10000，不要带where关键字')"
          :rows="4"
          type="textarea" />
      </BkFormItem>
      <BkFormItem
        :label="t('导出类型')"
        property="exportType"
        required>
        <BkRadioGroup v-model="formData.exportType">
          <template
            v-for="item in exportTypeList"
            :key="item.value">
            <BkRadio :label="item.value">
              {{ item.label }}
            </BkRadio>
          </template>
        </BkRadioGroup>
      </BkFormItem>
      <BkFormItem
        :label="t('导出原因')"
        property="remark"
        required>
        <BkInput
          v-model="formData.remark"
          :rows="4"
          type="textarea" />
      </BkFormItem>
    </DbForm>
  </div>
</template>

<script setup lang="tsx" generic="T extends TendbsingleModel | TendbhaModel | TendbClusterModel">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import TendbsingleModel from '@services/model/mysql/tendbsingle';
  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import { getClusterDatabaseNameList } from '@services/source/remoteService';
  import { createTicket } from '@services/source/ticket';

  import { useTicketMessage } from '@hooks';

  import { TicketTypes } from '@common/const';

  import DbForm from '@components/db-form/index.vue';

  import TableNameFromItem from './TableNameFromItem.vue';

  interface Props {
    data: T;
    ticketType: TicketTypes.MYSQL_DUMP_DATA | TicketTypes.TENDBCLUSTER_DUMP_DATA;
  }

  interface Expose {
    submit(): Promise<any>;
  }

  const props = defineProps<Props>();

  const initFormData = () => ({
    domain: '',
    databases: [],
    tables: [],
    tablesIgnore: [],
    where: '',
    exportType: 'DATA_TABLE',
    remark: '',
  });

  const { t } = useI18n();
  const ticketMessage = useTicketMessage();

  const formRef = ref<InstanceType<typeof DbForm>>();

  const formData = reactive(initFormData());

  const exportTypeList = [
    {
      label: t('数据和表结构'),
      value: 'DATA_TABLE',
    },
    {
      label: t('数据'),
      value: 'DATA',
    },
    {
      label: t('表结构'),
      value: 'TABLE',
    },
  ];

  const databaseSelectList = computed(() => {
    const databaseList = clusterDatabaseNameList.value;
    const { length } = formData.databases;
    if (databaseList && databaseList.length > 0) {
      const [{ databases }] = databaseList;
      return databases.map((item) => ({
        value: item,
        label: item,
        disabled: length >= 5,
      }));
    }
    return [];
  });

  const {
    data: clusterDatabaseNameList,
    loading: isLoading,
    run: getClusterDatabaseNameListRun,
  } = useRequest(getClusterDatabaseNameList, {
    manual: true,
  });

  watch(
    () => props.data,
    () => {
      formData.domain = props.data.master_domain;
      getClusterDatabaseNameListRun({ cluster_ids: [props.data.id] });
    },
    {
      immediate: true,
    },
  );

  defineExpose<Expose>({
    submit() {
      return formRef.value!.validate().then(() => {
        const details = {
          cluster_id: props.data.id,
          // charset: 'utf8',
          charset: 'default',
          databases: formData.databases,
          tables: formData.tables,
          tables_ignore: formData.tablesIgnore,
          where: formData.where,
        };

        if (formData.exportType === 'DATA_TABLE') {
          Object.assign(details, {
            dump_data: true,
            dump_schema: true,
          });
        } else if (formData.exportType === 'DATA') {
          Object.assign(details, {
            dump_data: true,
            dump_schema: false,
          });
        } else {
          Object.assign(details, {
            dump_data: false,
            dump_schema: true,
          });
        }

        return createTicket({
          ignore_duplication: true,
          ticket_type: props.ticketType,
          bk_biz_id: props.data.bk_biz_id,
          remark: formData.remark,
          details,
        }).then((res) => {
          ticketMessage(res.id);
          Object.assign(formData, {
            ...initFormData(),
            domain: props.data.master_domain,
          });
        });
      });
    },
  });
</script>

<style lang="less" scoped>
  .cluster-export-data-content {
    padding: 18px 40px 32px;

    :deep(.bk-form-label) {
      font-size: 12px;
    }

    .target-dbs {
      .required-mark {
        margin: 0 4px;
        color: #ea3636;
      }

      .label-text {
        color: #979ba5;
      }

      :deep(.bk-form-label::after) {
        display: none;
      }
    }
  }
</style>
