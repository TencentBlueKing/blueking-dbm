import _ from 'lodash';
import { computed, onBeforeUnmount } from 'vue';
import { useI18n } from 'vue-i18n';

import { getResourceSpecList } from '@services/source/dbresourceSpec';

import { useUrlSearch } from '@hooks';

import { DBTypeInfos, type DBTypes } from '@common/const';
import { batchSplitRegex, ipv4 } from '@common/regex';

import { type Props } from '@components/db-quick-search/bk-quick-search/Index.vue';

import { URL_HOST_MEMO_KEY } from '../constants';
import HostTable from '../HostTable.vue';

const quickSearchValue = ref<Record<string, any>>({});

export const useHostSearchSelect = (
  dbType: DBTypes,
  options = {} as { tableRef: Ref<InstanceType<typeof HostTable> | undefined> },
) => {
  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();
  const { getSearchParams } = useUrlSearch();

  const quickSearchData = computed(() => {
    const serachList: Props['data'] = [
      {
        id: 'ip',
        name: 'IP',
        type: 'multiple-input',
        validator: (value: string) => {
          if (value.split(batchSplitRegex).some((item) => !ipv4.test(item))) {
            return t('格式错误');
          }
          return true;
        },
      },
      {
        id: 'instance_role',
        name: t('部署角色'),
        remoteMethod: () =>
          Promise.resolve(
            _.uniqBy(
              options.tableRef?.value?.getData().map((item) => ({
                label: item.instance_role,
                value: item.instance_role,
              })),
              'value',
            ),
          ),
        type: 'single',
      },

      {
        id: 'region',
        name: t('地域'),
      },
      {
        id: 'bk_sub_zone',
        name: t('园区'),
      },
      {
        id: 'bk_os_name',
        name: t('操作系统'),
      },
      {
        id: 'spec_ids',
        name: t('绑定规格'),
        remoteMethod: () =>
          getResourceSpecList({
            limit: -1,
            offset: 0,
            spec_cluster_type: dbType,
          }).then((specResult) => {
            const specMap = specResult.results.reduce<
              Record<
                string,
                {
                  label: string;
                  value: number;
                }[]
              >
            >((prev, specItem) => {
              const optionItem = {
                label: specItem.spec_name,
                value: specItem.spec_id,
              };
              if (prev[specItem.spec_machine_type]) {
                return Object.assign(prev, {
                  [specItem.spec_machine_type]: prev[specItem.spec_machine_type]!.concat(optionItem),
                });
              }
              return Object.assign(prev, { [specItem.spec_machine_type]: [optionItem] });
            }, {});

            const { machineList } = DBTypeInfos[dbType];
            return machineList.map((machineItem) =>
              Object.assign(machineItem, { children: specMap[machineItem.value] }),
            );
          }),
        type: 'multiple-cascader',
      },
      {
        id: 'bk_svr_device_cls_name',
        name: t('机型'),
      },
    ] as const;

    return serachList;
  });

  const handleSearchValueChange = (payload: Record<string, string>) => {
    options.tableRef?.value?.fetchData();
    router.replace({
      query: {
        ...getSearchParams(),
        [URL_HOST_MEMO_KEY]: encodeURIComponent(JSON.stringify(payload)),
      },
    });
  };

  const fetchData = () => {
    handleSearchValueChange(quickSearchValue.value);
  };

  watch(quickSearchValue, () => {
    console.log(quickSearchValue.value);
  });

  onMounted(() => {
    const urlPaylaod = JSON.parse(decodeURIComponent(String(route.query[URL_HOST_MEMO_KEY] || '{}')));
    quickSearchValue.value = urlPaylaod;
  });

  onBeforeUnmount(() => {
    quickSearchValue.value = {};
  });

  return {
    fetchData,
    handleSearchValueChange,
    quickSearchData,
    quickSearchValue,
  };
};
