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
  import { merge } from 'lodash';
  import { useI18n } from 'vue-i18n';

  import type { HostDetails } from '@services/types';

  import { nameRegx } from '@common/regex';

  import BatchEdit from './BatchEdit.vue';

  interface IFormdata {
    bk_biz_id: '' | number,
    remark: string,
    ticket_type: string,
    details: {
      bk_cloud_id:number,
      city_code: string,
      db_app_abbr: string,
      spec: string,
      db_module_id: null | number,
      cluster_count: number,
      inst_num: number,
      start_sqlserver_port: number,
      domains: Array<{ key:string }>,
      ip_source: string,
      nodes: {
        backend: HostDetails[],
      },
      resource_spec:{
        count: number,
        spec_id: string,
        location_spec: {
          city: string,
          sub_zone_ids:any [],
        },
      }
    },
  }

  interface Props {
    moduleName: string,
    formdata: IFormdata,
    isSqlserverSingle:boolean,
  }

  const props = defineProps<Props>();

  const domains = defineModel<{ key: string }[]>('domains', {
    default: [{ key: '' }],
  });

  const { t } = useI18n();

  /**
   * 表单展示数据
   * 没有 moduleName 和 appName 则不展示 table 数据
   */
  const tableData = computed(() => {
    const { moduleName, formdata } = props;
    if (moduleName && (formdata.details.db_app_abbr)) {
      return formdata.details.domains;
    }
    return [];
  });

  const domainKeys = computed(() => tableData.value.map(item => item.key));

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
      validator: (val: string) => domainKeys.value.filter(item => item === val).length < 2,
    },
  ];

  // 设置域名 form-item refs
  const domainRefs: any[] = [];

  const setDomainRef = (el: any) => {
    if (el) {
      domainRefs.push(el);
    }
  };

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
            tableData.value.length === 0
              ? null
              : <BatchEdit
                  v-bk-tooltips={ t('快捷编辑_可通过换行分隔_快速编辑多个域名') }
                  moduleName={ props.moduleName }
                  appName={ props.formdata.details.db_app_abbr }
                  onChange={ handleBatchEditDomains } />
          }
        </span>
      ),
        field: 'mainDomain',
        minWidth: 500,
        render: ({ index }: { index: number }) => renderDomain(index, true),
      }];
    if (!props.isSqlserverSingle) {
      columns.push({
        label: t('从域名'),
        field: 'slaveDomain',
        render: ({ index }: { index: number }) => renderDomain(index),
      });
    }
    return columns;
  });

  watch(() => props.formdata.details.cluster_count, () => {
    if (domainRefs.length > 1) {
      domainRefs.splice(0, domainRefs.length - 1);
    }
  });

  /**
   * 批量编辑域名
   */
  const handleBatchEditDomains = (realm: string[]) => {
    if (realm.length !== 0) {
      const results = [...props.formdata.details.domains];
      results.forEach((item, index) => {
        if (realm[index]) {
          results[index].key = realm[index];
        }
      });
      merge(domains, results);
      // 校验域名信息
      nextTick(() => {
        domainRefs.forEach((item) => {
          item?.validate?.();
        });
      });
    }
  };

  /**
   * 编辑域名
   */
  const  handleChangeDomain = (value: string) => {
    domains.value = [{ key: value }];
  };

  /**
   * 渲染域名编辑
   */
  const  renderDomain = (rowIndex: number, isMain = false) => (
      <div class="domain-address">
        <span>{ props.moduleName }{ isMain ? 'db.' : 'dr.' }</span>
        {
          isMain
            ? (
              <bk-form-item
                ref={ setDomainRef }
                class="domain-address__item"
                errorDisplayType="tooltips"
                property={ `details.domains.${rowIndex}.key` }
                key={ rowIndex }
                rules={ domainRule }
                label-width={ 0 }>
                <bk-input
                  style="width:260px"
                  model-value={ props.formdata.details.domains[rowIndex]?.key }
                  placeholder={ t('请输入') }
                  v-bk-tooltips={{
                    trigger: 'click',
                    placement: 'top',
                    theme: 'light',
                    content: t('以小写英文字母开头_且只能包含英文字母_数字_连字符'),
                  }}
                  onInput={ (value: string) => handleChangeDomain(value) }
                />
              </bk-form-item>
            )
            : <span class="domain-address__placeholder">{ props.formdata.details.domains[rowIndex]?.key }</span>
      }
      <span>{ `.${props.formdata.details.db_app_abbr}.db` }</span>
      </div>
  );
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
