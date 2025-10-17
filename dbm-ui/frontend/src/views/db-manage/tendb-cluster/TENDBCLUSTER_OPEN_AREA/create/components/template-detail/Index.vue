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
  <BkSideslider
    v-model:is-show="isShow"
    :title="t('模板详情【templateName配置 】', { name: data?.config_name })"
    :width="1100">
    <BkCollapse
      v-model="activeIndex"
      class="template-detail-collapse"
      header-icon="right-shape">
      <BkCollapsePanel name="clone-rule">
        <span>{{ t('克隆的规则') }}</span>
        <template #content>
          <BkTable
            class="template-detail-table"
            :data="data.config_rules">
            <BkTableColumn
              field="source_db"
              :label="t('克隆 DB')" />
            <BkTableColumn :label="t('克隆表结构')">
              <template #default>
                {{ t('所有表') }}
              </template>
            </BkTableColumn>
            <BkTableColumn :label="t('克隆表数据')">
              <template #default="{ row }:{ row: OpenareaTemplateModel['config_rules'][0] }">
                <span v-if="!row.data_tblist.length">--</span>
                <BkTag
                  v-for="item in row.data_tblist"
                  v-else
                  :key="item">
                  {{ item }}
                </BkTag>
              </template>
            </BkTableColumn>
            <BkTableColumn
              field="target_db_pattern"
              :label="t('生成目标 DB 范式')" />
          </BkTable>
        </template>
      </BkCollapsePanel>
      <BkCollapsePanel name="permission-rule">
        <span>{{ t('权限规则') }}</span>
        <template #content>
          <BkLoading :loading="loading">
            <BkTable
              class="template-detail-permission-table"
              :data="tableData">
              <BkTableColumn
                field="user"
                :label="t('账号名称')"
                :show-overflow="false"
                :width="220">
                <template #default="{ row }: { row: MysqlPermissionAccountModel }">
                  <DbIcon
                    v-if="row.rules.length > 1"
                    class="flod-flag"
                    :class="{
                      'is-flod': rowFlodMap[row.account.user],
                    }"
                    type="down-shape"
                    @click="() => handleToogleExpand(row.account.user)" />
                  <span style="font-weight: 700">{{ row.account.user }}</span>
                </template>
              </BkTableColumn>
              <BkTableColumn
                field="access_db"
                :label="t('访问DB')"
                :width="300">
                <template #default="{ row }: { row: MysqlPermissionAccountModel }">
                  <BkTag
                    v-for="item in rowFlodMap[row.account.user] ? row.rules.slice(0, 1) : row.rules"
                    :key="item.access_db">
                    {{ item.access_db }}
                  </BkTag>
                </template>
              </BkTableColumn>
              <BkTableColumn
                field="privilege"
                :label="t('权限')"
                :show-overflow="false"
                :width="300">
                <template #default="{ row }: { row: MysqlPermissionAccountModel }">
                  <span v-if="!row.rules.length">--</span>
                  <TextOverflowLayout
                    v-for="item in rowFlodMap[row.account.user] ? row.rules.slice(0, 1) : row.rules"
                    v-else
                    :key="item.privilege">
                    {{ item.privilege }}
                  </TextOverflowLayout>
                </template>
              </BkTableColumn>
            </BkTable>
          </BkLoading>
        </template>
      </BkCollapsePanel>
    </BkCollapse>
  </BkSideslider>
</template>
<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MysqlPermissionAccountModel from '@services/model/mysql/mysql-permission-account';
  import OpenareaTemplateModel from '@services/model/openarea/openareaTemplate';
  import { getPermissionRules } from '@services/source/mysqlPermissionAccount';

  import { AccountTypes } from '@common/const';

  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  interface Props {
    data: OpenareaTemplateModel;
  }

  const props = defineProps<Props>();

  const isShow = defineModel<boolean>('isShow');

  const { t } = useI18n();

  const activeIndex = ref(['clone-rule', 'permission-rule']);
  const rowFlodMap = ref<Record<string, boolean>>({});
  const tableData = ref<MysqlPermissionAccountModel[]>([]);

  const { loading, run: fetchData } = useRequest(getPermissionRules, {
    manual: true,
    onSuccess(data) {
      tableData.value = data.results;
    },
  });

  watch(
    () => props.data.related_authorize,
    (ruleIds) => {
      if (ruleIds.length > 0) {
        fetchData({
          account_type: AccountTypes.TENDBCLUSTER,
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
          limit: -1,
          offset: 0,
          rule_ids: ruleIds.join(','),
        });
      }
    },
    {
      immediate: true,
    },
  );

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
    padding: 20px 16px;

    .bk-collapse-title {
      font-weight: 700;
    }

    .template-detail-permission-table {
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
  }
</style>
