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
  <div class="alert-group">
    <div class="alert-group-operations mb-16">
      <AuthButton
        action-id="notify_group_manage"
        theme="primary"
        @click="handleOpenDetail('add')">
        {{ t('新建') }}
      </AuthButton>
      <DbQuickSearch
        v-model="quickSearchValue"
        class="mb-16"
        :data="quickSearchData"
        parse-url
        :placeholder="t('请输入或选择条件搜索')"
        style="width: 500px; margin-left: auto"
        @change="handleQuickSearchChange" />
    </div>
    <DbTable
      ref="tableRef"
      class="alert-group-table"
      :data-source="getAlarmGroupList"
      :filter-value="quickSearchValue"
      releate-url-query
      :row-class-name="setRowClass"
      row-key="id"
      @filter-change="handleFilterChange"
      @request-success="handleRequestSuccess">
      <TableColumn
        col-key="name"
        :filter="columnFilter.name"
        fixed="left"
        :title="t('告警组名称')"
        :width="240">
        <template #default="{ row }: { row: NoticGroupModel }">
          <TextOverflowLayout>
            <template #append>
              <BkTag
                v-if="row.is_built_in"
                class="ml-4"
                size="small">
                {{ t('内置') }}
              </BkTag>
              <BkTag
                v-if="row.isNew"
                class="ml-4"
                size="small"
                theme="success">
                NEW
              </BkTag>
            </template>
            <template #default>
              <BkButton
                v-if="row.is_built_in"
                text
                theme="primary"
                @click="handleOpenDetail('edit', row)">
                {{ row.name }}
              </BkButton>
              <AuthButton
                v-else
                action-id="'notify_group_manage'"
                :permission="row.permission.notify_group_manage"
                text
                theme="primary"
                @click="handleOpenDetail('edit', row)">
                {{ row.name }}
              </AuthButton>
            </template>
          </TextOverflowLayout>
        </template>
      </TableColumn>
      <TableColumn
        col-key="receivers"
        :filter="columnFilter.receivers"
        :min-width="400"
        :title="t('通知对象')">
        <template #default="{ row }: { row: NoticGroupModel }">
          <RenderRow
            v-if="Object.keys(userGroupMap).length && row.receivers.length"
            :data="getReceivers(row)" />
          <span v-else>--</span>
        </template>
      </TableColumn>
      <NoticeMethodColumn />
      <TableColumn
        col-key="usedCountTotal"
        :title="t('关联策略')"
        :width="100">
        <template #default="{ row }: { row: NoticGroupModel }">
          <BkPopover
            v-if="row.usedCountTotal >= 2"
            click-content-auto-hide
            placement="top"
            theme="light"
            trigger="click"
            :width="180">
            <span style="color: #3a84ff; cursor: pointer">{{ row.usedCountTotal }}</span>
            <template #content>
              <div>
                <I18nT
                  class="mb-12"
                  keypath="共n条策略"
                  tag="div">
                  <template #n>
                    <span style="font-weight: bolder">{{ row.usedCountTotal }}</span>
                  </template>
                </I18nT>
                <div
                  v-for="[dbType, count] in Object.entries(row.used_count)"
                  :key="dbType"
                  class="alert-group-used-count-item">
                  <BkButton
                    text
                    theme="primary"
                    @click="toRelatedPolicy(row.id, dbType)">
                    {{ DBTypeInfos[dbType as DBTypes].name }}
                  </BkButton>
                  <BkTag
                    radius="50%"
                    size="small">
                    {{ count }}
                  </BkTag>
                </div>
              </div>
            </template>
          </BkPopover>
          <BkButton
            v-else-if="row.usedCountTotal === 1"
            text
            theme="primary"
            @click="toRelatedPolicy(row.id, Object.keys(row.used_count)[0])">
            {{ row.usedCountTotal }}
          </BkButton>
          <span
            v-else
            v-bk-tooltips="t('暂无策略使用此告警组')"
            style="cursor: pointer">
            0
          </span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="update_at"
        sorter
        :title="t('更新时间')"
        :width="250">
        <template #default="{ row }: { row: NoticGroupModel }">
          <span>{{ row.updateAtDisplay || '--' }}</span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="updater"
        :title="t('更新人')"
        :width="180">
        <template #default="{ row }: { row: NoticGroupModel }">
          <span>{{ row.updater || '--' }}</span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="operation"
        fixed="right"
        :title="t('操作')"
        :width="130">
        <template #default="{ row }: { row: NoticGroupModel }">
          <AuthButton
            v-bk-tooltips="{
              content: t('内置告警组不可编辑，可通过克隆创建自定义副本后再编辑'),
              disabled: !row.is_built_in,
            }"
            action-id="notify_group_manage"
            :disabled="row.is_built_in"
            :permission="row.permission.notify_group_manage"
            text
            theme="primary"
            @click="handleOpenDetail('edit', row)">
            {{ t('编辑') }}
          </AuthButton>
          <AuthButton
            action-id="notify_group_manage"
            class="ml-16"
            :permission="row.permission.notify_group_manage"
            text
            theme="primary"
            @click="handleOpenDetail('copy', row)">
            {{ t('克隆') }}
          </AuthButton>
          <AuthButton
            v-bk-tooltips="{
              content: row.is_built_in
                ? t('内置告警组不可删除')
                : row.usedCountTotal > 0
                  ? t('已被 n 个策略使用，无法删除', { n: row.usedCountTotal })
                  : '',
              disabled: !(row.is_built_in || row.usedCountTotal > 0),
            }"
            action-id="notify_group_manage"
            class="ml-16"
            :disabled="row.is_built_in || row.usedCountTotal > 0"
            :permission="row.permission.notify_group_manage"
            text
            theme="primary"
            @click="handleDelete(row.id)">
            {{ t('删除') }}
          </AuthButton>
        </template>
      </TableColumn>
    </DbTable>
    <DetailDialog
      v-model="detailDialogShow"
      :biz-id="currentBizId"
      :detail-data="detailData"
      :name-list="nameList"
      :type="detailType"
      @successed="fetchTableData" />
  </div>
</template>

<script setup lang="ts">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import NoticGroupModel from '@services/model/notice-group/notice-group';
  import { getUserGroupList } from '@services/source/cmdb';
  import { deleteAlarmGroup, getAlarmGroupList } from '@services/source/monitorNoticeGroup';
  import type { ListBase } from '@services/types';

  import { useGlobalBizs } from '@stores';

  import { DBTypeInfos, DBTypes } from '@common/const/index.ts';

  import DbTable from '@components/db-table/IndexNew.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { messageSuccess } from '@utils';

  import DetailDialog from './components/detail-dialog/Index.vue';
  import NoticeMethodColumn from './components/NoticeMethodColumn.vue';
  import RenderRow from './components/RenderRow.vue';
  import { useColumnFilter } from './useColumnFilter.ts';
  import { useQuickSearch } from './useQuickSearch.ts';

  interface UserGroupMap {
    [key: string]: ServiceReturnType<typeof getUserGroupList>[number];
  }

  interface ReceiverItem {
    display_name: string;
    id: string;
    logo: string;
    members: string[];
    type: string;
  }

  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();
  const router = useRouter();
  const { quickSearchData, quickSearchValue } = useQuickSearch();
  const { data: columnFilter } = useColumnFilter();

  const tableRef = useTemplateRef('tableRef');

  const detailDialogShow = ref(false);
  const detailType = ref<'add' | 'edit' | 'copy'>('add');
  const detailData = ref({} as NoticGroupModel);
  const nameList = ref<string[]>([]);
  const userGroupMap = shallowRef<UserGroupMap>({});

  useRequest(getUserGroupList, {
    defaultParams: [{ bk_biz_id: currentBizId }],
    onSuccess(userGroupList) {
      userGroupMap.value = userGroupList.reduce(
        (userGroupPrev, userGroup) =>
          Object.assign({}, userGroupPrev, {
            [userGroup.id]: userGroup,
          }),
        {} as UserGroupMap,
      );
    },
  });

  const getReceivers = (data: NoticGroupModel): ReceiverItem[] => {
    return data.receivers.map((item) => {
      if (item.type === 'group') {
        return userGroupMap.value[item.id] || item;
      }
      return {
        ...item,
        display_name: item.id,
        logo: '',
        members: [],
      };
    });
  };

  const handleQuickSearchChange = () => {
    fetchTableData();
  };

  const handleFilterChange = (filterValue: Record<string, string>) => {
    quickSearchValue.value = filterValue;
    fetchTableData();
  };

  const fetchTableData = () => {
    tableRef.value!.fetchData({
      ...quickSearchValue.value,
      bk_biz_id: currentBizId,
    });
  };

  const setRowClass = ({ row }: { row: NoticGroupModel }) => (row.isNew ? 'is-new' : '');

  const toRelatedPolicy = (notifyGroups: number, dbType: string) => {
    const routerData = router.resolve({
      name: 'monitorStrategy',
      query: {
        db_type: dbType,
        notify_groups: notifyGroups,
      },
    });

    window.open(routerData.href, '_blank');
  };

  const handleOpenDetail = (type: 'add' | 'edit' | 'copy', row?: NoticGroupModel) => {
    detailDialogShow.value = true;
    detailType.value = type;
    if (row) {
      detailData.value = row;
    }
  };

  const handleDelete = (id: number) => {
    InfoBox({
      content: t('删除后将无法恢复'),
      onConfirm: async () => {
        await deleteAlarmGroup({ id });
        messageSuccess(t('删除成功'));
        fetchTableData();
      },
      title: t('确认删除该告警组'),
      type: 'warning',
    });
  };

  const handleRequestSuccess = (tableData: ListBase<NoticGroupModel[]>) => {
    nameList.value = tableData.results.map((tableItem) => tableItem.name);
  };

  onMounted(() => {
    fetchTableData();
  });
</script>

<style lang="less" scoped>
  .alert-group-used-count-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    height: 32px;
    line-height: 32px;
    border-top: 1px solid #dcdee5;

    &:last-child {
      border-bottom: 1px solid #dcdee5;
    }
  }

  .alert-group {
    .alert-group-operations {
      display: flex;

      .search-input {
        width: 500px;
        margin-left: auto;
      }
    }

    :deep(.alert-group-table) {
      .name-cell {
        display: flex;
        align-items: center;

        .name-button {
          display: block;
          overflow: hidden;
          line-height: 1.5;
          flex: 0 1 auto;

          .bk-button-text {
            display: block;
            overflow: hidden;
            line-height: inherit;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
        }
      }

      .is-new {
        td {
          background-color: #f3fcf5 !important;
        }
      }
    }
  }
</style>
