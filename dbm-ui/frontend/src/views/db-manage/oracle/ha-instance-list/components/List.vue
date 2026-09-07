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
  <div class="oracle-ha-instance-list-page">
    <div class="operation-box mb-12">
      <DbQuickSearch
        v-model="searchValue"
        :data="searchSelectData"
        parse-url
        :placeholder="t('请输入或选择条件搜索')"
        @change="handleSearchValueChange" />
    </div>
    <DbTable
      ref="tableRef"
      :bk-ui-settings="settings"
      :data-source="getOracleHaInstanceList"
      releate-url-query
      :row-class-name="setRowClass"
      row-key="id"
      @bk-ui-settings-change="updateTableSettings"
      @clear-search="clearSearchValue">
      <TableColumn
        col-key="id"
        fixed="left"
        title="ID"
        :width="80">
      </TableColumn>
      <TableColumn
        col-key="instance_address"
        fixed="left"
        :min-width="200"
        :title="t('实例')">
        <template #default="{ row: data }: { row: OraclehaInstanceModel }">
          <TextOverflowLayout>
            <AuthButton
              action-id="oracle_view"
              :permission="data.permission.oracle_view"
              :resource="data.cluster_id"
              text
              theme="primary"
              @click="() => handleToDetails(data)">
              {{ data.instance_address }}
            </AuthButton>
            <template #append>
              <BkTag
                v-if="data.isNew"
                class="ml-4"
                size="small"
                theme="success">
                NEW
              </BkTag>
            </template>
          </TextOverflowLayout>
        </template>
      </TableColumn>
      <TableColumn
        col-key="status"
        :title="t('状态')"
        :width="140">
        <template #default="{ row: data }: { row: OraclehaInstanceModel }">
          <ClusterInstanceStatus :data="data.status" />
        </template>
      </TableColumn>
      <TableColumn
        col-key="role"
        :title="t('部署角色')"
        :width="140">
      </TableColumn>
      <TableColumn
        col-key="bk_sub_zone"
        :title="t('所在园区')"
        :width="140">
        <template #default="{ row: data }: { row: OraclehaInstanceModel }">
          {{ data.bk_sub_zone || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="master_domain"
        :min-width="250"
        :title="t('所属集群')">
        <template #default="{ row: data }: { row: OraclehaInstanceModel }">
          <TextOverflowLayout>
            {{ data.master_domain }}
            <template #append>
              <DbIcon
                v-bk-tooltips="t('复制所属集群')"
                class="copy-btn"
                type="copy"
                @click="() => execCopy(data.master_domain, t('复制成功，共n条', { n: 1 }))" />
            </template>
          </TextOverflowLayout>
        </template>
      </TableColumn>
      <TableColumn
        col-key="cluster_name"
        :min-width="180"
        :title="t('集群名称')">
        <template #default="{ row: data }: { row: OraclehaInstanceModel }">
          <TextOverflowLayout>
            <AuthButton
              action-id="oracle_view"
              :permission="data.permission.oracle_view"
              :resource="data.cluster_id"
              text
              theme="primary"
              @click="() => handleToClusterDetails(data)">
              {{ data.cluster_name }}
            </AuthButton>
            <template #append>
              <DbIcon
                v-bk-tooltips="t('复制集群名称')"
                class="copy-btn"
                type="copy"
                @click="() => execCopy(data.cluster_name, t('复制成功，共n条', { n: 1 }))" />
            </template>
          </TextOverflowLayout>
        </template>
      </TableColumn>
      <TableColumn
        col-key="create_at"
        :title="t('部署时间')"
        :width="240">
        <template #default="{ row: data }: { row: OraclehaInstanceModel }">
          {{ data.createAtDisplay || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        v-if="!isStretchLayoutOpen"
        col-key="row-operation"
        fixed="right"
        :title="t('操作')"
        :width="100">
        <template #default="{ row: data }: { row: OraclehaInstanceModel }">
          <AuthButton
            action-id="oracle_view"
            :permission="data.permission.oracle_view"
            :resource="data.cluster_id"
            text
            theme="primary"
            @click="() => handleToDetails(data)">
            {{ t('查看详情') }}
          </AuthButton>
        </template>
      </TableColumn>
    </DbTable>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import OraclehaInstanceModel from '@services/model/oracle/oracle-ha-instance';
  import { queryBizClusterAttrs } from '@services/source/dbbase';
  import { getOracleHaInstanceList } from '@services/source/oracleHaCluster';

  import { useStretchLayout, useTableSettings } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, UserPersonalSettings } from '@common/const';
  import { ipPort, ipv4 } from '@common/regex';

  import ClusterInstanceStatus from '@components/cluster-instance-status/Index.vue';
  import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';
  import DbTable from '@components/db-table/IndexNew.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import { execCopy } from '@utils';

  const instanceData = defineModel<{ clusterId: number; instanceAddress: string }>('instanceData');

  let isInit = true;
  const fetchData = (loading?: boolean) => {
    tableRef.value.fetchData(searchValue.value, loading);
    isInit = false;
  };

  const router = useRouter();
  const { t } = useI18n();
  const { isOpen: isStretchLayoutOpen, splitScreen: stretchLayoutSplitScreen } = useStretchLayout();
  const { currentBizId } = useGlobalBizs();

  const searchValue = ref<Record<string, string>>({});

  const searchSelectData = computed(
    () =>
      [
        {
          id: 'instance',
          name: t('IP 或 IP:Port'),
          type: 'multiple-input',
          validator: (value: string) => ipPort.test(value) || ipv4.test(value) || t('格式错误'),
        },
        {
          id: 'domain',
          name: t('访问入口'),
          type: 'multiple-input',
        },
        {
          id: 'name',
          name: t('集群名称'),
        },
        {
          id: 'status',
          list: [
            {
              label: t('正常'),
              value: 'running',
            },
            {
              label: t('异常'),
              value: 'unavailable',
            },
            {
              label: t('重建中'),
              value: 'loading',
            },
          ],
          name: t('状态'),
          type: 'multiple',
        },
        {
          id: 'role',
          name: t('部署角色'),
          remoteMethod: () =>
            queryBizClusterAttrs({
              bk_biz_id: currentBizId,
              cluster_type: ClusterTypes.ORACLE_PRIMARY_STANDBY,
              instances_attrs: 'role',
            }).then((data) =>
              data.role.map((item) => ({
                label: item.text,
                value: item.value,
              })),
            ),
          type: 'multiple',
        },
        {
          id: 'port',
          name: t('端口'),
        },
      ] as QuickSearchProps['data'],
  );

  const tableRef = ref();

  onMounted(() => {
    fetchData(isInit);
  });

  const handleSearchValueChange = () => {
    fetchData();
  };

  const clearSearchValue = () => {
    searchValue.value = {};
    fetchData();
  };

  // 设置行样式
  const setRowClass = ({ row }: { row: OraclehaInstanceModel }) => {
    const classList = [row.isNew ? 'is-new-row' : ''];

    if (
      row.cluster_id === instanceData.value?.clusterId &&
      row.instance_address === instanceData.value.instanceAddress
    ) {
      classList.push('is-selected-row');
    }

    return classList.filter((cls) => cls).join(' ');
  };

  const { settings, updateTableSettings } = useTableSettings(UserPersonalSettings.ORACLE_HA_INSTANCE_SETTINGS, {
    checked: ['id', 'instance_address', 'status', 'role', 'bk_sub_zone', 'master_domain', 'cluster_name', 'create_at'],
    disabled: ['instance_address', 'master_domain'],
  });

  /**
   * 查看实例详情
   */
  const handleToDetails = (data: OraclehaInstanceModel) => {
    stretchLayoutSplitScreen();
    instanceData.value = {
      clusterId: data.cluster_id,
      instanceAddress: data.instance_address,
    };
  };

  /**
   * 查看集群详情
   */
  const handleToClusterDetails = (data: OraclehaInstanceModel) => {
    router.push({
      name: 'OracleHaClusterList',
      query: {
        id: data.cluster_id,
      },
    });
  };
</script>

<style lang="less">
  @import '@styles/mixins.less';

  .oracle-ha-instance-list-page {
    height: 100%;
    padding: 24px 0;
    margin: 0 24px;
    overflow: hidden;

    .t-table__cell {
      .copy-btn {
        display: none;
        margin-left: 4px;
        color: @primary-color;
        cursor: pointer;
      }
    }

    tr:hover {
      .copy-btn {
        display: inline-block !important;
      }
    }

    .operation-box {
      display: flex;
      flex-wrap: wrap;

      .bk-quick-search {
        flex: 1;
        max-width: 500px;
        min-width: 320px;
        margin-left: auto;
      }
    }
  }
</style>
