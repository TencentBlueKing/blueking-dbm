<template>
  <div class="result-head">
    <div class="head-item">
      <div class="head-item-title">{{ t('无权限的IP共n个', { n: privIpMap.noPriv.length }) }}</div>
      <template v-if="privIpMap.noPriv.length">
        ：
        <div class="head-item-ip">
          <MultLineText :line="3">
            {{ privIpMap.noPriv.join('，') }}
          </MultLineText>
        </div>
        <BkButton
          v-bk-tooltips="t('复制 IP')"
          class="ml-4 mt-2"
          style="flex-shrink: 0"
          text
          theme="primary"
          @click="handleIpCopy(privIpMap.noPriv.join('\n'))">
          <DbIcon type="copy" />
        </BkButton>
      </template>
    </div>
    <div class="head-item head-item-center mt-12">
      <span class="head-item-title">{{ t('有权限的IP共n个', { n: privIpMap.hasPriv.length }) }}</span>
      <template v-if="privIpMap.hasPriv.length">
        <BkButton
          v-bk-tooltips="t('复制 IP')"
          class="ml-4"
          text
          theme="primary"
          @click="handleIpCopy(privIpMap.hasPriv.join('\n'))">
          <DbIcon type="copy" />
        </BkButton>
        <BkButton
          v-bk-tooltips="t('导出结果表')"
          class="ml-4"
          text
          theme="primary"
          @click="handleExport">
          <DbIcon type="daochu-2" />
        </BkButton>
      </template>
      <BkRadioGroup
        v-model="formatType"
        style="margin-left: auto"
        type="capsule"
        @change="handleFormatTypeChange">
        <BkRadioButton label="ip">{{ t('IP 视角') }}</BkRadioButton>
        <BkRadioButton label="cluster">{{ t('域名视角') }}</BkRadioButton>
      </BkRadioGroup>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { getAccountPrivs } from '@services/source/mysqlPermissionAccount';

  import { useCopy } from '@hooks';

  import MultLineText from './components/MultLineText.vue';

  interface Props {
    data?: ServiceReturnType<typeof getAccountPrivs>;
  }
  interface Emits {
    (e: 'export'): void;
    (e: 'search'): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  const formatType = defineModel<string>({
    default: '',
  });

  const { t } = useI18n();
  const copy = useCopy();

  const privIpMap = computed(() => {
    const { data } = props;
    if (data) {
      const { no_priv: noPriv, has_priv: hasPriv } = data.results;
      return {
        noPriv: noPriv || [],
        hasPriv: hasPriv || [],
      };
    }
    return {
      noPriv: [],
      hasPriv: [],
    };
  });

  const handleIpCopy = (value: string) => {
    copy(value);
  };

  const handleFormatTypeChange = () => {
    emits('search');
  };

  const handleExport = () => {
    emits('export');
  };
</script>

<style lang="less" scoped>
  .result-head {
    .head-item {
      display: flex;
      align-items: flex-start;

      .head-item-title {
        flex-shrink: 0;
        font-size: 12px;
        font-weight: bolder;
        color: #313238;
      }

      .head-item-ip {
        font-size: 12px;
        color: #313238;
      }
    }

    .head-item-center {
      align-items: center;
    }
  }
</style>
