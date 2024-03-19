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

  import { nameRegx } from '@common/regex';

  import BatchEdit from './BatchEdit.vue';

  interface Props {
    moduleName: string,
    dbAppAbbr: string,
    isSqlserverSingle: boolean,
  }

  const props = defineProps<Props>();

  const domains = defineModel<{ key: string }[]>('domains', {
    default: () => [{ key: '' }],
  });

  const { t } = useI18n();

  /**
   * 表单展示数据
   * 没有 moduleName 和 appName 则不展示 table 数据
   */
  const tableData = computed(() => {
    const {
      moduleName,
      dbAppAbbr,
    } = props;
    if (moduleName && dbAppAbbr) {
      return domains.value;
    }
    return [];
  });

  const domainKeyList = computed(() => tableData.value.map(item => item.key));

  const domainRule = [
    {
      required: true,
      message: t('必填项'),
      trigger: 'change',
    },
    {
      message: t('最大长度为m', { m: 63 }),
      trigger: 'blur',
      validator: (val: string) => val.length <= 63,
    },
    {
      message: t('以小写英文字母开头_且只能包含英文字母_数字_连字符'),
      trigger: 'blur',
      validator: (val: string) => nameRegx.test(val),
    },
    {
      message: t('主访问入口重复'),
      trigger: 'blur',
      validator: (val: string) => domainKeyList.value.filter(item => item === val).length < 2,
    },
  ];

  const columns = computed(() => {
    const columns: Column[] = [
      {
        type: 'index',
        label: t('序号'),
        width: 60,
      },
      {
        label: () => (
          <span>
            {
              props.isSqlserverSingle ? t('域名') : t('主域名')
            }
            {
              tableData.value.length !== 0 && (
                <span v-bk-tooltips={t('快捷编辑_可通过换行分隔_快速编辑多个域名')}>
                  <BatchEdit
                    moduleName={props.moduleName}
                    appName={props.dbAppAbbr}
                    onChange={handleBatchEditDomains} />
                </span>
              )
            }
          </span>
        ),
        field: 'mainDomain',
        minWidth: 500,
        render: ({ index }: { index: number }) => (
          <div class="domain-address">
            <span>
              {props.moduleName}db.
            </span>
            <bk-form-item
              errorDisplayType="tooltips"
              property={`details.domains.${index}.key`}
              key={index }
              rules={domainRule}
              label-width={0}>
                <bk-input
                  style="width:260px"
                  model-value={domains.value[index]?.key}
                  placeholder={t('请输入')}
                  v-bk-tooltips={{
                    trigger: 'click',
                    placement: 'top',
                    theme: 'light',
                    content: t('以小写英文字母开头_且只能包含英文字母_数字_连字符'),
                  }}
                  onChange={(value: string) => handleChangeDomain(value, index)}
                />
            </bk-form-item>
            <span>
              {`.${props.dbAppAbbr}.db`}
            </span>
          </div>
        ),
      }];

    if (!props.isSqlserverSingle) {
      columns.push({
        label: t('从域名'),
        field: 'slaveDomain',
        render: ({ index }: { index: number }) => (
          <div class="domain-address">
            <span>
              {props.moduleName}dr.
            </span>
            <span >
              {domains.value[index]?.key}
            </span>
            <span>
              {`.${props.dbAppAbbr}.db`}
            </span>
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
    domains.value = newDomainList.map(newDomainItem => ({
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
</script>

<style lang="less" scoped>
  .sqlserver-domains {
    :deep(.bk-table) {
      .bk-form-content {
        margin-left: 0 !important;
      }
    }
  }
</style>
