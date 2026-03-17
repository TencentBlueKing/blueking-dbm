import _ from 'lodash';
import { computed, ref } from 'vue';
import { useI18n } from 'vue-i18n';

import MonitorPolicyModel from '@services/model/monitor/monitor-policy';
import { getSimpleList } from '@services/source/monitorNoticeGroup';
import { getUserList } from '@services/source/user';

import { DBTypes, MonitorTargetLevel } from '@common/const';

import { type Props as QuickSearchProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

export const useStrategyQuickSearch = (isPlatform: boolean, dbType?: DBTypes) => {
  const { t } = useI18n();

  const searchValue = ref<Record<string, string>>({});
  const isSearching = computed(() => Object.keys(searchValue.value).length > 0);

  const quickSearchData = _.filter(
    [
      {
        description: t('模糊'),
        id: 'name',
        name: t('策略名称'),
        // type: 'input',
      },
      {
        id: 'id',
        name: t('策略 ID'),
        // type: 'input',
      },
      !isPlatform && {
        description: t('模糊'),
        id: 'target_keyword',
        name: t('监控目标'),
        // type: 'input',
      },
      {
        id: 'is_enabled',
        list: [
          {
            label: t('已启用'),
            value: true,
          },
          {
            label: t('已停用'),
            value: false,
          },
        ],
        name: t('启停状态'),
        type: 'single',
      },
      !isPlatform && {
        id: 'target_level',
        list: [
          {
            label: t('内置'),
            value: MonitorTargetLevel.PLATFORM,
          },
          {
            label: t('自定义'),
            value: Object.values(MonitorTargetLevel)
              .filter((item) => item !== MonitorTargetLevel.PLATFORM)
              .join(','),
          },
        ],
        name: t('策略来源'),
        type: 'multiple',
      },
      !isPlatform && {
        id: 'policy_type',
        list: [
          {
            label: t('单指标'),
            value: MonitorPolicyModel.SINGLE,
          },
          {
            label: t('多指标'),
            value: MonitorPolicyModel.MULTI,
          },
          {
            label: 'PromQL',
            value: MonitorPolicyModel.PROMQL,
          },
        ],
        name: t('策略类型'),
        type: 'single',
      },
      !isPlatform && {
        id: 'notify_groups',
        name: t('告警组'),
        remoteMethod: () => {
          return getSimpleList({
            bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
            db_type: dbType || DBTypes.MYSQL,
          }).then((results) =>
            results.map((item) => ({
              label: item.name,
              value: item.id,
            })),
          );
        },
        remoteSearch: true,
        type: 'multiple',
      },
      {
        id: 'updater',
        name: t('更新人'),
        remoteMethod: (params: { defaultValue?: string; keyword?: string }) => {
          const requestParams = {};
          if (params.defaultValue) {
            Object.assign(requestParams, { exact_lookups: params.defaultValue });
          }
          if (params.keyword) {
            Object.assign(requestParams, { fuzzy_lookups: params.keyword });
          }

          return getUserList(requestParams).then((data) =>
            data.results.map((item) => ({
              label: `${item.username} (${item.display_name})`,
              value: item.username,
            })),
          );
        },
        remoteSearch: true,
        type: 'single',
      },
    ],
    (item) => item,
  ) as QuickSearchProps['data'];

  const handleFilterList = (tableOriginalData: MonitorPolicyModel[]) => {
    const localSearchValue = searchValue.value;

    if (Object.keys(localSearchValue).length === 0) {
      return tableOriginalData;
    }

    return tableOriginalData.filter((tableOriginalDataItem) => {
      if (
        Object.prototype.hasOwnProperty.call(localSearchValue, 'name') &&
        !tableOriginalDataItem.name.includes(localSearchValue.name)
      ) {
        return false;
      }
      if (
        Object.prototype.hasOwnProperty.call(localSearchValue, 'id') &&
        tableOriginalDataItem.id !== Number(localSearchValue.id)
      ) {
        return false;
      }
      if (
        Object.prototype.hasOwnProperty.call(localSearchValue, 'is_enabled') &&
        String(tableOriginalDataItem.is_enabled) !== localSearchValue.is_enabled
      ) {
        return false;
      }
      if (
        Object.prototype.hasOwnProperty.call(localSearchValue, 'updater') &&
        tableOriginalDataItem.updater !== localSearchValue.updater
      ) {
        return false;
      }

      if (!isPlatform) {
        if (
          Object.prototype.hasOwnProperty.call(localSearchValue, 'target_keyword') &&
          tableOriginalDataItem.targets.every((target) =>
            target.rule.value.every((value) => !value.includes(localSearchValue.target_keyword)),
          )
        ) {
          return false;
        }
        if (Object.prototype.hasOwnProperty.call(localSearchValue, 'target_level')) {
          const targetLevels = localSearchValue.target_level
            .split(',')
            .flatMap((levelItem) =>
              levelItem === MonitorTargetLevel.PLATFORM ? MonitorTargetLevel.PLATFORM : levelItem.split(','),
            );

          if (!targetLevels.includes(tableOriginalDataItem.target_level)) {
            return false;
          }
        }
        if (
          Object.prototype.hasOwnProperty.call(localSearchValue, 'policy_type') &&
          tableOriginalDataItem.policyType !== localSearchValue.policy_type
        ) {
          return false;
        }
        if (Object.prototype.hasOwnProperty.call(localSearchValue, 'notify_groups')) {
          const notifyGroupIdMap = Object.fromEntries(
            localSearchValue.notify_groups.split(',').map((item) => [item, true]),
          );
          if (tableOriginalDataItem.notify_groups.every((notifyGroupId) => !notifyGroupIdMap[notifyGroupId])) {
            return false;
          }
        }
      }

      return true;
    });
  };

  const handleMergeSearchParams = (currentParams: Record<string, any>) => {
    const currentParamsCopy = { ...currentParams };
    const searchValueParams = searchValue.value;
    const quickSearchDataIds = quickSearchData.map((item) => item.id);

    const filteredParams = _.omitBy(
      currentParamsCopy,
      (value, key) => quickSearchDataIds.includes(key) && !Object.prototype.hasOwnProperty.call(searchValueParams, key),
    );

    return Object.assign({}, filteredParams, searchValueParams);
  };

  return {
    handleFilterList,
    handleMergeSearchParams,
    isSearching,
    quickSearchData,
    searchValue,
  };
};
