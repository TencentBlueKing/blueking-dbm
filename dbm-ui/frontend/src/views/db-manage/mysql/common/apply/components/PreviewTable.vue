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
  <PrimaryTable
    class="preview-table"
    :columns="columns"
    :data="data"
    :max-height="maxHeight"
    row-key="domain"
    :rowspan-and-colspan="rowspanAndColspan"
    v-bind="$attrs" />
</template>

<script setup lang="tsx">
  import type { PrimaryTableCol, PrimaryTableProps, TableRowData } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';

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
    data?: TableRowData[];
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
      const singleColumns: PrimaryTableCol[] = [
        {
          colKey: 'domain',
          ellipsis: true,
          title: t('主访问入口'),
        },
        {
          colKey: 'deployStructure',
          ellipsis: true,
          title: t('部署架构'),
        },
        {
          colKey: 'version',
          ellipsis: true,
          title: t('数据库版本'),
        },
        {
          colKey: 'charset',
          ellipsis: true,
          title: t('字符集'),
        },
      ];
      if (props.isShowNodes) {
        singleColumns.push({
          cell: () => {
            const hosts = props.nodes.backend;
            return hosts.map((item) => (
              <div class='host-list-item'>
                <strong class='host-list-tag host-list-tag--master'>M</strong>
                <span class='host-list-ip'>{item.ip}</span>
              </div>
            ));
          },
          className: 'host-td',
          colKey: 'backend',
          title: t('服务器'),
          width: 200,
        });
      }
      return singleColumns;
    }

    const haColumns: PrimaryTableCol[] = [
      {
        colKey: 'domain',
        ellipsis: true,
        minWidth: 240,
        title: t('主访问入口'),
      },
      {
        colKey: 'slaveDomain',
        ellipsis: true,
        minWidth: 240,
        title: t('从访问入口'),
      },
      {
        colKey: 'deployStructure',
        ellipsis: true,
        title: t('部署架构'),
        width: 100,
      },
      {
        colKey: 'version',
        ellipsis: true,
        title: t('数据库版本'),
        width: 120,
      },
      {
        colKey: 'charset',
        ellipsis: true,
        title: t('字符集'),
        width: 100,
      },
    ];

    if (props.isShowNodes) {
      haColumns.push(
        {
          cell: () => {
            const hosts = props.nodes.proxy || [];
            return getRenderHosts(hosts).map((group) => (
              <div class='host-list-group'>
                {group.map((item) => (
                  <div class='host-list-item'>
                    <strong class='host-list-tag host-list-tag--proxy'>P</strong>
                    <span class='host-list-ip'>{item.ip}</span>
                  </div>
                ))}
              </div>
            ));
          },
          className: 'host-td',
          colKey: 'proxy',
          title: 'Proxy IP',
          width: 300,
        },
        {
          cell: () => {
            const hosts = props.nodes.backend;
            return getRenderHosts(hosts).map((group) => (
              <div class='host-list-group'>
                {group.map((item, index) => {
                  const tag = index === 0 ? 'master' : 'slave';
                  return (
                    <div class='host-list-item'>
                      <strong class={`host-list-tag ${`host-list-tag--${tag}`}`}>{tag.charAt(0).toUpperCase()}</strong>
                      <span class='host-list-ip'>{item.ip}</span>
                    </div>
                  );
                })}
              </div>
            ));
          },
          className: 'host-td',
          colKey: 'backend',
          title: 'Master / Slave IP',
          width: 300,
        },
      );
    }
    return haColumns;
  });

  const rowspanAndColspan: PrimaryTableProps['rowspanAndColspan'] = ({ col, rowIndex }) => {
    if (['backend', 'proxy'].includes(col.colKey as string) && rowIndex === 0) {
      return {
        rowspan: props.data.length === 0 ? 1 : props.data.length,
      };
    }
    return {};
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
    :deep(.t-table) {
      td {
        position: relative;

        &.host-td {
          height: 100% !important;
          padding: 0;
          line-height: normal !important;
        }
      }

      .host-list {
        height: 100%;
        text-align: center;

        .host-list-wrapper {
          position: relative;
          top: 50%;
          display: inline-block;
          transform: translateY(-50%);
        }

        .host-list-group {
          display: flex;
          align-items: center;
        }

        .host-list-item {
          display: flex;
          align-items: center;
          min-width: 130px;
          line-height: 32px;
        }

        .host-list-tag {
          width: 16px;
          height: 16px;
          margin-right: 4px;
          font-size: @font-size-mini;
          line-height: 16px;
          text-align: center;

          &.host-list-tag--proxy {
            color: #ff9c01;
            background-color: #ffe8c3;
          }

          &.host-list-tag--master {
            color: @primary-color;
            background-color: #cad7eb;
          }

          &.host-list-tag--slave {
            color: #2dcb56;
            background-color: #c8e5cd;
          }
        }
      }
    }
  }
</style>
