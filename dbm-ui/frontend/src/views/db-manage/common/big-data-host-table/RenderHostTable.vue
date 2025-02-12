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
    class="big-data-host-table">
    <div class="search-box">
      <BkInput
        v-model="searchKey"
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
            <span v-else>{{ $t('共') }}</span>
            <span class="ip-num">{{ serachList.length }}</span>
            {{ $t('台') }}
          </span>
        </div>
        <BkDropdown @click.stop>
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
          <DbOriginalTable
            :columns="columns"
            :data="serachList"
            :is-searching="!!searchKey"
            :pagination="pagination"
            :settings="tableSetting"
            @clear-search="handleClearSearch"
            @page-limit-change="handlePaginationLimitChange"
            @page-value-change="handlePaginationCurrentChange" />
        </BkLoading>
      </Transition>
    </div>
  </div>
</template>
<script setup lang="tsx">
  import {
    ref,
    shallowRef,
    watch,
  } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { HostInfo } from '@services/types';

  import DbStatus from '@components/db-status/index.vue';

  import { execCopy } from '@utils';

  import tableSetting from './common/tableSetting';
  import useLocalPagination from './hook/useLocalPagination';

  interface Props {
    data: Array<HostInfo>
  }

  interface Emits {
    (e: 'update:data', value: Array<HostInfo>): void
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const isLoading = ref(false);
  const localData = shallowRef(props.data);
  const isShowTable = ref(true);

  const columns = [
    {
      label: 'IP',
      field: 'ip',
      width: 160,
      render: ({ data }: {data: HostInfo}) => data.ip,
    },
    {
      label: t('机型'),
      field: 'bk_cpu',
      render: ({ data }: {data: HostInfo}) => data.bk_cpu || '--',
    },
    {
      label: t('机房'),
      field: 'bk_idc_name',
      render: ({ data }: {data: HostInfo}) => data.bk_idc_name || '--',
    },
    {
      label: t('主机名称'),
      field: 'host_name',
      render: ({ data }: {data: HostInfo}) => data.host_name || '--',
    },
    {
      label: t('Agent状态'),
      field: 'alive',
      render: ({ data }: {data: HostInfo}) => {
        const info = data.alive === 1 ? { theme: 'success', text: t('正常') } : { theme: 'danger', text: t('异常') };
        return <DbStatus theme={info.theme}>{info.text}</DbStatus>;
      },
    },
    {
      label: t('管控区域'),
      field: 'cloud_area',
      render: ({ data }: {data: HostInfo}) => data.cloud_area.name || '--',
    },
    {
      label: t('OS名称'),
      field: 'os_name',
      render: ({ data }: {data: HostInfo}) => data.os_name || '--',
    },
    {
      label: t('OS类型'),
      field: 'os_type',
      render: ({ data }: {data: HostInfo}) => data.os_type || '--',
    },
    {
      label: t('主机ID'),
      field: 'host_id',
      render: ({ data }: {data: HostInfo}) => data.host_id || '--',
    },
    {
      label: 'Agent ID',
      field: 'agent_id',
      render: ({ data }: {data: HostInfo}) => data.agent_id || '--',
    },
    {
      label: t('操作'),
      field: 'operation',
      width: 100,
      render: ({ data }: {data: HostInfo}) => (
        <bk-button
          text
          theme="primary"
          onClick={() => handleRemove(data)}>
          { t('删除') }
        </bk-button>
      ),
    },
  ];

  watch(() => props.data, () => {
    localData.value = props.data;
  });

  const {
    searchKey,
    pagination,
    serachList,
    handlePaginationCurrentChange,
    handlePaginationLimitChange,
  } = useLocalPagination(localData);

  const handleClearSearch = () => {
    searchKey.value = '';
  };

  const handleToggleShowTable = () => {
    isShowTable.value = !isShowTable.value;
  };

  // 移除指定主机节点数
  const handleRemove = (data: HostInfo) => {
    const result = props.data.reduce((result, item) => {
      if (item.host_id !== data.host_id) {
        result.push(item);
      }
      return result;
    }, [] as Array<HostInfo>);
    emits('update:data', result);
  };

  // 清空所有主机
  const handleClearAll = () => {
    const searchHostIdMap = serachList.value.reduce((result, hostData) => ({
      ...result,
      [hostData.host_id]: true,
    }), {} as Record<number, boolean>);

    const result = props.data.reduce((result, hostData) => {
      if (!searchHostIdMap[hostData.host_id]) {
        result.push(hostData);
      }
      return result;
    }, [] as Array<HostInfo>);
    emits('update:data', result);
  };

  // 清空异常主机
  const handleClearAbnormal = () => {
    const searchHostIdMap = serachList.value.reduce((result, hostData) => {
      if (!hostData.alive) {
        return {
          ...result,
          [hostData.host_id]: true,
        };
      }
      return result;
    }, {} as Record<number, boolean>);

    const result = props.data.reduce((result, hostData) => {
      if (!searchHostIdMap[hostData.host_id]) {
        result.push(hostData);
      }
      return result;
    }, [] as Array<HostInfo>);
    emits('update:data', result);
  };

  // 复制所有主机IP
  const handleCopyAll = () => {
    const ipList = serachList.value.map(_ => _.ip);
    execCopy(ipList.join('\n'), t('复制成功，共n条', { n: ipList.length }));
  };

  // 复制异常主机IP
  const handleCopyAbnormal = () => {
    const abnormalList = serachList.value.reduce((result, item) => {
      if (!item.alive) {
        result.push(item.ip);
      }
      return result;
    }, [] as Array<string>);
    execCopy(abnormalList.join('\n'), t('复制成功，共n条', { n: abnormalList.length }));
  };
</script>
<style lang="less" scoped>
  .big-data-host-table {
    display: block;
    margin-top: 15px;

    .search-box {
      display: flex;
      margin-top: -48px;
      margin-bottom: 16px;
    }

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

    :deep(.bk-table) {
      th {
        background-color: #f5f7fa !important;
      }
    }
  }
</style>
