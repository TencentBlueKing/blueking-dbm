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
    <PrimaryTable
      class="custom-edit-table"
      :columns="columns"
      :data="tableData"
      :empty="t('请选择业务和DB模块名')"
      row-key="key" />
  </div>
</template>

<script setup lang="tsx">
  import type { PrimaryTableCol } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';

  import { checkDomainRepeat } from '@services/source/ticket.tsx';
  import type { HostInfo } from '@services/types';

  import { ClusterTypes, TicketTypes } from '@common/const';
  import { clusterNameFormatRegx, clusterNameSymbolRegx } from '@common/regex.ts';

  import { getDomainStrategy } from '@views/db-manage/utils/getDomainPreview.ts';

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
      message: '',
      required: true,
      trigger: 'blur',
      validator: (val: string) => !!val,
    },
    // {
    //   message: t('最大长度为m', { m: 63 }),
    //   trigger: 'blur',
    //   validator: (val: string) => val.length <= 63,
    // },
    {
      message: t('不能以连字符开头或结尾'),
      trigger: 'blur',
      validator: (val: string) => clusterNameFormatRegx.test(val),
    },
    {
      message: t('格式不正确，请勿使用中文、大写、空格、下划线或特殊符号'),
      trigger: 'blur',
      validator: (val: string) => clusterNameSymbolRegx.test(val),
    },
    {
      message: t('主访问入口重复'),
      trigger: 'blur',
      validator: (val: string) => domainKeys.value.filter((item) => item === val).length < 2,
    },
    {
      message: t('该域名已被占用，请修改集群标识'),
      trigger: 'blur',
      validator: (val: string) => {
        const { bk_biz_id: bizId, details } = props.formdata;
        const { db_app_abbr: dbAppAbbr, db_module_id: dbModuleId } = details;
        if (!bizId || !dbModuleId) {
          return true;
        }
        return checkDomainRepeat({
          cluster_type: isMysqlSingle.value ? ClusterTypes.TENDBSINGLE : ClusterTypes.TENDBHA,
          db_app_abbr: dbAppAbbr || `biz-${bizId}`,
          db_module_id: dbModuleId,
          domains: [val],
        }).then((result) => {
          return !result[0].validate;
        });
      },
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
    const columns: PrimaryTableCol[] = [
      {
        cell: (_, { rowIndex }) => String(rowIndex + 1),
        colKey: 'index',
        title: t('序号'),
        // type: 'index',
        width: 80,
      },
      {
        cell: (_, { rowIndex }) => renderDomain(rowIndex, true),
        colKey: 'mainDomain',
        minWidth: 500,
        title: () => (
          <span>
            {t('主访问入口')}
            {tableData.value.length === 0 ? null : (
              <BatchEdit
                appName={props.formdata.details.db_app_abbr}
                moduleAliasName={props.moduleAliasName}
                onChange={handleBatchEditDomains}
              />
            )}
          </span>
        ),
      },
    ];
    if (!isMysqlSingle.value) {
      columns.push({
        cell: (_, { rowIndex }) => renderDomain(rowIndex),
        colKey: 'slaveDomain',
        minWidth: 400,
        title: t('从访问入口'),
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
          {/* {props.moduleAliasName}
          {isMain ? 'db.' : 'dr.'} */}
          {
            getDomainPreview(props.formdata.details.domains[rowIndex]?.key)[isMain ? 'masterDomain' : 'slaveDomain']
              ?.prefix
          }
        </span>
        {isMain ? (
          <bk-form-item
            key={rowIndex}
            ref={setDomainRef}
            class={{
              'domain-address-item': true,
              'domain-address-item-empty': !props.formdata.details.domains[rowIndex]?.key,
            }}
            errorDisplayType='tooltips'
            label-width={0}
            property={`details.domains.${rowIndex}.key`}
            rules={domainRule}>
            <db-input
              v-bk-tooltips={{
                content: t('仅支持小写字母、数字、连字符，同时会参与集群域名生成，创建后不可改'),
                placement: 'top',
                theme: 'light',
                trigger: 'click',
              }}
              maxlength={63}
              model-value={props.formdata.details.domains[rowIndex]?.key}
              placeholder={t('请输入')}
              show-word-limit
              style='width:260px'
              onInput={(value: string) => handleChangeDomain(value, rowIndex)}>
              {{
                suffix: () =>
                  props.formdata.details.domains[rowIndex]?.key && (
                    <span class='domain-address-placeholder ml-4'></span>
                  ),
              }}
            </db-input>
          </bk-form-item>
        ) : (
          <span class='domain-address-placeholder'>
            {props.formdata.details.domains[rowIndex]?.key || '{' + t('集群标识') + '}'}
          </span>
        )}
        <span>
          {/* {`.${props.formdata.details.db_app_abbr}.db`} */}
          {
            getDomainPreview(props.formdata.details.domains[rowIndex]?.key)[isMain ? 'masterDomain' : 'slaveDomain']
              ?.suffix
          }
        </span>
      </div>
    );
  }

  const getDomainPreview = (clusterName: string) => {
    const strategy = getDomainStrategy(isMysqlSingle.value ? ClusterTypes.TENDBSINGLE : ClusterTypes.TENDBHA);

    return strategy({
      clusterName,
      clusterType: isMysqlSingle.value ? ClusterTypes.TENDBSINGLE : ClusterTypes.TENDBHA,
      dbAppAbbr: props.formdata.details.db_app_abbr,
      moduleName: props.moduleAliasName,
    });
  };
</script>

<style lang="less">
  .mysql-domains {
    .custom-edit-table {
      .bk-form-content {
        margin-left: 0 !important;
      }
    }

    .domain-address {
      display: flex;
      align-items: center;

      > span {
        flex-shrink: 0;
      }

      .domain-address-item {
        margin-bottom: 0;

        .bk-form-label {
          display: none;
        }

        .domain-address-placeholder {
          display: none;
        }

        &.is-error {
          .domain-address-placeholder {
            display: inline;
          }
        }
      }

      .domain-address-item-empty {
        .bk-form-error-tips {
          display: none;
        }
      }

      .domain-address-placeholder {
        min-width: 12px;
      }
    }
  }
</style>
