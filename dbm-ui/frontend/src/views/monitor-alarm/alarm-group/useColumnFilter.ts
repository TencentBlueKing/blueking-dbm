import { markRaw, shallowRef } from 'vue';

import NoticGroupModel from '@services/model/notice-group/notice-group';
import { getUserList } from '@services/source/user';

import MultipleSelect from '@components/db-table/components/MultipleSelect.vue';

export const useColumnFilter = () => {
  const baseFilter = {
    name: {
      popupProps: {
        attach: 'body',
        placement: 'bottom',
      },
      showConfirmAndReset: true,
    },
    notice_ways: {
      component: markRaw(MultipleSelect),
      popupProps: {
        attach: 'body',
        placement: 'bottom',
      },
      props: {
        list: NoticGroupModel.NoticeMethodList.map((item) => ({
          label: item.label,
          value: item.type,
        })),
      },
      showConfirmAndReset: true,
    },
    receivers: {
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
  } as const;

  const data = shallowRef({ ...baseFilter });

  return {
    data,
  };
};
