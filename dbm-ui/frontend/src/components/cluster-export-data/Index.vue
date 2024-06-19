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
  <DbSideslider
    v-model:is-show="isShow"
    class="export-data"
    width="960">
    <template #header>
      <span>{{ t('导出数据') }}</span>
      <div class="cluster-domain">{{ formData.domain }}</div>
    </template>
    <div class="cluster-export-data">
      <DbForm
        ref="formRef"
        form-type="vertical"
        :model="formData"
        :rules="rules">
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
          <BkTagInput
            v-model="formData.databases"
            allow-auto-match
            allow-create
            :clearable="false"
            collapse-tags
            has-delete-icon
            :max-data="5" />
        </BkFormItem>
        <BkFormItem
          :label="t('目标表名')"
          property="tables"
          required>
          <BkInput
            v-model="formData.tables"
            :placeholder="t('请输入目标表，如： table_chart%，tab2%，多个英文逗号或换行分割')"
            :rows="4"
            type="textarea" />
        </BkFormItem>
        <BkFormItem
          :label="t('忽略表名')"
          property="tablesIgnore">
          <BkInput
            v-model="formData.tablesIgnore"
            :placeholder="t('请输入目标表，如： table_chart%，tab2%，多个英文逗号或换行分割')"
            :rows="4"
            type="textarea" />
        </BkFormItem>
        <BkFormItem
          :label="t('where 条件')"
          property="where">
          <BkInput
            v-model="formData.where"
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
  </DbSideslider>
</template>

<script setup lang="tsx" generic="T extends TendbsingleModel | TendbhaModel | TendbClusterModel">
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import TendbsingleModel from '@services/model/mysql/tendbsingle';
  import TendbClusterModel from '@services/model/spider/tendbCluster';
  import { createTicket } from '@services/source/ticket';

  import { useTicketMessage } from '@hooks';

  import { TicketTypes } from '@common/const';

  import DbForm from '@components/db-form/index.vue';

  interface Props {
    data: T;
  }

  interface Expose {
    submit(): Promise<any>;
  }

  const props = defineProps<Props>();
  const isShow = defineModel<boolean>('isShow', {
    required: true,
    default: false,
  });

  const initFormData = () => ({
    domain: '',
    databases: [],
    tables: '',
    tablesIgnore: '',
    where: '',
    exportType: 'DATA_TABLE',
    remark: '',
  });

  const { t } = useI18n();
  const ticketMessage = useTicketMessage();

  const formRef = ref<InstanceType<typeof DbForm>>();

  const formData = reactive(initFormData());

  const splitString = (value: string) => value.split(/[\s,]+/);

  const genarateTableRules = () => [
    {
      validator: (value: string) => {
        const hasAllMatch = splitString(value).some((item) => /[%*?]/.test(item));
        return !(value.length > 1 && hasAllMatch);
      },
      message: t('包含通配符 * % ? 时，只允许单一对象'),
    },
    {
      validator: (value: string) => {
        if (value) {
          return splitString(value).some((item) => !/^\*$/.test(item));
        }
        return true;
      },
      message: t('* 只允许单独使用'),
      trigger: 'change',
    },
    {
      validator: (value: string) => {
        if (value) {
          return splitString(value).every((item) => !/^%$/.test(item));
        }
        return true;
      },
      message: t('% 不允许单独使用'),
      trigger: 'change',
    },
  ];

  const rules = {
    tables: genarateTableRules(),
    tablesIgnore: genarateTableRules(),
  };

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

  watch(
    () => props.data,
    () => {
      formData.domain = props.data.master_domain;
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
          databases: formData.databases.filter((item) => item !== ''),
          tables: splitString(formData.tables).filter((item) => item !== ''),
          tables_ignore: splitString(formData.tablesIgnore).filter((item) => item !== ''),
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

        createTicket({
          ignore_duplication: true,
          ticket_type: TicketTypes.MYSQL_DUMP_DATA,
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

<style lang="less">
  .export-data {
    .cluster-domain {
      padding-left: 8px;
      margin-left: 8px;
      color: #979ba5;
      font-size: 14px;
      border-left: 1px solid #dcdee5;
    }
  }
</style>
<style lang="less" scoped>
  .cluster-export-data {
    padding: 18px 40px 32px;
    .target-dbs {
      .required-mark {
        color: #ea3636;
        margin: 0 4px;
      }
      .label-text {
        color: #979ba5;
      }
      :deep(.bk-form-label:after) {
        display: none;
      }
    }
  }
</style>
