<template>
  <BkDialog
    v-model:is-show="isShow"
    :title="t('添加授权规则')"
    width="80%">
    <div class="openarea-permission-rule-selector">
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
        :data-source="getPermissionRules"
        :max-height="700"
        :row-class-name="rowClass"
        :show-overflow="false"
        @clear-search="handleClearSearch"
        @request-success="initRowFlodMap">
        <BkTableColumn
          field="user"
          :label="t('账号名称')"
          :width="220">
          <template #default="{ row }: {row: MysqlPermissionAccountModel}">
            <DbIcon
              v-if="row.rules.length > 1"
              class="flod-flag"
              :class="{
                'is-flod': rowFlodMap[row.account.user],
              }"
              type="down-shape"
              @click="() => handleToogleExpand(row.account.user)" />
            {{ row.account.user }}
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="access_db"
          :label="t('访问DB')"
          :width="300">
          <template #default="{ row }: {row: MysqlPermissionAccountModel}">
            <div v-if="row.rules.length === 0">
              <span>{{ t('暂无规则') }}，</span>
              <AuthButton
                action-id="tendbcluster_priv_manage"
                :permission="row.permission.tendbcluster_priv_manage"
                :resource="row.account.account_id"
                size="small"
                text
                theme="primary"
                @click="handleGoCreateRules">
                {{ t('立即新建') }}
              </AuthButton>
            </div>
            <p
              v-for="item in rowFlodMap[row.account.user] ? row.rules : row.rules.slice(0, 1)"
              :key="item.rule_id"
              class="inner-row">
              <BkCheckbox
                class="mr-8"
                :model-value="ruleCheckedMap[item.rule_id]"
                @change="(value: boolean) => handleDbChange(value, item.rule_id)" />
              <BkTag>{{ item.access_db }}</BkTag>
            </p>
          </template>
        </BkTableColumn>
        <BkTableColumn
          field="privilege"
          :label="t('权限')"
          :min-width="300">
          <template #default="{ row }: {row: MysqlPermissionAccountModel}">
            <TextOverflowLayout
              v-for="item in rowFlodMap[row.account.user] ? row.rules : row.rules.slice(0, 1)"
              :key="item.rule_id"
              class="inner-row">
              {{ item.privilege }}
            </TextOverflowLayout>
          </template>
        </BkTableColumn>
      </DbTable>
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

  import MysqlPermissionAccountModel from '@services/model/mysql/mysql-permission-account';
  import { getPermissionRules } from '@services/source/mysqlPermissionAccount';

  import type { AccountTypes } from '@common/const';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { getSearchSelectorParams } from '@utils';

  interface Props {
    accountType: AccountTypes.MYSQL | AccountTypes.TENDBCLUSTER;
    clusterId: number;
  }

  type Emits = (e: 'submit', value: number[]) => void;

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
      id: 'user',
      multiple: true,
      name: t('账号名称'),
    },
    {
      id: 'access_db',
      multiple: true,
      name: t('访问DB'),
    },
  ];

  watch(isShow, () => {
    if (!isShow.value) {
      searchSelectValue.value = [];
      return;
    }

    ruleCheckedMap.value = modleValue.value.reduce(
      (result, id) =>
        Object.assign(result, {
          [id]: true,
        }),
      {},
    );

    nextTick(() => {
      fetchTableData();
    });
  });

  const rowClass = ({ row }: { row: MysqlPermissionAccountModel }) => {
    if (!rowFlodMap.value[row.account.user]) {
      return 'init-height';
    }
    return '';
  };

  const fetchTableData = () => {
    tableRef.value.fetchData(
      {
        cluster_id: props.clusterId,
      },
      {
        account_type: props.accountType,
      },
    );
  };

  const handleSearchChange = (valueList: ISearchValue[]) => {
    ruleCheckedMap.value = {};
    const params = getSearchSelectorParams(valueList);
    tableRef.value.fetchData(
      {
        cluster_id: props.clusterId,
        ...params,
      },
      {
        account_type: props.accountType,
      },
    );
  };

  const handleClearSearch = () => {
    searchSelectValue.value = [];
    fetchTableData();
  };

  const initRowFlodMap = (data: ServiceReturnType<typeof getPermissionRules>) => {
    rowFlodMap.value = data.results.reduce<typeof rowFlodMap.value>((acc, item: MysqlPermissionAccountModel) => {
      Object.assign(acc, {
        [item.account.user]: item.rules.length > 1, // 默认展开
      });
      return acc;
    }, {});
  };

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
      const ruleIds = Object.keys(ruleCheckedMap.value).map((item) => Number(item));
      tableRef.value.fetchData(
        {
          cluster_id: props.clusterId,
          rule_ids: ruleIds.join(','),
        },
        {
          account_type: props.accountType,
        },
      );
      return;
    }
    fetchTableData();
  };

  const handleGoCreateRules = () => {
    const route = router.resolve({
      name: 'spiderPermission',
    });
    window.open(route.href);
  };

  const handleSubmit = () => {
    const ruleIds = Object.keys(ruleCheckedMap.value).map((item) => Number(item));
    modleValue.value = ruleIds;
    emits('submit', ruleIds);
    isShow.value = false;
  };

  const handleCancel = () => {
    isShow.value = false;
  };
</script>
<style lang="less">
  .openarea-permission-rule-selector {
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

    .flod-flag {
      display: inline-block;
      margin-right: 4px;
      cursor: pointer;
      transition: all 0.1s;

      &.is-flod {
        transform: rotateZ(-90deg);
      }
    }

    .inner-row {
      height: 28px;
      display: flex;
      align-items: center;
    }

    .init-height {
      td {
        height: initial !important;
      }
    }
  }
</style>
