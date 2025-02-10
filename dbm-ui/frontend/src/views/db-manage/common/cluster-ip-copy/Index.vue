<template>
  <BkDropdown
    class="ml-8"
    @hide="() => (isCopyDropdown = false)"
    @show="() => (isCopyDropdown = true)">
    <BkButton
      class="w-86"
      :class="{ active: isCopyDropdown }">
      {{ t('复制') }}
      <DbIcon
        class="ml-4"
        type="up-big" />
    </BkButton>
    <template #content>
      <BkDropdownMenu ext-cls="cluster-ip-copy">
        <BkDropdownItem>
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
        </BkDropdownItem>
        <BkDropdownItem>
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
        </BkDropdownItem>
      </BkDropdownMenu>
    </template>
  </BkDropdown>
</template>

<script setup lang="ts" generic="T extends { allIPList: string[]; allUnavailableIPList: string[] }">
  import { Message } from 'bkui-vue';
  import { uniq } from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { execCopy } from '@utils';

  interface Props {
    selected: T[];
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const isCopyDropdown = ref(false);

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
        theme: 'primary',
        message: t('无异常IP可复制'),
      });
      return;
    }
    execCopy(copyList.join('\n'), t('复制成功，共n条', { n: copyList.length }));
  };
</script>

<style lang="less" scoped>
  .cluster-ip-copy {
    .bk-dropdown-item {
      padding: 0;

      .bk-button {
        height: 100%;
        padding: 0 16px;
      }
    }
  }
</style>
