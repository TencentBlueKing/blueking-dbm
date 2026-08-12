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
  <DbSideslider
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
        :max-height="tableMaxHeight"
        :pagination-extra="{
          small: true,
        }"
        :releate-url-query="false"
        row-class-name="temporary-password-modify-instance-box-table-row"
        row-key="uniqueKey"
        selectable
        @clear-search="fetchData"
        @selection="handleSelection">
        <TableColumn
          col-key="bk_cloud_name"
          :title="t('云区域')"
          :width="100">
        </TableColumn>
        <TableColumn
          col-key="instance"
          :title="t('实例')"
          :width="150">
          <template #default="{ row: data }: { row: AdminPasswordModel }">
            <TextOverflowLayout>
              {{ `${data.ip}:${data.port}` }}
              <template #append>
                <BkButton
                  text
                  theme="primary"
                  @click="handleCopy(`${data.ip}:${data.port}`)">
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
          :width="200">
          <template #title>
            <span>{{ t('密码') }}</span>
            <BkButton
              text
              @click="handlePasswordShow">
              <DbIcon type="visible1 ml-4" />
            </BkButton>
          </template>
          <template #default="{ row: data }: { row: AdminPasswordModel }">
            <TextOverflowLayout :key="Number(isRowPasswordShow(data))">
              <span>{{ isRowPasswordShow(data) ? getRowPassword(data) : '******' }}</span>
              <template #append>
                <AuthTemplate
                  :action-id="adminPwdViewActionMap[dbType]"
                  :permission="data.permission[adminPwdViewActionMap[dbType]]"
                  :resource="data.cluster_id">
                  <DbIcon
                    class="row-copy-icon ml-4"
                    type="copy"
                    @click="handleCopy(getRowPassword(data))" />
                  <DbIcon
                    class="row-view-icon ml-4"
                    type="visible1"
                    @click="handleToggleRowPassword(data)" />
                </AuthTemplate>
              </template>
            </TextOverflowLayout>
          </template>
        </TableColumn>
        <TableColumn
          col-key="immute_domain"
          :title="t('所属集群')"
          :width="100">
          <template #default="{ row }">
            {{ row.immute_domain }}
          </template>
        </TableColumn>
        <TableColumn
          col-key="lock_until"
          :min-width="280"
          sorter
          :title="t('过期时间')">
          <template #default="{ row: data }: { row: AdminPasswordModel }">
            <span
              v-if="isExpiringSoon(data)"
              class="expired-time">
              {{ data.lockUntilDisplay }}（{{ t('n天后过期', [expireDays(data)]) }}）
            </span>
            <span v-else>{{ data.lockUntilDisplay }}</span>
          </template>
        </TableColumn>
        <TableColumn
          col-key="operator"
          :title="t('修改人')"
          :width="150">
        </TableColumn>
        <TableColumn
          col-key="update_time"
          sorter
          :title="t('修改时间')"
          :width="160">
          <template #default="{ row: data }: { row: AdminPasswordModel }">
            {{ data.updateTimeDisplay }}
          </template>
        </TableColumn>
      </DbTable>
    </div>
  </DbSideslider>
</template>

<script setup lang="tsx">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  import type { IRequestPayload } from '@services/http';
  import AdminPasswordModel from '@services/model/admin-password/admin-password';
  import { getInstancePassword, queryAdminPassword } from '@services/source/permission';

  import { useTableMaxHeight } from '@hooks';

  import { DBTypes, OccupiedInnerHeight } from '@common/const';

  import DbTable from '@components/db-table/IndexNew.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { execCopy, getSearchSelectorParams, messageWarn } from '@utils';

  const isShow = defineModel<boolean>({
    default: false,
    required: true,
  });

  const dbType = defineModel<DBTypes>('dbType', {
    default: DBTypes.MYSQL,
  });

  // 不鉴权：无查看权限时静默失败，不弹权限申请框
  // 固定写入 bk_biz_id 与当前 db_type，保证首次加载 / 翻页 / 排序等由表格内部触发的请求也带上筛选条件
  const dataSource = (params: Record<string, any>, payload?: IRequestPayload) =>
    queryAdminPassword(
      {
        ...params,
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        db_type: dbType.value,
      },
      { ...payload, permission: 'catch' },
    );

  const { t } = useI18n();
  const tableMaxHeight = useTableMaxHeight(OccupiedInnerHeight.NOT_PAGINATION);

  const tableRef = ref();
  // 行级密码显隐：记录已展开密码的行 uniqueKey（表头批量与行级单行共用）
  const passwordShowRows = shallowRef(new Set<string>());
  // 通过 get_instance_password 接口实时拉取到的实例密码（uniqueKey -> password）
  const instancePasswordMap = shallowRef<Record<string, string>>({});
  const selected = shallowRef<AdminPasswordModel[]>([]);

  const searchParams = reactive({
    keys: [],
    time: ['', ''] as [string, string],
  });

  const hasSelected = computed(() => selected.value.length > 0);

  /**
   * 查看临时密码权限 action（按 DB 类型区分）
   *
   * 原业务级 admin_pwd_view 已废弃，查看权限按 DB 类型拆分为以下集群级 action：
   * - mysql_admin_pwd_view
   * - tendbcluster_admin_pwd_view
   * - sqlserver_admin_pwd_view
   */
  const adminPwdViewActionMap: Record<string, keyof AdminPasswordModel['permission']> = {
    [DBTypes.MYSQL]: 'mysql_admin_pwd_view',
    [DBTypes.SQLSERVER]: 'sqlserver_admin_pwd_view',
    [DBTypes.TENDBCLUSTER]: 'tendbcluster_admin_pwd_view',
  };

  const searchSelectData = [
    {
      id: 'instances',
      name: t('IP 或 IP:Port'),
    },
  ];

  // 仅组装搜索/时间筛选参数，db_type 与 bk_biz_id 由 dataSource 统一注入
  const fetchData = () => {
    const params = {
      ...getSearchSelectorParams(searchParams.keys),
    };

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

  const expireDays = (row: AdminPasswordModel) => {
    const lockUntilDate = dayjs(row.lock_until).format('YYYY-MM-DD');
    const currentDate = dayjs().format('YYYY-MM-DD');
    return dayjs(lockUntilDate).diff(currentDate, 'day');
  };

  const isExpiringSoon = (row: AdminPasswordModel) => expireDays(row) <= 7;

  // 密码展示/复制优先使用接口实时拉取的值，未拉取到则回退到列表字段
  const getRowPassword = (row: AdminPasswordModel) => instancePasswordMap.value[row.uniqueKey];

  const isRowPasswordShow = (row: AdminPasswordModel) => passwordShowRows.value.has(row.uniqueKey);

  const handleToggleRowPassword = async (row: AdminPasswordModel) => {
    const set = new Set(passwordShowRows.value);
    if (set.has(row.uniqueKey)) {
      set.delete(row.uniqueKey);
      passwordShowRows.value = set;
      return;
    }
    // 未获取过该实例密码时，通过接口实时拉取
    if (!instancePasswordMap.value[row.uniqueKey]) {
      const { results } = await getInstancePassword({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        db_type: dbType.value,
        instances: [
          {
            cluster_id: row.cluster_id,
            ip: row.ip,
            port: row.port,
          },
        ],
      });
      const item = results[0];
      if (item?.password) {
        instancePasswordMap.value = {
          ...instancePasswordMap.value,
          [row.uniqueKey]: item.password,
        };
      }
    }
    set.add(row.uniqueKey);
    passwordShowRows.value = set;
  };

  const handlePasswordShow = async () => {
    const actionId = adminPwdViewActionMap[dbType.value];
    const fullList = (await tableRef.value?.fetchAllData()) ?? [];
    const noPermissionRows = fullList.filter((row: AdminPasswordModel) => !row.permission[actionId]);
    const hasPermissionRows = fullList.filter((row: AdminPasswordModel) => row.permission[actionId]);

    // 判断当前是否已全部展开（即表头处于"显示"状态），是则批量隐藏
    const allShown = hasPermissionRows.every((row: AdminPasswordModel) => passwordShowRows.value.has(row.uniqueKey));
    if (allShown) {
      const set = new Set<string>();
      // 保留无权限行中已被行级眼睛单独展开的行
      noPermissionRows.forEach((row: AdminPasswordModel) => {
        if (passwordShowRows.value.has(row.uniqueKey)) set.add(row.uniqueKey);
      });
      passwordShowRows.value = set;
      return;
    }

    // 批量显示有权限行
    if (noPermissionRows.length > 0) {
      messageWarn(
        t('已显示n条_另有m条无查看权限_请在对应行申请', { m: noPermissionRows.length, n: hasPermissionRows.length }),
      );
    }
    const set = new Set(passwordShowRows.value);
    hasPermissionRows.forEach((row: AdminPasswordModel) => set.add(row.uniqueKey));
    passwordShowRows.value = set;

    // 仅首次开启时批量拉取有权限行尚未获取的密码
    const rowsToFetch = hasPermissionRows.filter(
      (row: AdminPasswordModel) => !instancePasswordMap.value[row.uniqueKey],
    );
    if (rowsToFetch.length > 0) {
      const { results } = await getInstancePassword({
        bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        db_type: dbType.value,
        instances: rowsToFetch.map((row: AdminPasswordModel) => ({
          cluster_id: row.cluster_id,
          ip: row.ip,
          port: row.port,
        })),
      });
      const newMap = { ...instancePasswordMap.value };
      results.forEach((item) => {
        const key = `${item.bk_cloud_id}:${item.ip}:${item.port}`;
        if (item.password) {
          newMap[key] = item.password;
        }
      });
      instancePasswordMap.value = newMap;
    }
  };

  const handleSelection = (_key: string[], list: AdminPasswordModel[]) => {
    selected.value = list;
  };

  const handleInstancesCopy = () => {
    const instances = selected.value.map((row) => `${row.ip}:${row.port}`);
    execCopy(instances.join('\n'), t('复制成功，共n条', { n: instances.length }));
  };

  const handleCopy = (val: string) => {
    execCopy(val, t('复制成功，共n条', { n: 1 }));
  };
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

    :deep(.row-copy-icon),
    :deep(.row-view-icon) {
      display: none;
      color: #979ba5;
      cursor: pointer;

      &:hover {
        color: #3a84ff;
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

    :deep(.row-copy-icon),
    :deep(.row-view-icon) {
      cursor: pointer;
      color: #979ba5;

      &:hover {
        color: #3a84ff;
      }
    }

    :deep(.expired-time) {
      color: @warning-color;
    }
  }
</style>
