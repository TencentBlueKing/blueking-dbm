<template>
  <DbDropdown>
    <template #default="{ popoverShow }">
      <BkButton
        class="cluster-ip-copy-button w-86"
        :class="{ active: popoverShow }">
        {{ t('复制') }}
        <DbIcon
          class="cluster-ip-copy-icon ml-4"
          type="up-big" />
      </BkButton>
    </template>
    <template #content>
      <DbDropdownMenu class="dropdown-menu-with-button cluster-ip-copy">
        <DbDropdownItem>
          <BkButton
            v-bk-tooltips="{
              disabled: selected.length,
              content: t('请先勾选'),
              placement: 'right',
            }"
            :disabled="selected.length === 0"
            text
            @click="handleCopy">
            {{ t('已选集群 IP') }}
          </BkButton>
        </DbDropdownItem>
        <DbDropdownItem>
          <BkButton
            v-bk-tooltips="{
              disabled: selected.length,
              content: t('请先勾选'),
              placement: 'right',
            }"
            :disabled="selected.length === 0"
            text
            @click="handleCopyUnavailableIp">
            {{ t('已选集群的异常 IP') }}
          </BkButton>
        </DbDropdownItem>
      </DbDropdownMenu>
    </template>
  </DbDropdown>
</template>

<script setup lang="ts" generic="T extends { allIPList: string[]; allUnavailableIPList: string[] }">
  import { Message } from 'bkui-vue';
  import { uniq } from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { execCopy } from '@utils';

  export interface Props<T> {
    selected: T[];
  }

  const props = defineProps<Props<T>>();

  const { t } = useI18n();

  /**
   * 复制已选集群 IP
   */
  const handleCopy = async () => {
    const copyList = uniq(
      props.selected.reduce((prevList, tableItem) => [...prevList, ...tableItem.allIPList], [] as string[]),
    );
    execCopy(copyList.join('\n'), t('复制成功，共n条', { n: copyList.length }));
  };

  /**
   * 复制已选集群异常 IP
   */
  const handleCopyUnavailableIp = async () => {
    const copyList = uniq(
      props.selected.reduce((prevList, tableItem) => [...prevList, ...tableItem.allUnavailableIPList], [] as string[]),
    );
    if (copyList.length === 0) {
      Message({
        message: t('无异常IP可复制'),
        theme: 'primary',
      });
      return;
    }
    execCopy(copyList.join('\n'), t('复制成功，共n条', { n: copyList.length }));
  };
</script>

<style lang="less">
  .cluster-ip-copy-button {
    .cluster-ip-copy-icon {
      transition: all 0.2s;
    }

    // 展开时箭头翻转，与 dropdown-export-excel 一致
    &.active:not(.is-disabled) {
      .cluster-ip-copy-icon {
        transform: rotate(180deg);
      }
    }
  }

  .cluster-ip-copy {
    .dbm-dropdown-item {
      .bk-button {
        justify-content: flex-start;
      }
    }
  }
</style>
