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
  <div class="mysql-domains">
    <DbOriginalTable
      class="custom-edit-table"
      :columns="columns"
      :data="tableData"
      :empty-text="$t('请选择业务和DB模块名')" />
  </div>
</template>

<script setup lang="tsx">
  import type { Column } from 'bkui-vue/lib/table/props';
  import { useI18n } from 'vue-i18n';

  import type { HostInfo } from '@services/types';

  import { TicketTypes } from '@common/const';

  import BatchEdit from './BatchEdit.vue';

  interface IFormdata {
    bk_biz_id: '' | number;
    details: {
      charset: string;
      city_code: string;
      cluster_count: number;
      db_app_abbr: string;
      db_module_id: null | number;
      disaster_tolerance_level: string;
      domains: Array<Domain>;
      inst_num: number;
      ip_source: string;
      nodes: {
        backend: HostInfo[];
        proxy: HostInfo[];
      };
      spec: string;
      start_mysql_port: number;
      start_proxy_port: number;
    };
    remark: string;
    ticket_type: string;
  }
  interface Domain {
    key: string;
  }
  interface Props {
    formdata: IFormdata;
    moduleAliasName: string;
    ticketType: string;
  }
  type Emits = (e: 'update:domains', value: Array<Domain>) => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const isMysqlSingle = computed(() => props.ticketType === TicketTypes.MYSQL_SINGLE_APPLY);
  /**
   * 表单展示数据
   * 没有 moduleAliasName 和 appName 则不展示 table 数据
   */
  const tableData = computed(() => {
    const { formdata, moduleAliasName } = props;
    if (moduleAliasName && formdata.details.db_app_abbr) {
      return formdata.details.domains;
    }
    return [];
  });
  const domainKeys = computed(() => tableData.value.map((item) => item.key));
  const domainRule = [
    {
      message: t('必填项'),
      required: true,
      trigger: 'change',
    },
    {
      message: t('最大长度为m', { m: 63 }),
      trigger: 'blur',
      validator: (val: string) => val.length <= 63,
    },
    {
      message: t('以小写英文字母或数字开头_且只能包含英文字母_数字_连字符'),
      trigger: 'blur',
      validator: (val: string) => /^[a-z0-9][a-z0-9-]*$/.test(val),
    },
    {
      message: t('主访问入口重复'),
      trigger: 'blur',
      validator: (val: string) => domainKeys.value.filter((item) => item === val).length < 2,
    },
  ];
  // 设置域名 form-item refs
  const domainRefs: any[] = [];
  const setDomainRef = (el: any) => {
    if (el) {
      domainRefs.push(el);
    }
  };
  watch(
    () => props.formdata.details.cluster_count,
    () => {
      domainRefs.splice(0, domainRefs.length - 1);
    },
  );
  const columns = computed(() => {
    const columns: Column[] = [
      {
        label: t('序号'),
        type: 'index',
        width: 60,
      },
      {
        field: 'mainDomain',
        label: () => (
          <span>
            {t('主访问入口')}
            {tableData.value.length === 0 ? null : (
              <BatchEdit
                v-bk-tooltips={t('快捷编辑_可通过换行分隔_快速编辑多个域名')}
                appName={props.formdata.details.db_app_abbr}
                moduleAliasName={props.moduleAliasName}
                onChange={handleBatchEditDomains}
              />
            )}
          </span>
        ),
        minWidth: 500,
        render: ({ index }: { index: number }) => renderDomain(index, true),
      },
    ];
    if (!isMysqlSingle.value) {
      columns.push({
        field: 'slaveDomain',
        label: t('从访问入口'),
        render: ({ index }: { index: number }) => renderDomain(index),
      });
    }
    return columns;
  });

  /**
   * 批量编辑域名
   */
  function handleBatchEditDomains(domains: string[]) {
    if (domains.length !== 0) {
      const results = [...props.formdata.details.domains];
      results.forEach((item, index) => {
        if (domains[index] !== undefined) {
          results[index].key = domains[index];
        }
      });
      emits('update:domains', results);
      // 校验域名信息
      nextTick(() => {
        domainRefs.forEach((item) => {
          item?.validate?.();
        });
      });
    }
  }

  /**
   * 编辑域名
   */
  function handleChangeDomain(value: string, index: number) {
    const domains = [...props.formdata.details.domains];
    domains[index].key = value;
    emits('update:domains', domains);
  }

  /**
   * 渲染域名编辑
   */
  function renderDomain(rowIndex: number, isMain = false) {
    return (
      <div class='domain-address'>
        <span>
          {props.moduleAliasName}
          {isMain ? 'db.' : 'dr.'}
        </span>
        {isMain ? (
          <bk-form-item
            key={rowIndex}
            ref={setDomainRef}
            class='domain-address__item'
            errorDisplayType='tooltips'
            label-width={0}
            property={`details.domains.${rowIndex}.key`}
            rules={domainRule}>
            <bk-input
              v-bk-tooltips={{
                content: t('以小写英文字母或数字开头_且只能包含英文字母_数字_连字符'),
                placement: 'top',
                theme: 'light',
                trigger: 'click',
              }}
              model-value={props.formdata.details.domains[rowIndex]?.key}
              placeholder={t('请输入')}
              style='width:260px'
              onInput={(value: string) => handleChangeDomain(value, rowIndex)}
            />
          </bk-form-item>
        ) : (
          <span class='domain-address__placeholder'>{props.formdata.details.domains[rowIndex]?.key}</span>
        )}
        <span>{`.${props.formdata.details.db_app_abbr}.db`}</span>
      </div>
    );
  }
</script>

<style lang="less" scoped>
  .mysql-domains {
    :deep(.bk-table) {
      .bk-form-content {
        margin-left: 0 !important;
      }
    }
  }
</style>
