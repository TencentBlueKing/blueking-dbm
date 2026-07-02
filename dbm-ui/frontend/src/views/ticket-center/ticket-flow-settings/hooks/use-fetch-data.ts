// eslint-disable-next-line simple-import-sort/imports
import { computed, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import type { SortInfo } from 'tdesign-vue-next';

import TicketFlowDescribeModel from '@services/model/ticket-flow-describe/TicketFlowDescribe';
import { queryTicketFlowDescribe } from '@services/source/ticket';

import { useUrlSearch } from '@hooks';

import { useGlobalBizs } from '@stores';

import { DBTypes } from '@common/const';

import { transfromDataToQuery } from '@utils';

import { usePagination } from './use-pagination';

export interface TableRow {
  children?: TableRow[];
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
    need_manual_confirm: boolean;
  };
  id: number;
  isChildRow: boolean;
  isCustom: boolean;
  isDuplicate?: boolean;
  permission: {
    biz_ticket_config_set: boolean;
    ticket_config_set: boolean;
  };
  rawData: TicketFlowDescribeModel;
  remark: string;
  ticket_type: string;
  ticket_type_display: string;
  updateAtDisplay: string;
  updater: string;
}

export const useFetchData = () => {
  const { currentBizId } = useGlobalBizs();
  const { getSearchParams, replaceSearchParams } = useUrlSearch();
  const route = useRoute();

  // db_type 由路由参数驱动（与 Index.vue 同步到路由的 dbType 保持一致，无需作为入参传入）
  const dbType = computed(() => (route.params.dbType as DBTypes) || DBTypes.MYSQL);

  // 分页状态由本 hook 统一持有并同步到 URL
  const { handlePageLimitChange, handlePageValueChange, pagination } = usePagination();
  // 筛选标签（全部 / 免审批），URL 驱动
  const activeTab = ref<'all' | 'noApproval'>('all');

  // 从 URL 读取初始状态：筛选标签与分页由 URL 作为单一可信源
  // （搜索条件由 DbQuickSearch 的 parse-url 负责从 URL 回显到 searchValue）
  const urlParams = getSearchParams();
  const searchValue = ref<Record<string, any>>({});

  // 筛选标签（全部 / 免审批）从 URL 恢复
  if (urlParams.activeTab) {
    activeTab.value = urlParams.activeTab as 'all' | 'noApproval';
  }

  // 分页参数从 URL 恢复
  if (urlParams.current) {
    pagination.current = Number(urlParams.current);
  }
  if (urlParams.limit) {
    pagination.limit = Number(urlParams.limit);
  }

  // 搜索 + 筛选标签 + 分页参数统一写回 URL（transfromDataToQuery 负责规整数组与过滤空值）
  const syncUrlParams = () => {
    replaceSearchParams(
      transfromDataToQuery({
        ...searchValue.value,
        activeTab: activeTab.value,
        current: pagination.current,
        limit: pagination.limit,
      }),
    );
  };

  // 加载状态
  const isLoading = ref(false);
  const isRequestFailed = ref(false);
  const isSearching = ref(false);

  // 树形数据（原始全量数据，不受 tab/搜索影响）
  const rawTreeData = ref<TableRow[]>([]);
  // 过滤后的数据（用于展示）
  const allTreeData = ref<TableRow[]>([]);
  const paginatedData = ref<TableRow[]>([]);
  const expandedTreeNodes = ref<(string | number)[]>([]);
  // 受控排序状态（TDesign SortInfo 类型）
  const tableSort = ref<SortInfo | undefined>({
    descending: true,
    sortBy: 'updated_at',
  } as SortInfo);

  /**
   * 构建树形数据结构
   */
  const buildTreeData = (results: TicketFlowDescribeModel[]): TableRow[] => {
    const parentRows: TableRow[] = [];
    const childMap = new Map<string, TableRow[]>();
    // 先建立 ticket_type -> parentConfig 的映射，用于判断子策略是否重复
    const parentConfigMap = new Map<string, boolean>();

    results.forEach((item) => {
      if (!item.isChildPolicy) {
        parentConfigMap.set(item.ticket_type, item.configs.need_itsm);
      }
    });

    results.forEach((item) => {
      const parentNeedItsm = parentConfigMap.get(item.ticket_type);
      const isDuplicate =
        item.isChildPolicy && parentNeedItsm !== undefined && parentNeedItsm === item.configs.need_itsm;

      const tableRow: TableRow = {
        clusters: item.clusters,
        configs: item.configs,
        id: item.id,
        isChildRow: item.isChildPolicy,
        isCustom: false,
        isDuplicate,
        permission: item.permission,
        rawData: item,
        remark: item.remark,
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

    // 构建 children 字段
    parentRows.forEach((parentRow, index) => {
      const children = childMap.get(parentRow.ticket_type);
      if (children && children.length > 0) {
        parentRows[index] = { ...parentRow, children };
      }
    });

    return parentRows;
  };

  /**
   * 检查节点是否匹配搜索条件
   */
  const isMatchSearch = (node: TableRow, searchMap: Record<string, string>): boolean => {
    // 如果没有搜索条件，返回 true
    const hasSearchCondition = Object.values(searchMap).some((v) => v !== '');
    if (!hasSearchCondition) {
      return true;
    }

    // 检查各个搜索字段
    let match = true;

    // 单据类型：cascader 实际过滤值（纯 ticket_type，如 mysql.BACKUP）在 ticket_type__in 中
    if (searchMap.ticket_type__in) {
      const ticketTypes = searchMap.ticket_type__in.split(',').filter(Boolean);
      match = match && ticketTypes.includes(node.ticket_type);
    }

    // 集群域名：模糊匹配节点下任意集群的 immute_domain（多选取并集，任一命中即通过）
    if (searchMap.immute_domain) {
      const domains = searchMap.immute_domain
        .split(',')
        .map((domain) => domain.trim().toLowerCase())
        .filter(Boolean);
      match =
        match &&
        domains.some((domain) => node.clusters.some((cluster) => cluster.immute_domain.toLowerCase().includes(domain)));
    }

    // 是否审批：多选值取 OR 逻辑（任一命中即通过）
    if (searchMap.need_itsm) {
      const needItsmValues = searchMap.need_itsm.split(',').filter(Boolean);
      match = match && needItsmValues.some((value) => String(node.configs.need_itsm) === value);
    }

    // 更新人：模糊匹配
    if (searchMap.updater) {
      const keyword = searchMap.updater.toLowerCase();
      match = match && node.updater.toLowerCase().includes(keyword);
    }

    // 更新时间：根据 __gte / __lte 端点比较
    if (searchMap.update_at__gte || searchMap.update_at__lte) {
      const nodeTime = new Date(node.updateAtDisplay || 0).getTime();
      if (!Number.isNaN(nodeTime)) {
        if (searchMap.update_at__gte) {
          const gte = new Date(searchMap.update_at__gte).getTime();
          if (!Number.isNaN(gte) && nodeTime < gte) {
            match = false;
          }
        }
        if (searchMap.update_at__lte) {
          const lte = new Date(searchMap.update_at__lte).getTime();
          if (!Number.isNaN(lte) && nodeTime > lte) {
            match = false;
          }
        }
      }
    }

    // 备注：模糊匹配
    if (searchMap.remark) {
      const keyword = searchMap.remark.toLowerCase();
      match = match && (node.remark || '').toLowerCase().includes(keyword);
    }

    return match;
  };

  /**
   * 递归过滤树形数据
   */
  const filterTreeData = (nodes: TableRow[], searchMap: Record<string, string>): TableRow[] => {
    const filtered: TableRow[] = [];

    nodes.forEach((node) => {
      // 检查当前节点是否匹配
      let selfMatch = false;

      if (activeTab.value === 'noApproval') {
        // Tab 过滤：父行本身免审批，或任一子行免审批
        const childrenNoApproval = node.children?.some((c) => !c.configs.need_itsm);
        selfMatch = !node.configs.need_itsm || (childrenNoApproval ?? false);
      } else {
        selfMatch = true;
      }

      // 搜索过滤
      selfMatch = selfMatch && isMatchSearch(node, searchMap);

      // 递归过滤子节点
      let filteredChildren: TableRow[] | undefined;
      if (node.children && node.children.length > 0) {
        filteredChildren = filterTreeData(node.children, searchMap);
        if (filteredChildren.length > 0) {
          selfMatch = true; // 子节点匹配，父节点也要保留
        }
      }

      if (selfMatch) {
        const newNode = { ...node };
        if (filteredChildren && filteredChildren.length > 0) {
          newNode.children = filteredChildren;
        } else if (node.children) {
          // 父节点匹配但子节点不匹配，保留空 children 或不设置
          delete newNode.children;
        }
        filtered.push(newNode);
      }
    });

    return filtered;
  };

  /**
   * 应用排序
   */
  const applySort = (nodes: TableRow[], sort: SortInfo): TableRow[] => {
    if (!sort.sortBy) return nodes;

    const sorted = [...nodes];
    sorted.sort((a, b) => {
      let compare = 0;
      if (sort.sortBy === 'updateAtDisplay') {
        // 按更新时间排序
        const dateA = new Date(a.updateAtDisplay || 0).getTime();
        const dateB = new Date(b.updateAtDisplay || 0).getTime();
        compare = dateA - dateB;
      }
      return sort.descending ? -compare : compare;
    });

    // 递归排序子节点（避免直接修改函数参数）
    const result = sorted.map((node) => {
      if (node.children && node.children.length > 0) {
        return { ...node, children: applySort(node.children, sort) };
      }
      return node;
    });

    return result;
  };

  /**
   * 应用分页
   */
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

  /**
   * 获取所有有子节点的父行 ID（用于默认展开）
   */
  const getAllParentIds = (nodes: TableRow[]): (string | number)[] => {
    const ids: (string | number)[] = [];
    nodes.forEach((node) => {
      if (node.children && node.children.length > 0) {
        ids.push(node.id);
      }
    });
    return ids;
  };

  /**
   * 递归统计所有节点总数（含子节点）
   */
  const countAllNodes = (nodes: TableRow[]): number => {
    let count = 0;
    nodes.forEach((node) => {
      count++;
      if (node.children) {
        count += countAllNodes(node.children);
      }
    });
    return count;
  };

  /**
   * 应用本地过滤（tab、搜索、排序、分页），不请求接口
   */
  const applyLocalFilter = () => {
    // 所有搜索条件（单据类型、集群域名、是否审批、更新人、更新时间、备注等）统一由
    // filterTreeData -> isMatchSearch 处理（多条件取 AND，子节点匹配则保留父节点）
    let filtered = filterTreeData(rawTreeData.value, searchValue.value);

    // 应用排序（如"更新时间"列）
    if (tableSort.value && tableSort.value.sortBy) {
      filtered = applySort(filtered, tableSort.value);
    }

    pagination.count = countAllNodes(filtered);

    allTreeData.value = filtered;

    // 默认展开所有有子节点的行
    expandedTreeNodes.value = getAllParentIds(filtered);

    applyPagination();

    isSearching.value = Object.values(searchValue.value).some((v) => v !== '');
  };

  /**
   * 获取列表数据（仅调接口，存储原始数据后触发本地过滤）
   */
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

  // 处理表头筛选变化（本地过滤）。合并而非覆盖，避免清空快捷搜索条件
  const handleFilterChange = (filters: Record<string, any>) => {
    pagination.current = 1;
    searchValue.value = filters;
  };

  // 处理排序变化（本地排序）
  const handleSortChange = (sort: SortInfo | SortInfo[]) => {
    pagination.current = 1;
    if (sort && !Array.isArray(sort) && sort.sortBy) {
      tableSort.value = { descending: sort.descending, sortBy: sort.sortBy } as SortInfo;
    } else {
      tableSort.value = undefined;
    }
    applyLocalFilter();
  };

  // tab 切换（仅设置 activeTab，由 watch(activeTab) 统一处理过滤与 URL 同步）
  const handleTabChange = (tab: 'all' | 'noApproval') => {
    activeTab.value = tab;
  };

  const handleClearFilter = () => {
    pagination.current = 1;
    searchValue.value = {};
    activeTab.value = 'all';
    applyLocalFilter();
  };

  const onExpandedTreeNodesChange = (expandedNodes: (string | number)[]) => {
    expandedTreeNodes.value = expandedNodes;
  };

  // 监听搜索值变化，触发本地过滤并同步到 URL（快捷搜索 / 表头筛选 / 清空均统一在此处理）
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

  // 监听筛选标签变化（全部 / 免审批）：重置到首页、同步 URL 并重新过滤
  watch(activeTab, () => {
    pagination.current = 1;
    syncUrlParams();
    applyLocalFilter();
  });

  // 监听分页变化，重新应用分页并同步到 URL
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
      // 仅在 dbType 真正变化（切换 Tab）时清空搜索；初始挂载不清除，以保留 URL 上的搜索参数用于状态恢复
      if (prevValue !== undefined) {
        searchValue.value = {};
        activeTab.value = 'all';
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

  // 统计数量（基于原始全量数据，不受 tab 切换影响）
  const allCount = computed(() => countAllNodes(rawTreeData.value));

  const noApprovalCount = computed(() => {
    let count = 0;
    const countNodes = (nodes: TableRow[]) => {
      nodes.forEach((node) => {
        if (!node.configs.need_itsm) {
          count++;
        }
        if (node.children) {
          countNodes(node.children);
        }
      });
    };
    countNodes(rawTreeData.value);
    return count;
  });

  return {
    activeTab,
    allCount,
    allTreeData,
    expandedTreeNodes,
    fetchListData,
    handleClearFilter,
    handleFilterChange,
    handlePageLimitChange,
    handlePageValueChange,
    handleSortChange,
    handleTabChange,
    isLoading,
    isRequestFailed,
    isSearching,
    noApprovalCount,
    onExpandedTreeNodesChange,
    paginatedData,
    pagination,
    searchValue,
    tableSort,
  };
};
