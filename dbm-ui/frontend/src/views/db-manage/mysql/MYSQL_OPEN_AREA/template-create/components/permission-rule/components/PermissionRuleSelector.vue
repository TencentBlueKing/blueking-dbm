<template>
  <BkDialog
    v-model:is-show="isShow"
    :title="t('添加授权规则')"
    width="80%">
    <div class="openarea-permission-rule-selector">
      <div class="top-operate mb-16">
        <div class="search-main">
          <DbQuickSearch
            v-model="searchSelectValue"
            class="mr-18"
            :data="searchSelectData"
            parse-url
            :placeholder="t('请输入账号或DB名')"
            style="width: 520px"
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
        fixed-pagination
        :height="700"
        :row-class-name="rowClass"
        row-key="account.account_id"
        @clear-search="handleClearSearch"
        @request-success="initRowFlodMap">
        <TableColumn
          col-key="user"
          :title="t('账号名称')"
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
        </TableColumn>
        <TableColumn
          col-key="access_db"
          :title="t('访问DB')"
          :width="300">
          <template #default="{ row }: {row: MysqlPermissionAccountModel}">
            <div v-if="row.rules.length === 0">
              <span>{{ t('暂无规则') }}，</span>
              <AuthButton
                action-id="mysql_priv_manage"
                :permission="row.permission.mysql_priv_manage"
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
        </TableColumn>
        <TableColumn
          col-key="privilege"
          :min-width="300"
          :title="t('权限')">
          <template #default="{ row }: {row: MysqlPermissionAccountModel}">
            <TextOverflowLayout
              v-for="item in rowFlodMap[row.account.user] ? row.rules : row.rules.slice(0, 1)"
              :key="item.rule_id"
              class="inner-row">
              {{ item.privilege }}
            </TextOverflowLayout>
          </template>
        </TableColumn>
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
  import { useI18n } from 'vue-i18n';

  import MysqlPermissionAccountModel from '@services/model/mysql/mysql-permission-account';
  import { getPermissionRules } from '@services/source/mysqlPermissionAccount';

  import type { AccountTypes } from '@common/const';

  import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';
  import DbTable from '@components/db-table/IndexNew.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

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
  const searchSelectValue = ref<Record<string, string>>({});
  const isOnlyShowSelected = ref(false);

  const checkedCount = computed(() => Object.keys(ruleCheckedMap.value).length);

  const searchSelectData = [
    {
      id: 'user',
      name: t('账号名称'),
      type: 'multiple-input',
    },
    {
      id: 'access_db',
      name: t('访问DB'),
      type: 'multiple-input',
    },
  ] as QuickSearchProps['data'];

  watch(isShow, () => {
    if (!isShow.value) {
      searchSelectValue.value = {};
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
    tableRef.value.fetchData({
      account_type: props.accountType,
      cluster_id: props.clusterId,
    });
  };

  const handleSearchChange = (value: Record<string, string>) => {
    ruleCheckedMap.value = {};
    tableRef.value.fetchData({
      account_type: props.accountType,
      cluster_id: props.clusterId,
      ...value,
    });
  };

  const handleClearSearch = () => {
    searchSelectValue.value = {};
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
      tableRef.value.fetchData({
        account_type: props.accountType,
        cluster_id: props.clusterId,
        rule_ids: ruleIds.join(','),
      });
      return;
    }
    fetchTableData();
  };

  const handleGoCreateRules = () => {
    const route = router.resolve({
      name: 'PermissionRules',
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
