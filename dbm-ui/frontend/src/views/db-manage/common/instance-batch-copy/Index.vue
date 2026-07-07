<template>
  <BkDropdown
    class="instance-batch-copy"
    :popover-options="{
      clickContentAutoHide: true,
    }"
    trigger="click">
    <template #default="{ popoverShow }">
      <BkButton class="default-btn">
        {{ t('复制') }}{{ typeText }}
        <DbIcon
          class="ml-4"
          :class="{ 'is-show': popoverShow }"
          type="up-big" />
      </BkButton>
    </template>
    <template #content>
      <BkDropdownMenu class="dropdown-menu-with-button instance-batch-copy-menu">
        <BkDropdownItem>
          <BkButton
            v-bk-tooltips="{
              disabled: selected.length,
              content: t('请先勾选'),
              placement: 'right',
            }"
            :disabled="selected.length === 0"
            text
            @click="handleCopySelected">
            {{ t('已选') }}{{ typeText }}
          </BkButton>
        </BkDropdownItem>
        <BkDropdownItem>
          <BkButton
            text
            @click="handleCopyUnavailable">
            {{ t('异常') }}{{ typeText }}
          </BkButton>
        </BkDropdownItem>
        <BkDropdownItem>
          <BkButton
            text
            @click="handleCopyAll">
            {{ t('全部') }}{{ typeText }}
          </BkButton>
        </BkDropdownItem>
      </BkDropdownMenu>
    </template>
  </BkDropdown>
</template>

<script
  setup
  lang="ts"
  generic="
    T extends { instance_address: string; isUnavailable: boolean; ip: string } | { podName: string; node: string }
  ">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { execCopy, messageWarn } from '@utils';

  export interface Props<T> {
    field: 'instance_address' | 'ip' | 'podName' | 'node';
    getTableData: () => Promise<T[]>;
    selected: T[];
  }

  const props = defineProps<Props<T>>();

  const { t } = useI18n();

  const typeText = computed(() => (['ip', 'node'].includes(props.field) ? ' IP' : t('实例')));

  const handleCopy = (copyList: string[]) => {
    if (copyList.length === 0) {
      messageWarn('没有可复制数据');
      return;
    }
    execCopy(copyList.join('\n'), t('复制成功，共n条', { n: copyList.length }));
  };

  const handleCopySelected = () => {
    const copyList = _.uniq(props.selected.map((item) => item[props.field]));
    handleCopy(copyList);
  };

  const handleCopyUnavailable = async () => {
    const tableDataList = await props.getTableData();
    const copyList = _.uniq(tableDataList.filter((item) => item.isUnavailable).map((item) => item[props.field]));
    handleCopy(copyList);
  };

  const handleCopyAll = async () => {
    const tableDataList = await props.getTableData();
    const copyList = _.uniq(tableDataList.map((item) => item[props.field]));
    handleCopy(copyList);
  };
</script>

<style lang="less">
  .instance-batch-copy {
    .default-btn {
      width: 104px;
    }

    .is-show {
      transform: rotateZ(180deg);
      transition: all 0.15s;
    }
  }

  .instance-batch-copy-menu {
    .bk-dropdown-item {
      .bk-button {
        justify-content: flex-start;
      }
    }
  }
</style>
