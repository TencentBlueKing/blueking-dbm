<template>
  <TableColumn
    v-bind="{ ...attrs, ...props }"
    :title="title">
    <template #title="{ colIndex }: { colIndex: number }">
      <div class="info-table-column-copy-button">
        {{ title }}
        <span v-if="colIndex === 0 && tableContext?.props.data.length">({{ tableContext.props.data.length }})</span>
        <DbIcon
          v-if="getCopyValue"
          type="copy"
          @click="handleCopy" />
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
    // eslint-disable-next-line vue/no-unused-properties
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

  const handleCopy = () => {
    const dataList = tableContext!.props.data.flatMap((item) => {
      const formatValue = props.getCopyValue!(item);
      return _.isArray(formatValue) ? formatValue : [formatValue];
    });

    if (dataList.length > 0) {
      execCopy(
        _.uniq(dataList)
          .filter((item) => !_.isEmpty(item))
          .join('\n'),
        t('复制成功，共n条', { n: dataList.length }),
      );
    }
  };
</script>

<style lang="less">
  .info-table-column-copy-button {
    [class*='db-icon'] {
      margin-top: 1px;
      margin-left: 4px;
      color: @primary-color;
      cursor: pointer;
    }
  }
</style>
