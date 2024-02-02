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
  <BkDialog
    class="account-rules-selector"
    :draggable="false"
    :esc-close="false"
    :height="700"
    :is-show="isShow"
    :quick-close="false"
    :title="t('选择账号权限')"
    :width="1300"
    @closed="isShow = false">
    <DbSearchSelect
      v-model="tableSearch"
      class="mb-16"
      :data="filters"
      :placeholder="t('请输入账号或DB名')"
      style="width: 520px;"
      unique-select
      @change="handleSearchSelectChange" />
    <AccountRulesTable
      ref="accountRulesTableRef"
      select-mode
      :selected-list="selectedList"
      @change="handleChange" />
    <template #footer>
      <div class="footer-wrapper">
        <div class="selected-text">
          <I18nT keypath="已选n台">
            <span class="selected-count">{{ selectedCount }}</span>
          </I18nT>
        </div>
        <BkButton
          class="mr-8"
          :disabled="!dataList.length"
          theme="primary"
          @click="handleConfirm">
          {{ t('确定') }}
        </BkButton>
        <BkButton @click="handleClose">
          {{ t('取消') }}
        </BkButton>
      </div>
    </template>
  </bkdialog>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import MongodbPermissonAccountModel from '@services/model/mongodb-permission/mongodb-permission-account';

  import { getSearchSelectorParams } from '@utils';

  import AccountRulesTable from './components/AccountRulesTable.vue';

  interface Props {
    selectedList?: MongodbPermissonAccountModel[]
  }

  interface Emits {
    (e: 'change', value: MongodbPermissonAccountModel[]): void,
  }

  withDefaults(defineProps<Props>(), {
    selectedList: () => [],
  });
  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>('isShow', {
    required: true,
    default: false,
  });

  const { t } = useI18n();

  const filters = [
    {
      name: t('账号名称'),
      id: 'user',
    },
    {
      name: t('访问DB'),
      id: 'access_db',
    },
  ];

  const accountRulesTableRef = ref<InstanceType<typeof AccountRulesTable>>();
  const tableSearch = ref([]);
  const dataList = shallowRef<MongodbPermissonAccountModel[]>([]);

  const selectedCount = computed(() => dataList.value
    .reduce((prevCount, dataItem) => prevCount + dataItem.rules.length, 0));

  watch(isShow, (newShow) => {
    nextTick(() => {
      if (newShow) {
        accountRulesTableRef.value!.searchData();
      }
    });
  });

  const handleSearchSelectChange = () => {
    accountRulesTableRef.value!.searchData(getSearchSelectorParams(tableSearch.value));
  };

  const handleChange = (value: Record<number, {
    account: MongodbPermissonAccountModel['account'],
    rule: MongodbPermissonAccountModel['rules'][number]
  }>) => {
    const dataMap = Object.keys(value).reduce((prev, key) => {
      const item = value[Number(key)];
      const resultItem = prev[item.account.account_id];
      if (!resultItem) {
        return Object.assign({}, prev, {
          [item.account.account_id]: Object.assign({}, item, { rules: [item.rule] }),
        });
      }
      resultItem.rules.push(item.rule);
      return prev;
    }, {} as Record<number, MongodbPermissonAccountModel>);
    dataList.value = Object.values(dataMap);
  };

  const handleConfirm = () => {
    // const result = Object.keys(selectedMap.value).reduce((result, tabKey) => ({
    //   ...result,
    //   [tabKey]: Object.values(selectedMap.value[tabKey]),
    // }), {});
    emits('change', dataList.value);
    handleClose();
  };

  const handleClose = () => {
    isShow.value =  false;
  };
</script>

<style lang="less" scoped>
.account-rules-selector {
  :deep(.bk-dialog-header) {
    padding-bottom: 12px;
  }

  .footer-wrapper {
    display: flex;
    align-items: center;

    .selected-text {
      margin-right: auto;

      .selected-count {
        font-size: 700;
        color: #2dcb56;
      }
    }
  }
}
</style>
