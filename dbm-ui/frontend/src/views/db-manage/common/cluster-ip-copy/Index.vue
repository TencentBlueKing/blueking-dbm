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
              disabled: hasUnavailableIp,
              content: t('请先勾选'),
              placement: 'right',
            }"
            :disabled="!hasUnavailableIp"
            text
            @click="handleCopyUnavailableIp">
            {{ t('已选集群异常 IP') }}
          </BkButton>
        </BkDropdownItem>
      </BkDropdownMenu>
    </template>
  </BkDropdown>
</template>

<script setup lang="ts" generic="T extends { allIPList: string[]; allUnavailableIPList: string[] }">
  import { uniq } from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { useCopy } from '@hooks';

  interface Props {
    selected: T[];
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const copy = useCopy();

  const isCopyDropdown = ref(false);

  const hasUnavailableIp = computed(() => props.selected.some((dataItem) => dataItem.allUnavailableIPList.length > 0));

  /**
   * 复制已选集群 IP
   */
  const handleCopy = async () => {
    const copyList = uniq(
      props.selected.reduce((prevList, tableItem) => [...prevList, ...tableItem.allIPList], [] as string[]),
    );
    copy(copyList.join('\n'));
  };

  /**
   * 复制已选集群异常 IP
   */
  const handleCopyUnavailableIp = async () => {
    const copyList = uniq(
      props.selected.reduce((prevList, tableItem) => [...prevList, ...tableItem.allUnavailableIPList], [] as string[]),
    );
    copy(copyList.join('\n'));
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
