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
    :title="t('临时密码生效的实例')"
    :width="1200"
    @closed="isShow = false">
    <div class="temporary-password-modify-instance-box">
      <BkRadioGroup
        v-model="dbType"
        @change="handleDbTypeChange">
        <BkRadioButton
          class="w-88"
          :label="DBTypes.MYSQL">
          Mysql
        </BkRadioButton>
        <BkRadioButton
          class="w-88"
          :label="DBTypes.TENDBCLUSTER">
          Tendb Cluster
        </BkRadioButton>
        <BkRadioButton
          class="w-88"
          :label="DBTypes.SQLSERVER">
          Sql Server
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
          @change="handleSearchValueChange" />
        <DbSearchSelect
          v-model="searchParams.keys"
          class="ml-8 search-select"
          :data="searchSelectData"
          :placeholder="t('请输入实例搜索')"
          @change="handleSearchValueChange" />
      </div>
      <DbTable
        ref="tableRef"
        :data-source="queryAdminPassword"
        :max-height="tableMaxHeight"
        :pagination-extra="{
          small: true,
        }"
        :releate-url-query="false"
        row-class-name="temporary-password-modify-instance-box-table-row"
        row-key="uniqueKey"
        selectable
        @clear-search="getDataSource"
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
            <TextOverflowLayout :key="Number(passwordShow)">
              <span>{{ passwordShow ? data.password : '******' }}</span>
              <template #append>
                <BkButton
                  text
                  theme="primary"
                  @click="handleCopy(data.password)">
                  <DbIcon
                    class="row-copy-icon ml-4"
                    type="copy" />
                </BkButton>
              </template>
            </TextOverflowLayout>
          </template>
        </TableColumn>
        <TableColumn
          col-key="component"
          :title="t('DB类型')"
          :width="100">
          <template #default="{ row: data }: { row: AdminPasswordModel }">
            <DbIcon type="mysql row-type" />
            <span class="ml-4">{{ data.component }}</span>
          </template>
        </TableColumn>
        <TableColumn
          col-key="lock_until"
          ellipsis
          :min-width="240"
          sorter
          :title="t('过期时间')">
          <template #default="{ row: data }: { row: AdminPasswordModel }">
            <span
              v-if="isExpireSoon(data.lock_until)"
              class="expired-time">
              {{ data.lockUntilDisplay }}（{{ t('n天后过期', [getExpireDays(data.lock_until)]) }}）
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
  </BkSideslider>
</template>

<script setup lang="tsx">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  import AdminPasswordModel from '@services/model/admin-password/admin-password';
  import { queryAdminPassword } from '@services/source/permission';

  import { useTableMaxHeight } from '@hooks';

  import { DBTypes, OccupiedInnerHeight } from '@common/const';

  import DbTable from '@components/db-table/IndexNew.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { execCopy, getSearchSelectorParams } from '@utils';

  const isShow = defineModel<boolean>({
    default: false,
    required: true,
  });

  const { t } = useI18n();
  const tableMaxHeight = useTableMaxHeight(OccupiedInnerHeight.NOT_PAGINATION);

  const searchSelectData = [
    {
      id: 'instances',
      name: t('IP 或 IP:Port'),
    },
  ];

  const tableRef = ref();
  const dbType = ref(DBTypes.MYSQL);
  const passwordShow = ref(false);
  const selected = shallowRef<AdminPasswordModel[]>([]);

  const searchParams = reactive({
    keys: [],
    time: ['', ''] as [string, string],
  });

  const hasSelected = computed(() => selected.value.length > 0);

  const handleSearchValueChange = () => {
    // tableRef.value!.clearSelected();
    getDataSource();
  };

  const getDataSource = () => {
    const keys = getSearchSelectorParams(searchParams.keys);
    const params = {
      ...keys,
      db_type: dbType.value,
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

  const isExpireSoon = (lockUntil: string) => {
    const lockUntilDate = dayjs(lockUntil).format('YYYY-MM-DD');
    const currentDate = dayjs().format('YYYY-MM-DD');
    return dayjs(lockUntilDate).diff(currentDate, 'day') <= 7;
  };

  const getExpireDays = (lockUntil: string) => {
    const lockUntilDate = dayjs(lockUntil).format('YYYY-MM-DD');
    const currentDate = dayjs().format('YYYY-MM-DD');
    return Math.ceil(dayjs(lockUntilDate).diff(currentDate, 'day'));
  };

  const handlePasswordShow = () => {
    passwordShow.value = !passwordShow.value;
  };

  const handleSelection = (idList: string[], list: AdminPasswordModel[]) => {
    selected.value = list;
  };

  const handleInstancesCopy = () => {
    const instances = selected.value.map((row) => `${row.ip}:${row.port}`);
    execCopy(instances.join('\n'), t('复制成功，共n条', { n: instances.length }));
  };

  const handleCopy = (val: string) => {
    execCopy(val, t('复制成功，共n条', { n: 1 }));
  };

  const handleDbTypeChange = () => {
    getDataSource();
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

    :deep(.row-copy-icon) {
      display: none;
    }

    :deep(.temporary-password-modify-instance-box-table-row) {
      &:hover {
        .row-copy-icon {
          display: inline;
        }
      }
    }

    :deep(.row-type) {
      font-size: 16px;
    }

    :deep(.expired-time) {
      color: @warning-color;
    }
  }
</style>
