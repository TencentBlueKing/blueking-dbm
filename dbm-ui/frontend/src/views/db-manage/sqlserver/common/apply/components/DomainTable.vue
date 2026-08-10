<template>
  <div class="sqlserver-domains">
    <DbOriginalTable
      class="custom-edit-table"
      :columns="columns"
      :data="tableData"
      :empty-text="t('请选择业务和DB模块名')" />
  </div>
</template>

<script setup lang="tsx">
  import type { Column } from 'bkui-vue/lib/table/props';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { ClusterTypes } from '@common/const';
  import { clusterNameFormatRegx, clusterNameSymbolRegx } from '@common/regex';

  import { getDomainStrategy } from '@views/db-manage/utils/getDomainPreview.ts';

  import { checkDomainRepeat } from '@/services/source/ticket.tsx';

  import BatchEdit from './BatchEdit.vue';

  interface Props {
    bizId: number | '';
    dbAppAbbr: string;
    isSqlserverSingle: boolean;
    moduleAliasName: string;
    moduleId: number | null;
  }

  const props = defineProps<Props>();

  const domains = defineModel<{ key: string }[]>('domains', {
    default: () => [{ key: '' }],
  });

  const { t } = useI18n();

  /**
   * 表单展示数据
   * 没有 moduleAliasName 和 appName 则不展示 table 数据
   */
  const tableData = computed(() => {
    const { dbAppAbbr, moduleAliasName } = props;
    if (moduleAliasName && dbAppAbbr) {
      return domains.value;
    }
    return [];
  });

  const domainKeyList = computed(() => tableData.value.map((item) => item.key));

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
      validator: (val: string) => domainKeyList.value.filter((item) => item === val).length < 2,
    },
    {
      message: t('该域名已被占用，请修改集群标识'),
      trigger: 'blur',
      validator: (val: string) => {
        if (!props.bizId || !props.moduleId) {
          return true;
        }
        return checkDomainRepeat({
          cluster_type: props.isSqlserverSingle ? ClusterTypes.SQLSERVER_SINGLE : ClusterTypes.SQLSERVER_HA,
          db_app_abbr: props.dbAppAbbr || `biz-${props.bizId}`,
          db_module_id: props.moduleId,
          domains: [val],
        }).then((result) => {
          return !result[0].validate;
        });
      },
    },
  ];

  const columns = computed(() => {
    const columns: Column[] = [
      {
        label: t('序号'),
        render: ({ index }: { index: number }) => index + 1,
        // type: 'index',
        width: 80,
      },
      {
        field: 'mainDomain',
        label: () => (
          <span>
            {props.isSqlserverSingle ? t('域名') : t('主域名')}
            {tableData.value.length !== 0 && (
              <span v-bk-tooltips={t('快捷编辑_可通过换行分隔_快速编辑多个域名')}>
                <BatchEdit
                  appName={props.dbAppAbbr}
                  moduleAliasName={props.moduleAliasName}
                  onChange={handleBatchEditDomains}
                />
              </span>
            )}
          </span>
        ),
        minWidth: 500,
        render: ({ index }: { index: number }) => (
          <div class='domain-address'>
            <span>
              {/* {props.moduleAliasName}db. */}
              {getDomainPreview(domains.value[index]?.key)['masterDomain']?.prefix}
            </span>
            <bk-form-item
              key={index}
              class={{
                'domain-address-item': true,
                'domain-address-item-empty': !domains.value[index]?.key,
              }}
              errorDisplayType='tooltips'
              label-width={0}
              property={`details.domains.${index}.key`}
              rules={domainRule}>
              <db-input
                v-bk-tooltips={{
                  content: t('仅支持小写字母、数字、连字符，同时会参与集群域名生成，创建后不可改'),
                  placement: 'top',
                  theme: 'light',
                  trigger: 'click',
                }}
                maxlength={63}
                model-value={domains.value[index]?.key}
                placeholder={t('请输入')}
                show-word-limit
                style='width:260px'
                onChange={(value: string) => handleChangeDomain(value, index)}>
                {{
                  suffix: () => domains.value[index]?.key && <span class='domain-address-placeholder ml-4'></span>,
                }}
              </db-input>
            </bk-form-item>
            <span>
              {/* {`.${props.dbAppAbbr}.db`} */}
              {getDomainPreview(domains.value[index]?.key)['masterDomain']?.suffix}
            </span>
          </div>
        ),
      },
    ];

    if (!props.isSqlserverSingle) {
      columns.push({
        field: 'slaveDomain',
        label: t('从域名'),
        minWidth: 400,
        render: ({ index }: { index: number }) => (
          <div class='domain-address'>
            {/* <span>{props.moduleAliasName}dr.</span>
            <span>{domains.value[index]?.key}</span>
            <span>{`.${props.dbAppAbbr}.db`}</span> */}
            <span>{getDomainPreview(domains.value[index]?.key)['masterDomain']?.prefix}</span>
            <span>{domains.value[index]?.key || t('集群标识')}</span>
            <span>{getDomainPreview(domains.value[index]?.key)['masterDomain']?.suffix}</span>
          </div>
        ),
      });
    }

    return columns;
  });

  /**
   * 批量编辑域名
   */
  const handleBatchEditDomains = (newDomainList: string[]) => {
    domains.value = newDomainList.map((newDomainItem) => ({
      key: newDomainItem,
    }));
  };

  /**
   * 编辑域名
   */
  const handleChangeDomain = (value: string, index: number) => {
    const newDomains = _.cloneDeep(domains.value);
    newDomains[index].key = value;
    domains.value = newDomains;
  };

  const getDomainPreview = (clusterName: string) => {
    const strategy = getDomainStrategy(
      props.isSqlserverSingle ? ClusterTypes.SQLSERVER_SINGLE : ClusterTypes.SQLSERVER_HA,
    );

    return strategy(
      {
        clusterName,
        dbAppAbbr: props.dbAppAbbr,
        moduleName: props.moduleAliasName,
      },
      {
        bizId: props.bizId,
      },
    );
  };
</script>

<style lang="less">
  .sqlserver-domains {
    .custom-edit-table {
      .bk-form-content {
        margin-left: 0 !important;
      }

      .domain-address-item {
        margin-bottom: 0;

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
