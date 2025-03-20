<template>
  <div class="no_spec_ip_list">
    <div class="no_spec_ip_list-title">{{ t('无规格类型的 IP 共 n 个', { n: ipList.length }) }}：</div>
    <MultLineText>
      {{ ipList.join('，') }}
    </MultLineText>
    <div class="button-box">
      <BkButton
        v-bk-tooltips="t('复制')"
        class="copy-button ml-4"
        text
        theme="primary"
        @click="handleCopy">
        <DbIcon type="copy" />
      </BkButton>
      <BkButton
        v-bk-tooltips="t('跳转查看')"
        class="link-button ml-4"
        text
        theme="primary"
        @click="handleRedirect">
        <DbIcon type="link" />
      </BkButton>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { execCopy } from '@utils';

  import MultLineText from './components/MultLineText.vue';

  interface Props {
    ipList: string[];
  }

  const props = defineProps<Props>();

  const router = useRouter();
  const { t } = useI18n();

  const handleCopy = () => {
    execCopy(props.ipList.join('\n'), t('复制成功，共n条', { n: props.ipList.length }));
  };

  const handleRedirect = () => {
    const routeInfo = router.resolve({
      name: 'resourcePool',
      params: {
        page: 'host-list',
      },
      query: {
        hosts: props.ipList.join(','),
      },
    });
    window.open(routeInfo.href, '_blank');
  };
</script>

<style lang="less" scoped>
  .no_spec_ip_list {
    display: flex;
    padding: 8px 12px;
    font-size: 12px;
    background: #f0f1f5;
    border-radius: 2px;

    .no_spec_ip_list-title {
      font-weight: 700;
      color: #313238;
      flex-shrink: 0;
    }

    .button-box {
      flex-shrink: 0;

      .copy-button {
        font-size: 15px;
      }

      .link-button {
        font-size: 14px;
      }
    }
  }
</style>
