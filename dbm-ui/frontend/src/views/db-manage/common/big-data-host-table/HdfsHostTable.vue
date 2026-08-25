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
  <div
    v-if="props.data.length > 0"
    class="big-data-hdfs-host-table">
    <div class="search-box">
      <BkInput
        v-model="searchKey"
        clearable
        :placeholder="$t('请输入IP')"
        style="width: 320px; margin-left: auto" />
    </div>
    <div>
      <div
        class="collapse-header"
        @click="handleToggleShowTable">
        <div class="header-text">
          <i class="db-icon-down-shape" />
          <span style="padding-left: 5px">
            <span v-if="searchKey">{{ $t('已筛选') }}</span>
            {{ $t('共') }}
            <span class="ip-num">{{ serachList.length }}</span>
            {{ $t('台') }}
          </span>
        </div>
        <BkDropdown
          :popover-options="{
            clickContentAutoHide: true,
          }"
          trigger="click"
          @click.stop>
          <div class="extends-action">
            <i class="db-icon-more" />
          </div>
          <template #content>
            <BkDropdownMenu>
              <BkDropdownItem @click="handleClearAll">
                {{ $t('清除所有') }}
              </BkDropdownItem>
              <BkDropdownItem @click="handleClearAbnormal">
                {{ $t('清除异常IP') }}
              </BkDropdownItem>
              <BkDropdownItem @click="handleCopyAll">
                {{ $t('复制所有IP') }}
              </BkDropdownItem>
              <BkDropdownItem @click="handleCopyAbnormal">
                {{ $t('复制异常IP') }}
              </BkDropdownItem>
            </BkDropdownMenu>
          </template>
        </BkDropdown>
      </div>
      <Transition mode="in-out">
        <BkLoading
          v-show="isShowTable"
          :loading="isLoading">
          <PrimaryTable
            :bk-ui-settings="tableSetting"
            :columns="columns"
            :data="data"
            row-key="host_id">
            <template #empty>
              <EmptyStatus
                :is-anomalies="false"
                :is-searching="!!searchKey"
                @clear-search="handleClearSearch" />
            </template>
          </PrimaryTable>
          <div class="table-footer">
            <BkPagination
              v-bind="pagination"
              :layout="['total', 'limit', 'list']"
              :model-value="pagination.current"
              @change="handlePaginationCurrentChange"
              @limit-change="handlePaginationLimitChange" />
          </div>
        </BkLoading>
      </Transition>
    </div>
  </div>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import { Checkbox, type PrimaryTableCol } from 'tdesign-vue-next';
  import { computed, ref, shallowRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { HostInfo } from '@services/types';

  import DbStatus from '@components/db-status/index.vue';
  import EmptyStatus from '@components/empty-status/EmptyStatus.vue';

  import { execCopy } from '@utils';

  import tableSetting from './common/tableSetting';
  import useLocalPagination from './hook/useLocalPagination';

  interface Props {
    data: HostInfo[];
  }

  interface Emits {
    (e: 'update:data', value: Array<HostInfo>): void;
    (e: 'change', nameNode: Array<HostInfo>, zookeeper: Array<HostInfo>): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const isLoading = ref(false);
  const localData = shallowRef(props.data);
  const isShowTable = ref(true);

  const nameNodeCheckedMap = shallowRef<Record<number, HostInfo>>({});
  const zookeeperCheckedMap = shallowRef<Record<number, HostInfo>>({});

  // 部署 NameNodes 最多2台
  const isNameNodeCheckDisabled = computed(() => Object.keys(nameNodeCheckedMap.value).length >= 2);
  // 部署 Zookeepers / JournalNodes最多3台
  const isZookeeperCheckDisabled = computed(() => Object.keys(zookeeperCheckedMap.value).length >= 3);

  const columns: PrimaryTableCol[] = [
    {
      cell: (_, { row }) => row.host_id || '--',
      colKey: 'host_id',
      title: t('主机ID'),
    },
    {
      cell: (_, { row }) => row.ip,
      colKey: 'ip',
      title: 'IP',
    },
    {
      cell: (_, { row }) => {
        const isDisabled = isNameNodeCheckDisabled.value && !nameNodeCheckedMap.value[row.host_id];
        const tooltipsOptions = {
          content: t('最多只能选择两台'),
          disabled: !isDisabled,
        };
        return (
          <span
            key={row.host_id}
            v-bk-tooltips={tooltipsOptions}>
            <Checkbox
              checked={Boolean(nameNodeCheckedMap.value[row.host_id])}
              disabled={isDisabled}
              onChange={(value: boolean) => handleNameNodesChange(value, row as HostInfo)}
            />
          </span>
        );
      },
      colKey: 'deploy_name_node',
      title: t('部署NameNode_2台'),
      width: '180px',
    },
    {
      cell: (_, { row }) => {
        const isDisabled = isZookeeperCheckDisabled.value && !zookeeperCheckedMap.value[row.host_id];
        const tooltipsOptions = {
          content: t('最多只能选择三台'),
          disabled: !isDisabled,
        };
        return (
          <span
            key={row.host_id}
            v-bk-tooltips={tooltipsOptions}>
            <Checkbox
              checked={Boolean(zookeeperCheckedMap.value[row.host_id])}
              disabled={isDisabled}
              onChange={(value: boolean) => handleZookeeperChange(value, row as HostInfo)}
            />
          </span>
        );
      },
      colKey: 'deploy_zookeeper',
      title: t('部署Zookeeper_JournalNode_3台'),
      width: '250px',
    },
    {
      cell: (_, { row }) => row.bk_cpu || '--',
      colKey: 'bk_cpu',
      title: t('机型'),
    },
    {
      cell: (_, { row }) => row.bk_idc_name || '--',
      colKey: 'bk_idc_name',
      title: t('机房'),
    },
    {
      cell: (_, { row }) => row.host_name || '--',
      colKey: 'host_name',
      title: t('主机名称'),
    },
    {
      cell: (_, { row }) => {
        const info = row.alive === 1 ? { text: t('正常'), theme: 'success' } : { text: t('异常'), theme: 'danger' };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
      colKey: 'alive',
      title: t('Agent状态'),
    },
    {
      cell: (_, { row }) => row.cloud_area.name || '--',
      colKey: 'cloud_area',
      title: t('管控区域'),
    },
    {
      cell: (_, { row }) => row.os_name || '--',
      colKey: 'os_name',
      title: t('OS名称'),
    },
    {
      cell: (_, { row }) => row.os_type || '--',
      colKey: 'os_type',
      title: t('OS类型'),
    },
    {
      cell: (_, { row }) => row.agent_id || '--',
      colKey: 'agent_id',
      title: 'Agent ID',
    },
    {
      cell: (_, { rowIndex }) => (
        <bk-button
          text
          theme='primary'
          onClick={() => handleRemove(rowIndex)}>
          {t('删除')}
        </bk-button>
      ),
      colKey: 'row-operation',
      title: t('操作'),
      width: 100,
    },
  ];

  const triggerChange = () => {
    emits('change', Object.values(nameNodeCheckedMap.value), Object.values(zookeeperCheckedMap.value));
  };

  watch(
    () => props.data,
    () => {
      localData.value = props.data;

      const isEmpty =
        Object.keys(nameNodeCheckedMap.value).length < 1 && Object.keys(zookeeperCheckedMap.value).length < 1;

      const nameNodeChecked = {} as Record<number, HostInfo>;
      const zookeeperChecked = {} as Record<number, HostInfo>;

      if (isEmpty) {
        _.forEach(props.data, (item) => {
          if (Object.keys(nameNodeChecked).length >= 2) {
            return;
          }
          nameNodeChecked[item.host_id] = item;
        });
        _.forEachRight(props.data, (item) => {
          if (Object.keys(zookeeperChecked).length >= 3) {
            return;
          }
          zookeeperChecked[item.host_id] = item;
        });
      } else {
        props.data.forEach((item) => {
          const hostId = item.host_id;
          if (nameNodeCheckedMap.value[hostId]) {
            nameNodeChecked[hostId] = nameNodeCheckedMap.value[hostId];
          }
          if (zookeeperCheckedMap.value[hostId]) {
            zookeeperChecked[hostId] = zookeeperCheckedMap.value[hostId];
          }
        });
      }
      nameNodeCheckedMap.value = nameNodeChecked;
      zookeeperCheckedMap.value = zookeeperChecked;
      triggerChange();
    },
    {
      immediate: true,
    },
  );

  const { data, handlePaginationCurrentChange, handlePaginationLimitChange, pagination, searchKey, serachList } =
    useLocalPagination(localData);

  const handleClearSearch = () => {
    searchKey.value = '';
  };

  const handleToggleShowTable = () => {
    isShowTable.value = !isShowTable.value;
  };

  const handleNameNodesChange = (value: boolean, data: HostInfo) => {
    const checkedMap = { ...nameNodeCheckedMap.value };
    if (value) {
      checkedMap[data.host_id] = data;
    } else {
      delete checkedMap[data.host_id];
    }
    nameNodeCheckedMap.value = checkedMap;
    triggerChange();
  };

  const handleZookeeperChange = (value: boolean, data: HostInfo) => {
    const checkedMap = { ...zookeeperCheckedMap.value };
    if (value) {
      checkedMap[data.host_id] = data;
    } else {
      delete checkedMap[data.host_id];
    }
    zookeeperCheckedMap.value = checkedMap;
    triggerChange();
  };

  // 移除指定主机节点数
  const handleRemove = (index: number) => {
    const list = [...props.data];

    handleNameNodesChange(false, list[index]);
    handleZookeeperChange(false, list[index]);

    list.splice(index, 1);
    emits('update:data', list);
  };
  // 清空所有主机
  const handleClearAll = () => {
    nameNodeCheckedMap.value = {};
    zookeeperCheckedMap.value = {};
    triggerChange();
    emits('update:data', []);
  };
  // 清空异常主机
  const handleClearAbnormal = () => {
    const list = [...props.data];
    _.remove(list, (_) => !_.alive);
    triggerChange();
  };

  // 复制所有主机IP
  const handleCopyAll = () => {
    const ipList = props.data.map((_) => _.ip);
    execCopy(ipList.join('\n'), t('复制成功，共n条', { n: ipList.length }));
  };
  // 复制异常主机IP
  const handleCopyAbnormal = () => {
    const abnormalList = props.data.reduce((result, item) => {
      if (!item.alive) {
        result.push(item.ip);
      }
      return result;
    }, [] as Array<string>);
    execCopy(abnormalList.join('\n'), t('复制成功，共n条', { n: abnormalList.length }));
  };
</script>
<style lang="less" scoped>
  .big-data-hdfs-host-table {
    display: block;

    .collapse-header {
      display: flex;
      height: 42px;
      padding-right: 12px;
      padding-left: 18px;
      font-size: 12px;
      color: #63656e;
      cursor: pointer;
      background: #f0f1f5;
      align-items: center;

      .header-text {
        margin-right: auto;
      }

      .ip-num {
        padding: 0 2px;
        font-weight: bold;
        color: #3a84ff;
      }

      .extends-action {
        display: flex;
        width: 20px;
        height: 20px;
        margin-left: auto;
        font-size: 20px;
        align-items: center;
        justify-content: center;
        border-radius: 2px;

        &:hover {
          color: #3a84ff;
          background: #e1ecff;
        }
      }
    }

    .search-box {
      display: flex;
      margin-top: -32px;
      margin-bottom: 16px;
      justify-content: flex-end;
    }

    :deep(.t-table__header) {
      th {
        background-color: #f5f7fa;
      }
    }

    .table-footer {
      display: flex;
      justify-content: flex-end;
      margin-top: 12px;
    }
  }
</style>
