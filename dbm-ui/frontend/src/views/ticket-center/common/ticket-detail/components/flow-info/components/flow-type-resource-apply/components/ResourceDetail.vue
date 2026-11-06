<template>
  <div
    v-if="isShow"
    class="flow-resource-detail">
    <BkCollapse>
      <BkCollapsePanel name="detail">
        <template #header>
          <div class="box-header">
            <DbIcon type="right-shape" />
            <div class="ml-8">{{ t('资源明细') }}</div>
            <!-- header 整块是折叠触发区，点导出不能顺带折叠面板 -->
            <BkButton
              v-if="hasHost"
              class="ml-8"
              size="small"
              @click.stop="handleExport">
              {{ t('导出') }}
            </BkButton>
          </div>
        </template>
        <template #content>
          <div class="resoure-wrapper">
            <BkCollapse
              v-model="collapseExpandIndex"
              header-icon="right-shape"
              use-block-theme>
              <template
                v-for="(groupItem, index) in renderGroupData"
                :key="groupItem.groupName">
                <BkCollapsePanel :name="index">
                  <template #header>
                    <div class="resource-header">
                      <span>{{ groupItem.groupName }}</span>
                      <span>{{ t('（共 n 个）', [groupItem.count]) }}</span>
                      <DbIcon
                        class="copy-icon"
                        type="copy"
                        @click="(event: Event) => handleCopyIp(groupItem, event)" />
                      <DbIcon
                        class="resource-colllapse-flag"
                        type="right-big" />
                    </div>
                  </template>
                  <template #content>
                    <div class="host-wrapper">
                      <ResourceDetailHostTable
                        v-if="groupItem.data.length"
                        :data="groupItem.data" />
                      <template v-if="groupItem.list.length">
                        <ResourceDetailHostTable
                          v-for="(item, itemIndex) in groupItem.list"
                          :key="itemIndex"
                          :data="item" />
                      </template>
                    </div>
                  </template>
                </BkCollapsePanel>
              </template>
            </BkCollapse>
          </div>
        </template>
      </BkCollapsePanel>
    </BkCollapse>
  </div>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import _ from 'lodash';
  import { type UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import * as XLSX from 'xlsx';

  import TicketModel from '@services/model/ticket/ticket';

  import { DBTypeInfos, DBTypes } from '@common/const';

  import {
    createWorkSheet,
    downloadWorkBook,
  } from '@views/ticket-center/common/ticket-detail/components/flow-info/utils/exportWorkBook';

  import { execCopy } from '@utils';

  import ResourceDetailHostTable, { type IResouce } from './ResourceDetailHostTable.vue';
  import { getResourceHostOwnerData } from './resourceHostOwner';

  interface Props {
    ticketDetail: TicketModel<{
      nodes: Record<string, IResouce[] | Record<string, IResouce>[]>;
    }>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const collapseExpandIndex = ref<number[]>([]);

  const renderGroupData = shallowRef<
    {
      count: number;
      data: IResouce[];
      groupName: string;
      list: ({ tag: string } & IResouce)[][];
    }[]
  >([]);

  const isShow = computed(() => Object.keys(props.ticketDetail.details.nodes || {}).length > 0);

  // 至少有一台主机才展示导出按钮
  const hasHost = computed(() => renderGroupData.value.some((item) => item.count > 0));

  watchEffect(() => {
    const nodes = props.ticketDetail.details.nodes;
    renderGroupData.value = Object.keys(nodes).map((nodeName) => {
      const nodeDataList = nodes[nodeName]!;
      const groupName = _.trim(nodeName.replace(/\d/g, '').split(/_+/).join('_'), '_');
      if (nodeDataList[0]!.ip) {
        return {
          count: nodes[nodeName]!.length,
          data: nodes[nodeName] as IResouce[],
          groupName,
          list: [],
        };
      }
      const multDataList = (nodeDataList as Record<string, IResouce>[]).map((item) => {
        return Object.keys(item).map((nodeKey) => ({
          tag: nodeKey,
          ...item[nodeKey]!,
        }));
      });
      return {
        count: _.flatten(multDataList).length,
        data: [],
        groupName,
        list: multDataList,
      };
    });
    collapseExpandIndex.value = renderGroupData.value.map((item, index) => index);
  });

  const handleCopyIp = (data: UnwrapRef<typeof renderGroupData>[number], event: Event) => {
    event.stopPropagation();
    event.stopImmediatePropagation();
    const copyList = [...data.data, ..._.flatten(data.list)];
    execCopy(copyList.map((item) => item.ip).join('\n'), t('复制成功，共n条', { n: copyList.length }));
  };

  // 空值写空单元格，不沿用页面的 -- 占位
  const getCellValue = (value: unknown) => (value === null || value === undefined || value === '' ? null : value);

  // 资源归属拆成「所属业务 / 所属DB / 资源标签」三列，口径与页面 ResourceHostOwner 一致
  const getOwnerCells = (host: IResouce) => {
    const owner = getResourceHostOwnerData(host);
    const bizName = owner.for_biz?.bk_biz_id ? owner.for_biz.bk_biz_name : t('公共资源池');
    const isForDb = owner.resource_type && owner.resource_type !== 'PUBLIC';
    const dbName =
      isForDb && DBTypeInfos[owner.resource_type as DBTypes]
        ? DBTypeInfos[owner.resource_type as DBTypes].name
        : t('通用');
    const labelNames = (owner.labels || [])
      .map((item) => item.name)
      .filter(Boolean)
      .join(',');
    return [bizName, dbName, getCellValue(labelNames)];
  };

  // 每个分组：分组名单独一行（合并整行），下面是带表头的完整资源列表，分组之间空一行；
  // 存在多节点分组时，各分组列表都在 IP 后加「标签」列，保证整张表列对齐
  const handleExport = () => {
    const hasTag = renderGroupData.value.some((item) => item.list.length > 0);
    const header = [
      'IP',
      ...(hasTag ? [t('标签')] : []),
      t('所属业务'),
      t('所属DB'),
      t('资源标签'),
      t('地域'),
      t('园区'),
      t('机架'),
      t('操作系统名称'),
      t('操作系统'),
      t('机型'),
      t('CPU_核_'),
      t('内存G'),
      t('磁盘G'),
    ];

    const sheetRows: unknown[][] = [];
    // 分组名所在行号，生成 sheet 后合并为整行
    const groupRowIndexList: number[] = [];
    renderGroupData.value.forEach((groupItem) => {
      const hostList: ({ tag?: string } & IResouce)[] = [...groupItem.data, ..._.flatten(groupItem.list)];
      if (!hostList.length) {
        return;
      }
      if (sheetRows.length) {
        sheetRows.push([]);
      }
      groupRowIndexList.push(sheetRows.length);
      // 分组行与页面分组标题一致：分组名 + 主机数量
      sheetRows.push([`${groupItem.groupName}${t('（共 n 个）', [groupItem.count])}`]);
      sheetRows.push(header);
      hostList.forEach((host) => {
        sheetRows.push([
          host.ip,
          ...(hasTag ? [getCellValue(host.tag)] : []),
          ...getOwnerCells(host),
          getCellValue(host.city),
          getCellValue(host.sub_zone),
          getCellValue(host.rack_id),
          getCellValue(host.os_name),
          getCellValue(host.os_type),
          getCellValue(host.device_class),
          getCellValue(host.bk_cpu),
          // 内存与页面口径一致：MB 换算为 G，保留两位小数，以数字写入
          host.bk_mem ? Number((host.bk_mem / 1024).toFixed(2)) : null,
          getCellValue(host.bk_disk),
        ]);
      });
    });

    const workSheet = createWorkSheet(sheetRows);
    workSheet['!merges'] = groupRowIndexList.map((rowIndex) => ({
      e: { c: header.length - 1, r: rowIndex },
      s: { c: 0, r: rowIndex },
    }));

    const workBook = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(workBook, workSheet, t('资源明细'));

    const { id, ticket_type_display: ticketTypeName } = props.ticketDetail;
    downloadWorkBook(workBook, `${ticketTypeName}_${id}_${t('资源明细')}_${dayjs().format('YYYYMMDD')}.xlsx`);
  };
</script>
<style lang="less">
  .flow-resource-detail {
    position: relative;
    z-index: 0;
    display: block;
    background: #f5f7fa;

    .bk-collapse-header {
      height: 28px;
      line-height: 28px;
    }

    .bk-collapse-content {
      padding: 0;
    }

    .bk-collapse-icon {
      display: none;
    }

    .box-header {
      display: flex;
      padding: 12px 9px;
      font-weight: bold;
      color: #4d4f56;
      align-items: center;
      cursor: pointer;
    }

    .resoure-wrapper {
      .bk-collapse-item-active {
        .resource-header {
          .resource-colllapse-flag {
            transform: rotate(90deg);
          }
        }
      }

      .bk-collapse-item {
        margin-bottom: 18px;
      }
    }

    .resource-header {
      display: flex;
      height: 28px;
      padding: 0 12px;
      margin: 0 16px 0 32px;
      font-weight: 500;
      color: #313238;
      cursor: pointer;
      background: #f0f1f5;
      user-select: none;
      align-items: center;
      align-content: center;

      .copy-icon {
        margin-top: 2px;
        font-size: 14px;
        color: #979ba5;
        cursor: pointer;

        &:hover {
          color: #3a84ff;
        }
      }

      .resource-colllapse-flag {
        margin-left: auto;
        font-size: 18px;
        color: #979ba5;
      }
    }

    .host-wrapper {
      padding: 0 16px 0 32px;
    }
  }
</style>
