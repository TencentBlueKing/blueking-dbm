<template>
  <div style="padding: 20px 16px">
    <BkCollapse
      v-model="activeIndex"
      class="template-detail-collapse"
      header-icon="right-shape">
      <BkCollapsePanel name="clone-rule">
        <span>{{ t('克隆的规则') }}</span>
        <template #content>
          <BkTable
            class="template-detail-table"
            :columns="cloneRuleColumns"
            :data="data.config_rules" />
        </template>
      </BkCollapsePanel>
      <BkCollapsePanel name="permission-rule">
        <span>{{ t('权限规则') }}</span>
        <template #content>
          <BkLoading :loading="permissionTableloading">
            <BkTable
              :cell-class="getCellClass"
              class="template-detail-permission-table"
              :columns="permissionTableColumns"
              :data="permissionTableData" />
          </BkLoading>
        </template>
      </BkCollapsePanel>
    </BkCollapse>
  </div>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import MysqlPermissionAccountModel from '@services/model/mysql/mysql-permission-account';
  import OpenareaTemplateModel from '@services/model/openarea/openareaTemplate';
  import { getPermissionRules } from '@services/source/mysqlPermissionAccount';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  interface Props {
    data: OpenareaTemplateModel;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const permissionTableloading = ref(false);
  const activeIndex = ref(['clone-rule', 'permission-rule']);
  const rowFlodMap = ref<Record<string, boolean>>({});
  const permissionTableData = ref<MysqlPermissionAccountModel[]>([]);

  const permissionTableColumns = computed(() => [
    {
      field: 'user',
      label: t('账号名称'),
      render: ({ data }: { data: MysqlPermissionAccountModel }) => (
        <div class='account-box'>
          {data.rules.length > 1 && (
            <db-icon
              class={{
                'flod-flag': true,
                'is-flod': rowFlodMap.value[data.account.user],
              }}
              type='down-shape'
              onClick={() => handleToogleExpand(data.account.user)}
            />
          )}
          {data.account.user}
        </div>
      ),
      showOverflowTooltip: false,
      width: 220,
    },
    {
      field: 'access_db',
      label: t('访问DB'),
      render: ({ data }: { data: MysqlPermissionAccountModel }) => {
        const renderRules = rowFlodMap.value[data.account.user] ? data.rules.slice(0, 1) : data.rules;
        return renderRules.map((item) => (
          <div class='inner-row'>
            <bk-tag>{item.access_db}</bk-tag>
          </div>
        ));
      },
      showOverflowTooltip: true,
      width: 300,
    },
    {
      field: 'privilege',
      label: t('权限'),
      render: ({ data }: { data: MysqlPermissionAccountModel }) => {
        if (data.rules.length === 0) {
          return <div class='inner-row'>--</div>;
        }
        const renderRules = rowFlodMap.value[data.account.user] ? data.rules.slice(0, 1) : data.rules;
        return renderRules.map((item) => (
          <div class='inner-row cell-privilege'>
            <TextOverflowLayout>
              {{
                default: () => item.privilege,
              }}
            </TextOverflowLayout>
          </div>
        ));
      },
      showOverflowTooltip: false,
    },
  ]);

  const cloneRuleColumns = [
    {
      field: 'source_db',
      label: t('克隆 DB'),
    },
    {
      field: '',
      label: t('克隆表结构'),
      render: () => t('所有表'),
    },
    {
      label: t('克隆表数据'),
      render: ({ data }: { data: OpenareaTemplateModel['config_rules'][0] }) => (
        <>{data.data_tblist.length > 0 ? data.data_tblist.map((item) => <bk-tag>{item}</bk-tag>) : '--'}</>
      ),
    },
    {
      field: 'target_db_pattern',
      label: t('生成目标 DB 范式'),
    },
  ];

  watch(
    () => props.data.related_authorize,
    async (ruleIds) => {
      if (ruleIds.length > 0) {
        permissionTableloading.value = true;
        const rulesResult = await getPermissionRules({
          account_type: 'mysql',
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          limit: -1,
          offset: 0,
          rule_ids: ruleIds.join(','),
        }).finally(() => {
          permissionTableloading.value = false;
        });
        permissionTableData.value = rulesResult.results;
      }
    },
    {
      immediate: true,
    },
  );

  const getCellClass = (data: { field: string }) => (data.field === 'privilege' ? 'cell-privilege' : '');

  const handleToogleExpand = (user: string) => {
    if (rowFlodMap.value[user]) {
      delete rowFlodMap.value[user];
    } else {
      rowFlodMap.value[user] = true;
    }
  };
</script>
<style lang="less">
  .template-detail-collapse {
    .bk-collapse-title {
      font-weight: 700;
    }

    .template-detail-permission-table {
      .account-box {
        font-weight: 700;

        .flod-flag {
          display: inline-block;
          margin-right: 4px;
          cursor: pointer;
          transition: all 0.1s;

          &.is-flod {
            transform: rotateZ(-90deg);
          }
        }
      }

      .cell-privilege {
        .vxe-cell {
          padding: 0 !important;
          margin-left: -16px;

          .inner-row {
            padding-left: 32px !important;
          }
        }
      }

      .inner-row {
        display: flex;
        height: 40px;
        align-items: center;

        & ~ .inner-row {
          border-top: 1px solid #dcdee5;
        }
      }
    }
  }
</style>
