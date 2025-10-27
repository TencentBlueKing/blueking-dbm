import dayjs from 'dayjs';
import { markRaw, shallowRef, type UnwrapRef } from 'vue';
import { useRequest } from 'vue-request';

import { queryBizClusterAttrs } from '@services/source/dbbase';
import { listTag } from '@services/source/tag';
import { getUserList } from '@services/source/user';

import { ClusterTypes } from '@common/const';

import DatetimeRange from '@components/db-table/components/DatetimeRange.vue';
import MultCascader from '@components/db-table/components/MultCascader.vue';
import MultipleInput from '@components/db-table/components/MultipleInput.vue';
import MultipleSelect from '@components/db-table/components/MultipleSelect.vue';

import { t } from '@/locales';

export const baseFilter = {
  cluster_ids: {
    component: markRaw(MultipleInput),
    popupProps: {
      attach: 'body',
      placement: 'bottom',
    },
    showConfirmAndReset: true,
  },
  create_at: {
    component: markRaw(DatetimeRange),
    name: t('申请时间'),
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
  creator: {
    component: markRaw(MultipleSelect),
    popupProps: {
      attach: 'body',
      placement: 'bottom',
    },
    props: {
      remoteMethod: (params: { defaultValue?: string; keyword?: string }) => {
        const requestParams = {};
        if (params.defaultValue) {
          Object.assign(requestParams, { exact_lookups: params.defaultValue });
        }
        if (params.keyword) {
          Object.assign(requestParams, { fuzzy_lookups: params.keyword });
        }
        return getUserList(requestParams).then((res) =>
          res.results.map((item) => ({
            label: `${item.username} (${item.display_name})`,
            value: item.username,
          })),
        );
      },
      remoteSearch: true,
    },
    showConfirmAndReset: true,
  },
  domain: {
    component: markRaw(MultipleInput),
    popupProps: {
      attach: 'body',
      placement: 'bottom',
    },
    showConfirmAndReset: true,
  },
  name: {
    component: markRaw(MultipleInput),
    popupProps: {
      attach: 'body',
      placement: 'bottom',
    },
    showConfirmAndReset: true,
  },
  slave_domain: {
    component: markRaw(MultipleInput),
    popupProps: {
      attach: 'body',
      placement: 'bottom',
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
      list: [
        {
          label: t('正常'),
          value: 'normal',
        },
        {
          label: t('异常'),
          value: 'abnormal',
        },
      ],
    },
    showConfirmAndReset: true,
  },
  tag: {
    component: markRaw(MultCascader),
    popupProps: {
      attach: 'body',
      placement: 'bottom',
    },
    props: {
      checkStrictly: true,
      remoteMethod: () =>
        listTag(
          {
            bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
            limit: -1,
            offset: 0,
            type: 'cluster',
          },
          {
            cache: true,
          },
        ).then((data) => {
          const keyValueMap: Record<string, { label: string; value: string }[]> = {};
          data.results.forEach((item) => {
            if (!keyValueMap[item.key]) {
              keyValueMap[item.key] = [];
            }
            keyValueMap[item.key].push({
              label: item.value,
              value: `tag_ids=${item.id}`,
            });
          });

          return Object.keys(keyValueMap).map((tagKey) => ({
            children: keyValueMap[tagKey],
            label: tagKey,
            value: `tag_keys=${tagKey}`,
          }));
        }),
      showAllLevels: true,
    },
    showConfirmAndReset: true,
  },
} as const;

export const useClusterColumnFilter = <T extends readonly string[] = Array<keyof typeof baseFilter>>(params: {
  cluster_attrs?: T;
  cluster_type: ClusterTypes;
  instances_attrs?: T;
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

  const { loading, run: fetchBizClusterAttrs } = useRequest(queryBizClusterAttrs, {
    manual: true,
    onSuccess(result) {
      data.value = Object.keys(result).reduce(
        (res, attr) => {
          return Object.assign(res, {
            [attr]: {
              component: markRaw(MultipleSelect),
              popupProps: {
                attach: 'body',
                placement: 'bottom',
              },
              props: {
                list: result[attr].map((item) => ({
                  label: attr === 'bk_cloud_id' ? `${item.text}[${item.value}]` : item.text,
                  value: item.value,
                })),
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

  if (params.cluster_attrs?.length || params.instances_attrs?.length) {
    fetchBizClusterAttrs({
      ...params,
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      cluster_attrs: params.cluster_attrs?.join(','),
      cluster_type:
        params.cluster_type === ClusterTypes.REDIS
          ? [
              ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
              ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
              ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
              ClusterTypes.PREDIXY_REDIS_CLUSTER,
            ].join(',')
          : params.cluster_type,
      instances_attrs: params.instances_attrs?.join(''),
    });
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
