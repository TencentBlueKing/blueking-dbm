import { useI18n } from 'vue-i18n';

type ITableFilter = Record<
  string,
  {
    component?: any;
    confirmEvents?: string[];
    list?:
      | {
          label: string;
          value: string;
        }[]
      | {
          children: {
            label: string;
            value: string;
          }[];
          label: string;
          value: string;
        }[];
    name: string;
    props?: Record<string, any>;
    showConfirmAndReset: boolean;
    type?: 'multiple' | 'single' | 'input';
  }
>;

export default () => {
  const { t } = useI18n();

  const tableFilter = computed<ITableFilter>(() => {
    return {
      key_class: {
        name: t('Key 模式'),
        popupProps: {
          attach: 'body',
          placement: 'bottom',
        },
        showConfirmAndReset: true,
        type: 'input',
      },
      key_type: {
        name: t('Key 类型'),
        popupProps: {
          attach: 'body',
          placement: 'bottom',
        },
        showConfirmAndReset: true,
        type: 'input',
      },
    };
  });

  return tableFilter;
};
