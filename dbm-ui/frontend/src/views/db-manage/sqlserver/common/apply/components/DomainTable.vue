<template>
  <div class="sqlserver-domains">
    <!-- row-key 不能用 key：key 是正在编辑的域名，值一变整行就会重建；行数据上没有 index 字段，会回退到 rowIndex -->
    <PrimaryTable
      class="custom-edit-table"
      :columns="columns"
      :data="tableData"
      :empty="t('请选择业务和DB模块名')"
      row-key="index" />
    <!-- <EditTagDialog
      :biz-id="bizId"
      :domain="editingRowIndex !== undefined ? domains[editingRowIndex]?.key || '' : ''"
      :is-show="editingRowIndex !== undefined"
      :tags="editingTags"
      @close="handleCloseTagDialog"
      @confirm="handleTagConfirm" /> -->
  </div>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import type { PrimaryTableCol } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';

  import { useTicketModifyState } from '@hooks';

  import { ClusterTypes } from '@common/const';
  import { clusterNameFormatRegx, clusterNameSymbolRegx } from '@common/regex';

  // import EditTagDialog from '@views/db-manage/common/deploy-cluster-tag/components/EditTagDialog.vue';
  // import TagDisplay from '@views/db-manage/common/deploy-cluster-tag/Index.vue';
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

  const domains = defineModel<Array<{ key: string; tags?: Record<string, string>[] }>>('domains', {
    default: () => [{ key: '' }],
  });

  const { t } = useI18n();
  // 调整申请模式只放开资源申请条件，域名只读
  const isAdjustApply = Boolean(useTicketModifyState()?.isAdjustApply);

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
    const columns: PrimaryTableCol[] = [
      {
        cell: (_, { rowIndex }) => String(rowIndex + 1),
        colKey: 'index',
        title: t('序号'),
        // type: 'index',
        width: 80,
      },
      {
        cell: (_, { rowIndex }) => (
          <div class='domain-address'>
            <span>
              {/* {props.moduleAliasName}db. */}
              {getDomainPreview(domains.value[rowIndex]?.key)['masterDomain']?.prefix}
            </span>
            <bk-form-item
              key={rowIndex}
              class={{
                'domain-address-item': true,
                'domain-address-item-empty': !domains.value[rowIndex]?.key,
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
                disabled={isAdjustApply}
                maxlength={63}
                model-value={domains.value[rowIndex]?.key}
                placeholder={t('请输入')}
                show-word-limit
                style='width:260px'
                onChange={(value: string) => handleChangeDomain(value, rowIndex)}>
                {{
                  suffix: () => domains.value[rowIndex]?.key && <span class='domain-address-placeholder ml-4'></span>,
                }}
              </db-input>
            </bk-form-item>
            <span>
              {/* {`.${props.dbAppAbbr}.db`} */}
              {getDomainPreview(domains.value[rowIndex]?.key)['masterDomain']?.suffix}
            </span>
          </div>
        ),
        colKey: 'mainDomain',
        minWidth: 500,
        title: () => (
          <span>
            {props.isSqlserverSingle ? t('域名') : t('主域名')}
            {tableData.value.length !== 0 && !isAdjustApply && (
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
      },
    ];

    if (!props.isSqlserverSingle) {
      columns.push({
        cell: (_, { rowIndex }) => (
          <div class='domain-address'>
            {/* <span>{props.moduleAliasName}dr.</span>
            <span>{domains.value[rowIndex]?.key}</span>
            <span>{`.${props.dbAppAbbr}.db`}</span> */}
            <span>{getDomainPreview(domains.value[rowIndex]?.key)['masterDomain']?.prefix}</span>
            <span>{domains.value[rowIndex]?.key || t('集群标识')}</span>
            <span>{getDomainPreview(domains.value[rowIndex]?.key)['masterDomain']?.suffix}</span>
          </div>
        ),
        colKey: 'slaveDomain',
        minWidth: 400,
        title: t('从域名'),
      });
    }

    // columns.push({
    //   cell: (_, { rowIndex }) => renderTagCell(rowIndex),
    //   colKey: 'tags',
    //   minWidth: 200,
    //   title: t('集群标签'),
    // });

    return columns;
  });

  /**
   * 批量编辑域名
   */
  const handleBatchEditDomains = (newDomainList: string[]) => {
    // 与单条编辑一致保留原对象上的其它字段（回填单据带后端补的 master / slave），只改 key，否则改单时值没变也算一项差异
    domains.value = newDomainList.map((newDomainItem, index) => ({
      ...domains.value[index],
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

  // // 「集群标签」编辑弹窗：undefined 表示未打开
  // const editingRowIndex = ref<number>();
  // const editingTags = computed(() =>
  //   editingRowIndex.value === undefined ? [] : (domains.value[editingRowIndex.value]?.tags ?? []),
  // );
  //
  // const handleEditTag = (rowIndex: number) => {
  //   editingRowIndex.value = rowIndex;
  // };
  //
  // const handleCloseTagDialog = () => {
  //   editingRowIndex.value = undefined;
  // };
  //
  // /** 弹窗确定：把标签写回当前行，不影响其他行 */
  // const handleTagConfirm = (tags: Record<string, string>[]) => {
  //   if (editingRowIndex.value === undefined) {
  //     return;
  //   }
  //   const newDomains = _.cloneDeep(domains.value);
  //   newDomains[editingRowIndex.value] = { ...newDomains[editingRowIndex.value], tags };
  //   domains.value = newDomains;
  //   editingRowIndex.value = undefined;
  // };
  //
  // /** 渲染「集群标签」列：标签只读展示 + 编辑图标 */
  // const renderTagCell = (rowIndex: number) => (
  //   <div class='cluster-tag-cell'>
  //     <TagDisplay tags={domains.value[rowIndex]?.tags} />
  //     {!isAdjustApply && (
  //       <db-icon
  //         v-bk-tooltips={t('编辑标签')}
  //         class='tag-edit-icon'
  //         type='edit'
  //         onClick={() => handleEditTag(rowIndex)}
  //       />
  //     )}
  //   </div>
  // );

  const getDomainPreview = (clusterName: string) => {
    const strategy = getDomainStrategy(
      props.isSqlserverSingle ? ClusterTypes.SQLSERVER_SINGLE : ClusterTypes.SQLSERVER_HA,
    );

    return strategy({
      clusterName,
      clusterType: props.isSqlserverSingle ? ClusterTypes.SQLSERVER_SINGLE : ClusterTypes.SQLSERVER_HA,
      dbAppAbbr: props.dbAppAbbr,
      moduleName: props.moduleAliasName,
    });
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

    // .cluster-tag-cell {
    //   display: flex;
    //   align-items: flex-start;
    //
    //   .tag-edit-icon {
    //     margin-left: 8px;
    //     font-size: 14px;
    //     line-height: 20px;
    //     color: #3a84ff;
    //     cursor: pointer;
    //     flex-shrink: 0;
    //   }
    // }
  }
</style>
