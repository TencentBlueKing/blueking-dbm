import dayjs from 'dayjs';
import { markRaw, shallowRef, type UnwrapRef } from 'vue';
import { useRequest } from 'vue-request';

import { queryBizInstanceAttrs } from '@services/source/dbbase';

import { clusterInstStatus, ClusterTypes, specialOptionLabelMap, SpecialOptions } from '@common/const';

import DatetimeRange from '@components/db-table/components/DatetimeRange.vue';
import MultipleInput from '@components/db-table/components/MultipleInput.vue';
import MultipleSelect from '@components/db-table/components/MultipleSelect.vue';

import { t } from '@/locales';

const clusterRedisTypeList = [
  ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
  ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
  ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
  ClusterTypes.PREDIXY_REDIS_CLUSTER,
];

const baseFilter = {
  create_at: {
    component: markRaw(DatetimeRange),
    name: t('部署时间'),
    props: {
      shortcuts: [
        {
          text: t('近 1 小时'),
          value: () => [dayjs().subtract(1, 'hour').toDate(), dayjs().toDate()],
        },
        {
          text: t('近 12 小时'),
          value: () => [dayjs().subtract(12, 'hour').toDate(), dayjs().toDate()],
        },
        {
          text: t('今天'),
          value: () => [dayjs().startOf('day').toDate(), dayjs().endOf('day').toDate()],
        },
        {
          text: t('近 7 天'),
          value: () => [dayjs().subtract(6, 'day').startOf('day').toDate(), dayjs().endOf('day').toDate()],
        },
        {
          text: t('近 1 个月'),
          value: () => [dayjs().subtract(1, 'month').startOf('day').toDate(), dayjs().endOf('day').toDate()],
        },
        {
          text: t('近 3 个月'),
          value: () => [dayjs().subtract(3, 'month').startOf('day').toDate(), dayjs().endOf('day').toDate()],
        },
        {
          text: t('近 6 个月'),
          value: () => [dayjs().subtract(6, 'month').startOf('day').toDate(), dayjs().endOf('day').toDate()],
        },
      ],
    },
    showConfirmAndReset: true,
  },
  id: {
    component: markRaw(MultipleInput),
    popupProps: {
      attach: 'body',
      placement: 'bottom',
    },
    props: {
      placeholder: t('请输入 ID'),
    },
    showConfirmAndReset: true,
  },
  ip: {
    component: markRaw(MultipleInput),
    popupProps: {
      attach: 'body',
      placement: 'bottom',
    },
    props: {
      placeholder: t('请输入 IP'),
    },
    showConfirmAndReset: true,
  },
  shard: {
    component: markRaw(MultipleInput),
    popupProps: {
      attach: 'body',
      placement: 'bottom',
    },
    props: {
      placeholder: t('请输入分片名'),
    },
    showConfirmAndReset: true,
  },
  status: {
    component: markRaw(MultipleSelect),
    popupProps: {
      attach: 'body',
      placement: 'bottom',
    },
    props: {
      list: Object.entries(clusterInstStatus).map(([key, statusItem]) => ({
        label: statusItem.text,
        value: key,
      })),
    },
    showConfirmAndReset: true,
  },
} as const;

export const useInstanceColumnFilter = <T extends readonly string[] = Array<keyof typeof baseFilter>>(params: {
  cluster_id?: number;
  cluster_type: ClusterTypes;
  instance_attrs?: T;
}) => {
  const data = shallowRef<{
    [K in keyof typeof baseFilter | T[number]]: {
      component: any;
      popupProps: {
        attach: 'body';
        placement: 'bottom';
      };
      props: Record<string, any>;
      showConfirmAndReset?: boolean;
    };
  }>();

  const { loading, run: fetchBizInstanceAttrs } = useRequest(queryBizInstanceAttrs, {
    manual: true,
    onSuccess(result) {
      data.value = Object.keys(result).reduce(
        (res, attr) => {
          const getList = () => {
            const formatList = result[attr].map((item) => ({
              label: item.text,
              value: item.value,
            }));

            if (['bk_os_name', 'bk_sub_zone', 'version'].includes(attr)) {
              const filterList = formatList.filter((item) => item.value !== null && item.value !== '');
              if (filterList.length !== formatList.length) {
                return filterList.concat({
                  label: specialOptionLabelMap[SpecialOptions.EMPTY],
                  value: SpecialOptions.EMPTY,
                });
              }
              return filterList;
            }

            return formatList;
          };

          return Object.assign(res, {
            [attr]: {
              component: markRaw(MultipleSelect),
              popupProps: {
                attach: 'body',
                placement: 'bottom',
              },
              props: {
                list: getList(),
              },
              showConfirmAndReset: true,
            },
          });
        },
        {} as NonNullable<UnwrapRef<typeof data>>,
      );
      data.value = {
        ...baseFilter,
        ...data.value,
      };
    },
  });

  if (params.instance_attrs?.length) {
    const instanceParams = {
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      instances_attrs: params.instance_attrs?.join(','),
    };
    if (params.cluster_id) {
      Object.assign(instanceParams, { cluster_id: params.cluster_id });
    } else {
      Object.assign(instanceParams, {
        cluster_type:
          params.cluster_type === ClusterTypes.REDIS_CLUSTER ? clusterRedisTypeList.join(',') : params.cluster_type,
      });
    }
    fetchBizInstanceAttrs(instanceParams);
  } else {
    data.value = {
      ...(baseFilter as NonNullable<UnwrapRef<typeof data>>),
    };
  }

  return {
    data,
    loading,
  };
};
