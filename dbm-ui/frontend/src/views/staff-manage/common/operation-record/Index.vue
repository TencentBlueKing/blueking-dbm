<template>
  <div class="staff-manage-operation-record">
    <DbQuickSearch
      v-model="quickSearchValue"
      class="mb-16"
      :data="quickSearchData"
      parse-url
      :placeholder="
        isPlatform
          ? t('搜索操作人、操作时间、所属业务、操作类型、DB 类型、变更角色、变更人员')
          : t('搜索操作人、操作时间、操作类型、DB 类型、变更角色、变更人员')
      "
      style="width: 500px"
      @change="handleQuickSearchChange" />
    <DbTable
      ref="tableRef"
      :data-source="dataSource"
      :filter-value="quickSearchValue"
      releate-url-query
      row-key="id"
      @filter-change="handleFilterChange">
      <TableColumn
        col-key="creator"
        :filter="columnFilter?.creator"
        :title="t('操作人')"
        width="110" />
      <TableColumn
        col-key="create_at"
        :filter="columnFilter?.create_at"
        :title="t('操作时间')"
        width="150">
        <template #default="{ row }: { row: DBAdminOperationRecordModel }">
          {{ row.createAtDisplay || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        v-if="isPlatform"
        col-key="bk_biz_id"
        :filter="columnFilter?.bk_biz_id"
        :title="t('业务')"
        width="120">
        <template #default="{ row }: { row: DBAdminOperationRecordModel }">
          {{ row.bk_biz_id ? bizIdMap.get(row.bk_biz_id)?.name || '--' : '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="operate_type"
        :filter="columnFilter?.operate_type"
        :title="t('操作类型')"
        width="120">
        <template #default="{ row }: { row: DBAdminOperationRecordModel }">
          <BkTag
            v-if="row.operate_type === DBAOperateTypes.DEFAULT_DBA_CHANGE"
            class="custom-tag">
            {{ dbaOperateTypesInfo[row.operate_type].text }}
          </BkTag>
          <BkTag
            v-else
            :theme="dbaOperateTypesInfo[row.operate_type].theme">
            {{ dbaOperateTypesInfo[row.operate_type].text }}
          </BkTag>
        </template>
      </TableColumn>
      <TableColumn
        col-key="db_type"
        :filter="columnFilter?.db_type"
        :title="t('DB类型')"
        width="90">
        <template #default="{ row }: { row: DBAdminOperationRecordModel }">
          {{ row.db_type ? DBTypeInfos[row.db_type].name : '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="role"
        :filter="columnFilter?.role"
        :title="t('变更角色')"
        width="90">
        <template #default="{ row }: { row: DBAdminOperationRecordModel }">
          <template v-if="row.role">
            <div
              class="role-dot mr-8"
              :class="[`role-${dbaRoleTypesInfo[row.role].tagTheme}`]" />
            <span>{{ dbaRoleTypesInfo[row.role].text }}</span>
          </template>
          <span v-else>--</span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="change_before"
        :title="t('变更前')"
        width="150">
        <template #default="{ row }: { row: DBAdminOperationRecordModel }">
          <template v-if="row.change_before">
            <TagList
              v-if="row.operate_type === DBAOperateTypes.TAG_CHANGE"
              :list="row.change_before.split(',').map((tagItem) => ({ label: tagItem, value: tagItem }))" />
            <span v-else>{{ row.change_before || '--' }}</span>
          </template>
          <span v-else>--</span>
        </template>
      </TableColumn>
      <TableColumn
        col-key="change_after"
        :title="t('变更后')"
        width="150">
        <template #default="{ row }: { row: DBAdminOperationRecordModel }">
          <template v-if="row.change_after">
            <TagList
              v-if="row.operate_type === DBAOperateTypes.TAG_CHANGE"
              :list="row.change_after.split(',').map((tagItem) => ({ label: tagItem, value: tagItem }))" />
            <span v-else>{{ row.change_after || '--' }}</span>
          </template>
          <span v-else>--</span>
        </template>
      </TableColumn>
    </DbTable>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import DBAdminOperationRecordModel from '@services/model/db-admin/db-admin-operation_record';
  import { getAppOprationRecord } from '@services/source/dbadmin';

  import { useGlobalBizs } from '@stores';

  import { DBAOperateTypes, dbaOperateTypesInfo, dbaRoleTypesInfo, DBTypeInfos } from '@common/const';

  import DbTable from '@components/db-table/IndexNew.vue';

  import TagList from '@views/staff-manage/common/TagList.vue';

  import { useColumnFilter } from './useColumnFilter';
  import { useQuickSearch } from './useQuickSearch';

  const route = useRoute();
  const { t } = useI18n();
  const { bizIdMap } = useGlobalBizs();

  const isPlatform = route.name === 'PlatformStaffManage';
  const { quickSearchData, quickSearchValue } = useQuickSearch(isPlatform);
  const { data: columnFilter } = useColumnFilter();

  const tableRef = useTemplateRef('tableRef');

  const dataSource = (params: ServiceParameters<typeof getAppOprationRecord>) =>
    getAppOprationRecord({
      bk_biz_id: isPlatform ? undefined : window.PROJECT_CONFIG.BIZ_ID,
      ...params,
    });

  const fetchData = () => {
    tableRef.value!.fetchData(quickSearchValue.value);
  };

  const handleQuickSearchChange = () => {
    fetchData();
  };

  const handleFilterChange = (filterValue: Record<string, any>) => {
    quickSearchValue.value = filterValue;
  };
</script>

<style lang="less">
  .staff-manage-operation-record {
    .custom-tag {
      color: #531dab;
      background: #f9f0ff;
    }

    .role-dot {
      display: inline-block;
      width: 6px;
      height: 6px;
      vertical-align: middle;
      border-radius: 2px;
    }

    .role-info {
      background: #3a84ff;
    }

    .role-success {
      background: #2caf5e;
    }

    .role-warning {
      background: #f59500;
    }
  }
</style>
