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
  <DbOriginalTable
    :cell-class="setCellClass"
    class="preview-table"
    :columns="columns"
    :data="data"
    :max-height="maxHeight"
    v-bind="$attrs" />
</template>

<script setup lang="tsx">
  import type { Table } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';

  type TableProps = InstanceType<typeof Table>['$props'];

  interface HostInfo {
    bk_cloud_id: number;
    bk_host_id: number;
    ip: string;
  }
  interface Nodes {
    backend: Array<HostInfo>;
    proxy?: Array<HostInfo>;
  }
  interface Props {
    data?: unknown[];
    isShowNodes?: boolean;
    isSingleType?: boolean;
    maxHeight?: number;
    nodes?: Nodes;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: () => [],
    isShowNodes: true,
    isSingleType: false,
    maxHeight: 436,
    nodes: () => ({
      backend: [],
      proxy: [],
    }),
  });

  const { t } = useI18n();

  const columns = computed(() => {
    if (props.isSingleType) {
      const singleColumns: TableProps['columns'] = [
        {
          field: 'domain',
          label: t('主访问入口'),
          showOverflowTooltip: true,
        },
        {
          field: 'deployStructure',
          label: t('部署架构'),
          showOverflowTooltip: true,
        },
        {
          field: 'version',
          label: t('数据库版本'),
          showOverflowTooltip: true,
        },
        {
          field: 'charset',
          label: t('字符集'),
          showOverflowTooltip: true,
        },
      ];
      if (props.isShowNodes) {
        singleColumns.push({
          field: 'backend',
          label: t('服务器'),
          render: () => {
            const hosts = props.nodes.backend;
            return hosts.map((item) => (
              <div class='host-list__item'>
                <strong class='host-list__tag host-list__tag--master'>M</strong>
                <span class='host-list__ip'>{item.ip}</span>
              </div>
            ));
          },
          rowspan: () => (props.data.length === 0 ? 1 : props.data.length),
          width: 200,
        });
      }
      return singleColumns;
    }

    const haColumns: TableProps['columns'] = [
      {
        field: 'domain',
        label: t('主访问入口'),
        minWidth: 240,
        showOverflowTooltip: true,
      },
      {
        field: 'slaveDomain',
        label: t('从访问入口'),
        minWidth: 240,
        showOverflowTooltip: true,
      },
      {
        field: 'deployStructure',
        label: t('部署架构'),
        showOverflowTooltip: true,
        width: 100,
      },
      {
        field: 'version',
        label: t('数据库版本'),
        showOverflowTooltip: true,
        width: 120,
      },
      {
        field: 'charset',
        label: t('字符集'),
        showOverflowTooltip: true,
        width: 100,
      },
    ];

    if (props.isShowNodes) {
      haColumns.push(
        ...[
          {
            field: 'proxy',
            label: 'Proxy IP',
            render: () => {
              const hosts = props.nodes.proxy;
              return getRenderHosts(hosts).map((group) => (
                <div class='host-list__group'>
                  {group.map((item) => (
                    <div class='host-list__item'>
                      <strong class='host-list__tag host-list__tag--proxy'>P</strong>
                      <span class='host-list__ip'>{item.ip}</span>
                    </div>
                  ))}
                </div>
              ));
            },
            rowspan: () => (props.data.length === 0 ? 1 : props.data.length),
            width: 300,
          },
          {
            field: 'backend',
            label: 'Master / Slave IP',
            render: () => {
              const hosts = props.nodes.backend;
              return getRenderHosts(hosts).map((group) => (
                <div class='host-list__group'>
                  {group.map((item, index) => {
                    const tag = index === 0 ? 'master' : 'slave';
                    return (
                      <div class='host-list__item'>
                        <strong class={`host-list__tag ${`host-list__tag--${tag}`}`}>
                          {tag.charAt(0).toUpperCase()}
                        </strong>
                        <span class='host-list__ip'>{item.ip}</span>
                      </div>
                    );
                  })}
                </div>
              ));
            },
            rowspan: () => (props.data.length === 0 ? 1 : props.data.length),
            width: 300,
          },
        ],
      );
    }
    return haColumns;
  });

  const setCellClass = ({ field }: { field: string }) => {
    const targetFields = ['backend', 'proxy'];
    return targetFields.includes(field) ? 'host-td' : '';
  };

  /**
   * 主从分组渲染
   */
  function getRenderHosts(hosts: Array<HostInfo>) {
    const renderHosts: Array<Array<HostInfo>> = [];
    hosts.forEach((item, index) => {
      const page = Math.floor(index / 2);
      if (!renderHosts[page]) {
        renderHosts[page] = [];
      }
      renderHosts[page].push(item);
    });
    return renderHosts;
  }
</script>

<style lang="less" scoped>
  .preview-table {
    :deep(.bk-vxe-table) {
      td {
        position: relative;

        &.host-td .vxe-cell {
          height: 100% !important;
          padding: 0;
          line-height: normal !important;
        }
      }

      .host-list {
        height: 100%;
        text-align: center;

        &__wrapper {
          position: relative;
          top: 50%;
          display: inline-block;
          transform: translateY(-50%);
        }

        &__group {
          display: flex;
          align-items: center;
        }

        &__item {
          display: flex;
          align-items: center;
          min-width: 130px;
          line-height: 32px;
        }

        &__tag {
          width: 16px;
          height: 16px;
          margin-right: 4px;
          font-size: @font-size-mini;
          line-height: 16px;
          text-align: center;

          &--proxy {
            color: #ff9c01;
            background-color: #ffe8c3;
          }

          &--master {
            color: @primary-color;
            background-color: #cad7eb;
          }

          &--slave {
            color: #2dcb56;
            background-color: #c8e5cd;
          }
        }
      }
    }
  }
</style>
