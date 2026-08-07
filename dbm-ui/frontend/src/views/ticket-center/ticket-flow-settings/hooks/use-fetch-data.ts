// eslint-disable-next-line simple-import-sort/imports
import { computed, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import type { SortInfo } from 'tdesign-vue-next';

import TicketFlowDescribeModel, {
  type ScopeType,
  type TagMatchType,
} from '@services/model/ticket-flow-describe/TicketFlowDescribe';
import { type ClusterTagItem, queryTicketFlowDescribe } from '@services/source/ticket';

import { useUrlSearch } from '@hooks';

import { useGlobalBizs } from '@stores';

import { DBTypes } from '@common/const';

import { transfromDataToQuery } from '@utils';

import { usePagination } from './use-pagination';

export interface TableRow {
  children?: TableRow[];
  cluster_tags: ClusterTagItem[];
  clusters: Array<{
    cluster_id: number;
    immute_domain: string;
  }>;
  configs: {
    expire_config: {
      flow_todo_expire: number;
      inner_flow_expire: number;
      itsm_expire: number;
    };
    need_itsm: boolean;
    need_itsm_duplicated: boolean;
  };
  editable: boolean;
  id: number;
  isChildRow: boolean;
  isCustom: boolean;
  isDuplicate: boolean;
  /** 是否为同父策略下的最后一个子策略（用于树形连接线截断） */
  isLastChild?: boolean;
  /** 标签键是否已失效（仅按标签子策略有意义） */
  isTagInvalid: boolean;
  permission: {
    biz_ticket_config_set: boolean;
    ticket_config_set: boolean;
  };
  rawData: TicketFlowDescribeModel;
  remark: string;
  /** 生效范围类型：按集群 / 按标签 */
  scopeType: ScopeType;
  /** 标签生效范围展示文案（按标签子策略） */
  tagDisplay: string;
  /** 标签键（按标签子策略） */
  tagKey: string;
  /** 标签匹配条件类型 */
  tagMatchType: TagMatchType;
  /** 标签具体值列表（exists 时为空） */
  tagValues: string[];
  ticket_type: string;
  ticket_type_display: string;
  updateAtDisplay: string;
  updater: string;
}

export const useFetchData = () => {
  const { currentBizId } = useGlobalBizs();
  const { getSearchParams, replaceSearchParams } = useUrlSearch();
  const route = useRoute();

  // db_type 由路由参数驱动（与 Index.vue 同步到路由的 dbType 保持一致）
  const dbType = computed(() => (route.params.dbType as DBTypes) || DBTypes.MYSQL);

  const { handlePageLimitChange, handlePageValueChange, pagination } = usePagination();

  // 从 URL 读取初始状态（搜索条件由 DbQuickSearch 的 parse-url 负责回显到 searchValue）
  const urlParams = getSearchParams();
  const searchValue = ref<Record<string, any>>({});

  if (urlParams.current) {
    pagination.current = Number(urlParams.current);
  }
  if (urlParams.limit) {
    pagination.limit = Number(urlParams.limit);
  }

  // 搜索 + 筛选标签 + 分页参数统一写回 URL
  const syncUrlParams = () => {
    replaceSearchParams(
      transfromDataToQuery({
        ...searchValue.value,
        current: pagination.current,
        limit: pagination.limit,
      }),
    );
  };

  const isLoading = ref(false);
  const isRequestFailed = ref(false);
  const isSearching = ref(false);

  const rawTreeData = ref<TableRow[]>([]);
  const allTreeData = ref<TableRow[]>([]);
  const paginatedData = ref<TableRow[]>([]);
  const expandedTreeNodes = ref<(string | number)[]>([]);
  const tableSort = ref<SortInfo | undefined>();

  const buildTreeData = (results: TicketFlowDescribeModel[]): TableRow[] => {
    const parentRows: TableRow[] = [];
    const childMap = new Map<string, TableRow[]>();

    results.forEach((item) => {
      const tableRow: TableRow = {
        cluster_tags: item.cluster_tags,
        clusters: item.clusters,
        configs: item.configs,
        editable: item.editable,
        id: item.id,
        isChildRow: item.isChildPolicy,
        isCustom: false,
        isDuplicate: item.isChildPolicy && item.configs.need_itsm_duplicated,
        isTagInvalid: item.isTagKeyInvalid,
        permission: item.permission,
        rawData: item,
        remark: item.remark,
        scopeType: item.scopeType,
        tagDisplay: item.tagDisplay,
        tagKey: item.tagKey,
        tagMatchType: item.tagMatchType,
        tagValues: item.tagValues,
        ticket_type: item.ticket_type,
        ticket_type_display: item.ticket_type_display,
        updateAtDisplay: item.updateAtDisplay,
        updater: item.updater,
      };

      if (item.isChildPolicy) {
        const children = childMap.get(item.ticket_type) || [];
        children.push(tableRow);
        childMap.set(item.ticket_type, children);
      } else {
        tableRow.isCustom = item.isCustom;
        parentRows.push(tableRow);
      }
    });

    // 父策略按 ticket_type_display 自然序排序
    parentRows.sort((a, b) => a.ticket_type_display.localeCompare(b.ticket_type_display));

    // 构建 children 字段并排序：先「按集群」后「按标签」分组，组内按更新时间倒序（最新在前）
    // 同时标记每个父策略的最后一个子策略（用于树形连接线截断）
    parentRows.forEach((parentRow, index) => {
      const children = childMap.get(parentRow.ticket_type);
      if (children && children.length > 0) {
        children.sort((a, b) => {
          // 先按生效范围类型分组：按集群在前、按标签在后
          if (a.scopeType !== b.scopeType) {
            return a.scopeType === 'cluster' ? -1 : 1;
          }
          // 组内按更新时间倒序（最新在前），空更新时间视为最早
          const timeDiff =
            new Date(b.rawData.update_at || 0).getTime() - new Date(a.rawData.update_at || 0).getTime();
          // 时间相同时按 id 升序保证稳定
          return timeDiff !== 0 ? timeDiff : a.rawData.id - b.rawData.id;
        });
        children.forEach((child, i) => {
          children[i] = { ...child, isLastChild: false };
        });
        children[children.length - 1] = { ...children[children.length - 1], isLastChild: true };
        parentRows[index] = { ...parentRow, children };
      }
    });

    return parentRows;
  };

  /** 拆分逗号分隔的多选值为数组 */
  const splitMultiValue = (value: string) =>
    value
      .split(',')
      .map((v) => v.trim())
      .filter(Boolean);

  /** 检查节点是否匹配搜索条件（多条件取 AND） */
  const isMatchSearch = (node: TableRow, searchMap: Record<string, string>): boolean => {
    if (!Object.values(searchMap).some((v) => v !== '')) {
      return true;
    }

    // 单据类型：cascader 实际过滤值（纯 ticket_type，如 mysql.BACKUP）在 ticket_type__in 中
    if (searchMap.ticket_type__in && !splitMultiValue(searchMap.ticket_type__in).includes(node.ticket_type)) {
      return false;
    }

    // 集群域名：模糊匹配节点下任意集群的 immute_domain（多选取并集，任一命中即通过）
    if (searchMap.immute_domain) {
      const domains = splitMultiValue(searchMap.immute_domain).map((d) => d.toLowerCase());
      const hit = domains.some((domain) =>
        node.clusters.some((cluster) => cluster.immute_domain.toLowerCase().includes(domain)),
      );
      if (!hit) return false;
    }

    // 是否审批：多选值取 OR 逻辑（任一命中即通过）
    if (searchMap.need_itsm) {
      const values = splitMultiValue(searchMap.need_itsm);
      if (!values.some((value) => String(node.configs.need_itsm) === value)) return false;
    }

    // 更新人：模糊匹配
    if (searchMap.updater && !node.updater.toLowerCase().includes(searchMap.updater.toLowerCase())) {
      return false;
    }

    // 更新时间：根据 __gte / __lte 端点比较
    if (searchMap.update_at__gte || searchMap.update_at__lte) {
      const nodeTime = new Date(node.updateAtDisplay || 0).getTime();
      if (!Number.isNaN(nodeTime)) {
        const gte = searchMap.update_at__gte ? new Date(searchMap.update_at__gte).getTime() : -Infinity;
        const lte = searchMap.update_at__lte ? new Date(searchMap.update_at__lte).getTime() : Infinity;
        if (!Number.isNaN(gte) && nodeTime < gte) return false;
        if (!Number.isNaN(lte) && nodeTime > lte) return false;
      }
    }

    // 备注：模糊匹配
    if (searchMap.remark && !(node.remark || '').toLowerCase().includes(searchMap.remark.toLowerCase())) {
      return false;
    }

    return true;
  };

  /** 递归过滤树形数据（子节点匹配则保留父节点） */
  const filterTreeData = (nodes: TableRow[], searchMap: Record<string, string>): TableRow[] =>
    nodes
      .map((node) => {
        // 递归过滤子节点
        const filteredChildren =
          node.children && node.children.length > 0 ? filterTreeData(node.children, searchMap) : undefined;

        // 搜索过滤 + 子节点匹配则保留父节点
        const selfMatch = isMatchSearch(node, searchMap);
        const matched = selfMatch || (filteredChildren && filteredChildren.length > 0);

        if (!matched) return null;

        // 父节点匹配但子节点不匹配时丢弃 children
        const rest = { ...node };
        delete rest.children;
        const finalChildren =
          filteredChildren && filteredChildren.length > 0
            ? filteredChildren.map((child, i) => {
                const restChildren = { ...child, isLastChild: false };
                return i === filteredChildren.length - 1 ? { ...restChildren, isLastChild: true } : restChildren;
              })
            : null;
        return finalChildren ? { ...rest, children: finalChildren } : rest;
      })
      .filter((node): node is TableRow => node !== null);

  /** 应用排序（递归排序子节点） */
  const applySort = (nodes: TableRow[], sort: SortInfo): TableRow[] => {
    if (!sort.sortBy) return nodes;

    const sorted = [...nodes].sort((a, b) => {
      // 当前仅支持按更新时间排序
      const compare =
        sort.sortBy === 'updateAtDisplay'
          ? new Date(a.updateAtDisplay || 0).getTime() - new Date(b.updateAtDisplay || 0).getTime()
          : 0;
      return sort.descending ? -compare : compare;
    });

    return sorted.map((node) => {
      const sortedChildren = node.children && node.children.length > 0 ? applySort(node.children, sort) : node.children;
      // 排序后重新标记最后一个子节点
      if (sortedChildren && sortedChildren.length > 0) {
        sortedChildren.forEach((child, i) => {
          sortedChildren[i] = { ...child, isLastChild: false };
        });
        sortedChildren[sortedChildren.length - 1] = {
          ...sortedChildren[sortedChildren.length - 1],
          isLastChild: true,
        };
      }
      return sortedChildren ? { ...node, children: sortedChildren } : node;
    });
  };

  /** 应用分页 */
  const applyPagination = () => {
    // 越界时回退到最后一页，避免筛选后停留在空页
    const maxPage = Math.max(1, Math.ceil(pagination.count / pagination.limit));
    if (pagination.current > maxPage) {
      pagination.current = maxPage;
    }
    const start = (pagination.current - 1) * pagination.limit;
    const end = start + pagination.limit;
    paginatedData.value = allTreeData.value.slice(start, end);
  };

  /** 获取所有有子节点的父行 ID（用于默认展开） */
  const getAllParentIds = (nodes: TableRow[]): (string | number)[] =>
    nodes.flatMap((node) => (node.children && node.children.length > 0 ? [node.id] : []));

  /** 应用本地过滤（tab、搜索、排序、分页），不请求接口 */
  const applyLocalFilter = () => {
    // 所有搜索条件统一由 filterTreeData -> isMatchSearch 处理（多条件取 AND，子节点匹配则保留父节点）
    const filtered = filterTreeData(rawTreeData.value, searchValue.value);

    // 应用排序（如"更新时间"列）
    const sorted = tableSort.value?.sortBy ? applySort(filtered, tableSort.value) : filtered;

    pagination.count = sorted.length;
    allTreeData.value = sorted;

    // 默认展开所有有子节点的行
    expandedTreeNodes.value = getAllParentIds(sorted);

    applyPagination();

    isSearching.value = Object.values(searchValue.value).some((v) => v !== '');
  };

  /** 获取列表数据（仅调接口，存储原始数据后触发本地过滤） */
  const fetchListData = async () => {
    isLoading.value = true;
    isRequestFailed.value = false;

    try {
      const data = await queryTicketFlowDescribe({
        bk_biz_id: currentBizId,
        db_type: dbType.value,
      });

      rawTreeData.value = buildTreeData(data.results);
      applyLocalFilter();
    } catch (error) {
      console.error('fetch list data error:', error);
      isRequestFailed.value = true;
      rawTreeData.value = [];
      allTreeData.value = [];
      paginatedData.value = [];
      pagination.count = 0;
    } finally {
      isLoading.value = false;
    }
  };

  // 表头筛选变化（本地过滤，合并而非覆盖，避免清空快捷搜索条件）
  const handleFilterChange = (filters: Record<string, any>) => {
    pagination.current = 1;
    searchValue.value = filters;
  };

  // 排序变化（本地排序）
  const handleSortChange = (sort: SortInfo | SortInfo[]) => {
    pagination.current = 1;
    tableSort.value =
      sort && !Array.isArray(sort) && sort.sortBy
        ? ({ descending: sort.descending, sortBy: sort.sortBy } as SortInfo)
        : undefined;
    applyLocalFilter();
  };

  const handleClearFilter = () => {
    pagination.current = 1;
    searchValue.value = {};
    applyLocalFilter();
  };

  const onExpandedTreeNodesChange = (expandedNodes: (string | number)[]) => {
    expandedTreeNodes.value = expandedNodes;
  };

  // 监听搜索值变化，触发本地过滤并同步到 URL
  watch(
    searchValue,
    () => {
      syncUrlParams();
      applyLocalFilter();
    },
    {
      deep: true,
    },
  );

  // 分页变化，重新应用分页并同步到 URL
  watch(
    () => [pagination.current, pagination.limit],
    () => {
      syncUrlParams();
      applyPagination();
    },
  );

  watch(
    () => route.params.dbType,
    (_, prevValue) => {
      // 仅在 dbType 真正变化（切换 Tab）时清空搜索；初始挂载不清除，以保留 URL 上的搜索参数
      if (prevValue !== undefined) {
        searchValue.value = {};
        pagination.current = 1;
      }
      nextTick(() => {
        fetchListData();
      });
    },
    {
      immediate: true,
    },
  );

  return {
    allTreeData,
    expandedTreeNodes,
    fetchListData,
    handleClearFilter,
    handleFilterChange,
    handlePageLimitChange,
    handlePageValueChange,
    handleSortChange,
    isLoading,
    isRequestFailed,
    isSearching,
    onExpandedTreeNodesChange,
    paginatedData,
    pagination,
    searchValue,
    tableSort,
  };
};
