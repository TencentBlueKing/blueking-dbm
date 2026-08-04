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
    :is-show="isShow"
    render-directive="if"
    :show-footer="false"
    :title="t('查看临时密码')"
    :width="1200"
    @closed="isShow = false">
    <div class="temporary-password-modify-instance-box">
      <BkRadioGroup
        v-model="dbType"
        @change="fetchData">
        <BkRadioButton
          class="w-88"
          :label="DBTypes.MYSQL">
          MySQL
        </BkRadioButton>
        <BkRadioButton
          class="w-88"
          :label="DBTypes.TENDBCLUSTER">
          TenDBCluster
        </BkRadioButton>
        <BkRadioButton
          class="w-88"
          :label="DBTypes.SQLSERVER">
          SQLServer
        </BkRadioButton>
      </BkRadioGroup>
      <div class="operate-area">
        <BkButton
          :disabled="!hasSelected"
          @click="handleInstancesCopy">
          {{ t('复制实例') }}
        </BkButton>
        <BkDatePicker
          v-model="searchParams.time"
          class="ml-8"
          clearable
          format="yyyy-MM-dd HH:mm:ss"
          :placeholder="t('请选择')"
          type="datetimerange"
          @change="fetchData" />
        <DbSearchSelect
          v-model="searchParams.keys"
          class="ml-8 search-select"
          :data="searchSelectData"
          :placeholder="t('请输入实例搜索')"
          @change="fetchData" />
      </div>
      <DbTable
        ref="tableRef"
        :data-source="dataSource"
        :releate-url-query="false"
        row-class-name="temporary-password-modify-instance-box-table-row"
        row-key="uniqueKey"
        selectable
        @clear-search="fetchData"
        @selection="handleSelection">
        <TableColumn
          col-key="bk_cloud_name"
          :title="t('云区域')"
          :width="100" />
        <TableColumn
          col-key="instance"
          ellipsis
          :title="t('实例')"
          :width="150">
          <template #default="{ row }">
            <TextOverflowLayout>
              <template #default>
                {{ `${row.ip}:${row.port}` }}
              </template>
              <template #append>
                <BkButton
                  text
                  theme="primary"
                  @click="handleCopy(`${row.ip}:${row.port}`)">
                  <DbIcon
                    class="row-copy-icon ml-4"
                    type="copy" />
                </BkButton>
              </template>
            </TextOverflowLayout>
          </template>
        </TableColumn>
        <TableColumn
          col-key="password"
          ellipsis
          :width="180">
          <template #title>
            <span>{{ t('密码') }}</span>
            <span
              v-bk-tooltips="{
                disabled: hasAnyPermission,
                content: t('当前实例均无查看密码权限'),
              }"
              class="inline-block">
              <BkButton
                :disabled="!hasAnyPermission"
                text
                @click="handlePasswordShow">
                <DbIcon
                  class="header-view-icon ml-4"
                  type="visible1" />
              </BkButton>
            </span>
          </template>
          <template #default="{ row }">
            <TextOverflowLayout :key="Number(isRowPasswordShow(row))">
              <template #default>
                <span>{{ isRowPasswordShow(row) ? getRowPassword(row) : '******' }}</span>
              </template>
              <template #append>
                <AuthTemplate
                  :action-id="adminPwdViewActionMap[dbType]"
                  :permission="row.permission[adminPwdViewActionMap[dbType]]"
                  :resource="row.cluster_id">
                  <DbIcon
                    class="row-copy-icon ml-4"
                    type="copy"
                    @click="handleCopy(getRowPassword(row))" />
                  <DbIcon
                    class="row-view-icon ml-4"
                    type="visible1"
                    @click="handleToggleRowPassword(row)" />
                </AuthTemplate>
              </template>
            </TextOverflowLayout>
          </template>
        </TableColumn>
        <TableColumn
          col-key="immute_domain"
          ellipsis
          :title="t('所属集群')"
          :width="220">
          <template #default="{ row }">
            {{ row.immute_domain }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="lock_until"
          ellipsis
          :min-width="280"
          sorter
          :title="t('过期时间')">
          <template #default="{ row }">
            <span
              v-if="isExpiringSoon(row)"
              class="expired-time">
              {{ row.lockUntilDisplay }}（{{ t('n天后过期', { n: expireDays(row) }) }}）
            </span>
            <span v-else>{{ row.lockUntilDisplay }}</span>
          </template>
        </TableColumn>
        <TableColumn
          col-key="operator"
          :title="t('修改人')"
          :width="120">
        </TableColumn>
        <TableColumn
          col-key="update_time"
          ellipsis
          sorter
          :title="t('修改时间')"
          :width="260" />
      </DbTable>
    </div>
  </BkSideslider>
</template>

<script setup lang="tsx">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  import type { IRequestPayload } from '@services/http';
  import AdminPasswordModel from '@services/model/admin-password/admin-password';
  import { getInstancePassword, queryAdminPassword } from '@services/source/permission';

  import { DBTypes } from '@common/const';

  import DbTable from '@components/db-table/IndexNew.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { execCopy, getSearchSelectorParams, messageWarn } from '@utils';

  const isShow = defineModel<boolean>({ default: false, required: true });
  const dbType = defineModel<DBTypes>('dbType', { default: DBTypes.MYSQL });

  const { t } = useI18n();
  const tableMaxHeight = useTableMaxHeight(OccupiedInnerHeight.NOT_PAGINATION);
  const tableRef = ref();

  // 全量列表缓存（打开侧滑时拉取，前端分页 / 排序；密码按需拉取）
  const allData = ref<AdminPasswordModel[]>([]);
  let currentCacheKey = '';

  // 行级 / 表头共用：已展开密码的行 uniqueKey 集合 + 按需拉取的密码缓存
  const passwordShowRows = shallowRef(new Set<string>());
  const instancePasswordMap = shallowRef<Record<string, string>>({});
  const selected = shallowRef<AdminPasswordModel[]>([]);

  const searchParams = reactive({
    keys: [],
    time: ['', ''] as [string, string],
  });

  const hasSelected = computed(() => selected.value.length > 0);

  // 是否至少有一行有查看密码权限，全无权限时表头眼睛禁用
  const hasAnyPermission = computed(() => {
    const actionId = adminPwdViewActionMap[dbType.value];
    return allData.value.some((r) => r.permission[actionId]);
  });

  // 查看临时密码权限 action（按 DB 类型拆分，原 admin_pwd_view 已废弃）
  const adminPwdViewActionMap: Record<string, keyof AdminPasswordModel['permission']> = {
    [DBTypes.MYSQL]: 'mysql_admin_pwd_view',
    [DBTypes.SQLSERVER]: 'sqlserver_admin_pwd_view',
    [DBTypes.TENDBCLUSTER]: 'tendbcluster_admin_pwd_view',
  };

  const searchSelectData = [{ id: 'instances', name: t('IP 或 IP:Port') }];

  // 表格数据源：缓存命中时前端分页 / 排序，未命中时全量拉取列表
  const dataSource = async (params: Record<string, any>, payload?: IRequestPayload) => {
    const { limit: _limit, offset: _offset, ordering, ...rest } = params;
    const cacheKey = JSON.stringify({ ...rest, db_type: dbType.value });

    if (cacheKey !== currentCacheKey) {
      currentCacheKey = cacheKey;
      const res = await queryAdminPassword(
        { ...rest, bk_biz_id: window.PROJECT_CONFIG.BIZ_ID, db_type: dbType.value, limit: -1 },
        { ...payload, permission: 'catch' },
      );
      allData.value = res.results;
    }

    let data = allData.value;
    if (ordering) {
      const isDesc = ordering.startsWith('-');
      const field = isDesc ? ordering.slice(1) : ordering;
      data = [...data].sort((a, b) => {
        const va = (a as any)[field] ?? '';
        const vb = (b as any)[field] ?? '';
        return isDesc ? (va < vb ? 1 : va > vb ? -1 : 0) : va < vb ? -1 : va > vb ? 1 : 0;
      });
    }

    const offset = _offset ?? 0;
    const limit = _limit === -1 ? data.length : (_limit ?? 10);
    return {
      count: data.length,
      next: '',
      permission: {},
      previous: '',
      results: data.slice(offset, offset + limit),
    };
  };

  const getRowPassword = (row: AdminPasswordModel) => instancePasswordMap.value[row.uniqueKey];
  const isRowPasswordShow = (row: AdminPasswordModel) => passwordShowRows.value.has(row.uniqueKey);

  // 行级眼睛：切换单行密码显隐，首次展开时按需拉取
  const handleToggleRowPassword = async (row: AdminPasswordModel) => {
    const set = new Set(passwordShowRows.value);
    if (set.has(row.uniqueKey)) {
      set.delete(row.uniqueKey);
      passwordShowRows.value = set;
      return;
    }
    if (!instancePasswordMap.value[row.uniqueKey]) {
      const { results } = await getInstancePassword({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        db_type: dbType.value,
        instances: [{ cluster_id: row.cluster_id, ip: row.ip, port: row.port }],
      });
      if (results[0]?.password) {
        instancePasswordMap.value = { ...instancePasswordMap.value, [row.uniqueKey]: results[0].password };
      }
    }
    set.add(row.uniqueKey);
    passwordShowRows.value = set;
  };

  // 表头眼睛：批量切换有权限行显隐，首次开启时批量拉取密码
  const handlePasswordShow = async () => {
    const actionId = adminPwdViewActionMap[dbType.value];
    const hasPermissionRows = allData.value.filter((r) => r.permission[actionId]);
    const noPermissionRows = allData.value.filter((r) => !r.permission[actionId]);

    // 全部已展开 → 批量隐藏（保留无权限行中被行级单独展开的）
    if (hasPermissionRows.every((r) => passwordShowRows.value.has(r.uniqueKey))) {
      const set = new Set<string>();
      noPermissionRows.forEach((r) => {
        if (passwordShowRows.value.has(r.uniqueKey)) set.add(r.uniqueKey);
      });
      passwordShowRows.value = set;
      return;
    }

    if (noPermissionRows.length > 0) {
      messageWarn(
        t('已显示n条_另有m条无查看权限_请在对应行申请', { m: noPermissionRows.length, n: hasPermissionRows.length }),
      );
    }

    const set = new Set(passwordShowRows.value);
    hasPermissionRows.forEach((r) => set.add(r.uniqueKey));
    passwordShowRows.value = set;

    // 首次开启时拉取尚未获取的密码
    const rowsToFetch = hasPermissionRows.filter((r) => !instancePasswordMap.value[r.uniqueKey]);
    if (rowsToFetch.length === 0) return;

    const { results } = await getInstancePassword({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      db_type: dbType.value,
      instances: rowsToFetch.map((r) => ({ cluster_id: r.cluster_id, ip: r.ip, port: r.port })),
    });
    const newMap = { ...instancePasswordMap.value };
    results.forEach((item) => {
      if (item.password) newMap[`${item.bk_cloud_id}:${item.ip}:${item.port}`] = item.password;
    });
    instancePasswordMap.value = newMap;
  };

  const fetchData = () => {
    const params = { ...getSearchSelectorParams(searchParams.keys) };
    if (searchParams.time.length) {
      const [beginTime, endTime] = searchParams.time;
      if (beginTime && endTime) {
        Object.assign(params, {
          begin_time: dayjs(beginTime).format('YYYY-MM-DD HH:mm:ss'),
          end_time: dayjs(endTime).format('YYYY-MM-DD HH:mm:ss'),
        });
      }
    }
    tableRef.value?.fetchData(params);
  };

  const expireDays = (row: AdminPasswordModel) =>
    dayjs(dayjs(row.lock_until).format('YYYY-MM-DD')).diff(dayjs().format('YYYY-MM-DD'), 'day');
  const isExpiringSoon = (row: AdminPasswordModel) => expireDays(row) <= 7;

  const handleSelection = (_key: string[], list: AdminPasswordModel[]) => {
    selected.value = list;
  };

  const handleInstancesCopy = () => {
    const instances = selected.value.map((r) => `${r.ip}:${r.port}`);
    execCopy(instances.join('\n'), t('复制成功，共n条', { n: instances.length }));
  };

  const handleCopy = (val: string) => execCopy(val, t('复制成功，共n条', { n: 1 }));
</script>

<style lang="less" scoped>
  .temporary-password-modify-instance-box {
    padding: 16px 24px;

    .operate-area {
      display: flex;
      margin-top: 18px;
      margin-bottom: 16px;

      .search-select {
        flex: 1;
      }
    }

    // 行级 icon 默认隐藏，hover 行时显示
    :deep(.row-copy-icon),
    :deep(.row-view-icon) {
      display: none;
    }

    // 所有密码 icon 共用 hover 变蓝样式（表头 + 行级）
    :deep(.row-copy-icon),
    :deep(.row-view-icon),
    :deep(.header-view-icon) {
      cursor: pointer;
      color: #979ba5;

      &:hover {
        color: #3a84ff;
      }
    }

    // 表头眼睛禁用态
    :deep(.bk-button.is-disabled .header-view-icon) {
      color: #c4c6cc;
      cursor: not-allowed;

      &:hover {
        color: #c4c6cc;
      }
    }

    :deep(.temporary-password-modify-instance-box-table-row) {
      &:hover {
        .row-copy-icon,
        .row-view-icon {
          display: inline;
        }
      }
    }

    :deep(.expired-time) {
      color: @warning-color;
    }
  }
</style>
