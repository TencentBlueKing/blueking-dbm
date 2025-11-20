<template>
  <TableColumn
    v-bind="{ ...attrs }"
    :col-key="colKey"
    resizable
    :title="title">
    <template #title>
      <div class="info-table-column-copy-button">
        <span>{{ title }}</span>
        <template v-if="getCopyValue">
          <span>{{ t('（共 n 个）', [copyDataList.length]) }}</span>
          <DbIcon
            type="copy"
            @click="handleCopy" />
        </template>
      </div>
    </template>
    <template
      v-if="slots.default"
      #default="defaultParams">
      <slot v-bind="defaultParams" />
    </template>
  </TableColumn>
</template>

<script setup lang="ts">
  import _ from 'lodash';
  import type { ComponentSlots } from 'vue-component-type-helpers';
  import { useI18n } from 'vue-i18n';

  import { TableColumn } from '@blueking/tdesign-ui';

  import { execCopy } from '@utils';

  import { TicketDetailTableKey } from './Index.vue';

  export interface Props {
    colKey: string;
    getCopyValue?: (item: any) => string | string[];
    title: string;
  }

  const props = defineProps<Props>();
  const slots = defineSlots<{
    default?: ComponentSlots<typeof TableColumn>['default'];
  }>();

  const attrs = useAttrs();

  const tableContext = inject(TicketDetailTableKey);

  const { t } = useI18n();

  const copyDataList = props.getCopyValue
    ? _.uniq(
        tableContext!.props.data.flatMap((item) => {
          const formatValue = props.getCopyValue!(item);
          return _.isArray(formatValue) ? formatValue : [formatValue];
        }),
      ).filter((item) => !_.isEmpty(item))
    : [];

  const handleCopy = () => {
    execCopy(
      _.uniq(copyDataList)
        .filter((item) => !_.isEmpty(item))
        .join('\n'),
      t('复制成功，共n条', { n: copyDataList.length }),
    );
  };
</script>

<style lang="less">
  .info-table-column-copy-button {
    [class*='db-icon'] {
      font-size: 14px;
      // margin-left: 4px;
      color: #979ba5;
      cursor: pointer;

      &:hover {
        color: #3a84ff;
      }
    }
  }
</style>
