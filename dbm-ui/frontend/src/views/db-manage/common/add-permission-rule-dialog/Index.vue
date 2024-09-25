<template>
  <BkDialog
    v-model:is-show="isShow"
    :title="t('添加授权规则')"
    :width="1300">
    <div class="openarea-create-permission-rule">
      <div class="top-operate mb-16">
        <div class="search-main">
          <DbSearchSelect
            v-model="searchSelectValue"
            class="mr-18"
            :data="searchSelectData"
            :placeholder="t('请输入账号或DB名')"
            style="width: 520px"
            tyle="width: 520px"
            unique-select
            @change="handleSearchChange" />
          <BkCheckbox
            v-model="isOnlyShowSelected"
            @change="handleChangeOnlyShowSelected">
            {{ t('仅显示已选择') }}
          </BkCheckbox>
        </div>
        <BkButton
          text
          theme="primary"
          @click="handleGoCreateRules">
          <DbIcon
            class="mr-5"
            type="link" />
          {{ t('去创建新的权限') }}
        </BkButton>
      </div>
      <DbTable
        ref="tableRef"
        :cell-class="cellClassCallback"
        :columns="columns"
        :data-source="getPermissionRules"
        :max-height="700"
        :settings="settings"
        @clear-search="handleClearSearch" />
    </div>
    <template #footer>
      <div style="display: flex">
        <I18nT
          v-if="checkedCount"
          keypath="已选n个"
          tag="div">
          <span
            class="number"
            style="color: #2dcb56">
            {{ checkedCount }}
          </span>
        </I18nT>
        <BkButton
          style="margin-left: auto"
          theme="primary"
          @click="handleSubmit">
          {{ t('确定') }}
        </BkButton>
        <BkButton
          class="ml-8"
          @click="handleCancel">
          {{ t('取消') }}
        </BkButton>
      </div>
    </template>
  </BkDialog>
</template>
<script setup lang="tsx">
  import type { ISearchValue } from 'bkui-vue/lib/search-select/utils';
  import { useI18n } from 'vue-i18n';

  import MysqlPermissonAccountModel from '@services/model/mysql/mysql-permission-account';
  import { getPermissionRules } from '@services/source/permission';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { getSearchSelectorParams } from '@utils';

  interface Props {
    clusterId: number,
    dbType: 'mysql' | 'tendbcluster',
  }

  interface Emits {
    (e: 'submit', value: number[]): void
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    default: false,
    required: true,
  });
  const modleValue = defineModel<number[]>({
    default: [],
  });

  const { t } = useI18n();
  const router = useRouter();

  const tableRef = ref();
  const rowFlodMap = ref<Record<string, boolean>>({});
  const ruleCheckedMap = ref<Record<number, boolean>>({});
  const searchSelectValue = ref<ISearchValue[]>([]);
  const isOnlyShowSelected = ref(false);

  const checkedCount = computed(() => Object.keys(ruleCheckedMap.value).length);

  const searchSelectData = [
    {
      name: t('账号名称'),
      id: 'user',
      multiple: true,
    },
    {
      name: t('访问DB'),
      id: 'access_db',
      multiple: true,
    },
  ];

  const settings = {
    fields: [
      {
        label: t('账号名称'),
        field: 'user',
      },
      {
        label: t('访问DB'),
        field: 'access_db',
      },
      {
        label: t('权限'),
        field: 'privilege',
      },
    ],
    checked: ['user', 'access_db', 'privilege'],
  };

  const columns = [
    {
      label: t('账号名称'),
      field: 'user',
      width: 220,
      showOverflowTooltip: false,
      render: ({ data }: { data: MysqlPermissonAccountModel }) => (
        <div class="account-box">
          {
            data.rules.length > 1
              && <db-icon
                  type="down-shape"
                  class={{
                    'flod-flag': true,
                    'is-flod': rowFlodMap.value[data.account.user],
                  }}
                  onClick={() => handleToogleExpand(data.account.user)} />
          }
          { data.account.user }
        </div>
      ),
    },
    {
      label: t('访问DB'),
      width: 300,
      field: 'access_db',
      showOverflowTooltip: true,
      sort: true,
      render: ({ data }: { data: MysqlPermissonAccountModel }) => {
        if (data.rules.length === 0) {
          return (
            <div class="inner-row">
              <bk-checkbox class="mr-8" disabled />
              <span>{t('暂无规则，')}</span>
              <router-link
                to={{
                    name: 'PermissionRules',
                }}
                target="_blank">
                {t('去创建')}
              </router-link>
            </div>
          );
        }
        const renderRules = rowFlodMap.value[data.account.user] ? data.rules.slice(0, 1) : data.rules;

        return renderRules.map(item => (
          <div class="inner-row">
            <bk-checkbox
              class="mr-8"
              model-value={ruleCheckedMap.value[item.rule_id]}
              onChange={(value: boolean) => handleDbChange(value, item.rule_id)} />
            <bk-tag>
              {item.access_db}
            </bk-tag>
          </div>
        ));
      },
    },
    {
      label: t('权限'),
      field: 'privilege',
      showOverflowTooltip: false,
      sort: true,
      render: ({ data }: { data: MysqlPermissonAccountModel }) => {
        if (data.rules.length === 0) {
          return <div class="inner-row">--</div>;
        }
        const renderRules = rowFlodMap.value[data.account.user] ? data.rules.slice(0, 1) : data.rules;
        return renderRules.map(item => (
          <div class="inner-row">
            <TextOverflowLayout>
              {{
                default: () => item.privilege
              }}
            </TextOverflowLayout>
          </div>
        ));
      },
    },
  ];

  watch(isShow, () => {
    if (!isShow.value) {
      searchSelectValue.value = [];
      return;
    }

    ruleCheckedMap.value = modleValue.value.reduce((result, id) => Object.assign(result, {
      [id]: true,
    }), {});

    nextTick(() => {
      fetchTableData();
    });
  });

  const fetchTableData = () => {
    tableRef.value.fetchData({
      cluster_id: props.clusterId,
    }, {
      account_type: props.dbType,
    });
  }

  const cellClassCallback = (data: any) => (data.field ? `cell-${data.field}` : '');

  const handleSearchChange = (valueList: ISearchValue[]) => {
    ruleCheckedMap.value = {}
    const params = getSearchSelectorParams(valueList);
    tableRef.value.fetchData({
      cluster_id: props.clusterId,
      ...params,
    }, {
      account_type: props.dbType,
    });
  }

  const handleClearSearch = () => {
    searchSelectValue.value = [];
    fetchTableData();
  }

  const handleToogleExpand = (user: string) => {
    if (rowFlodMap.value[user]) {
      delete rowFlodMap.value[user];
    } else {
      rowFlodMap.value[user] = true;
    }
  };

  const handleDbChange = (checked: boolean, ruleId: number) => {
    if (checked) {
      ruleCheckedMap.value[ruleId] = true;
    } else {
      delete ruleCheckedMap.value[ruleId];
    }
  };

  const handleChangeOnlyShowSelected = (isShow: boolean) => {
    if (isShow) {
      const ruleIds = Object.keys(ruleCheckedMap.value).map(item => Number(item));
      tableRef.value.fetchData({
        cluster_id: props.clusterId,
        rule_ids: ruleIds.join(',')
      }, {
        account_type: props.dbType,
      });
      return;
    }
    fetchTableData();
  }

  const handleGoCreateRules = () => {
    const route = router.resolve({
      name: 'PermissionRules',
    });
    window.open(route.href);
  }

  const handleSubmit = () => {
    const ruleIds = Object.keys(ruleCheckedMap.value).map(item => Number(item));
    modleValue.value = ruleIds
    emits('submit', ruleIds);
    isShow.value = false;
  };

  const handleCancel = () => {
    isShow.value = false;
  };
</script>
<style lang="less">
  .openarea-create-permission-rule {
    height: 730px;

    .top-operate {
      display: flex;
      width: 100%;
      font-size: 12px;

      .search-main {
        flex: 1;
        display: flex;
        align-items: center;

        .bk-checkbox-label {
          font-size: 12px;
        }
      }
    }

    .account-box {
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
      .cell {
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
</style>
