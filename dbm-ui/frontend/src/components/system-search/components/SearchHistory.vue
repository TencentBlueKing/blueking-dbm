<template>
  <div
    v-if="historyKeyWordList.length > 0"
    class="system-search-history">
    <div class="title">
      {{ t('历史记录') }}
    </div>
    <div class="wrapper">
      <div
        v-for="(item, index) in historyKeyWordList"
        :key="index"
        class="keyword-item"
        @click="handleSelect(item)">
        {{ item }}
        <DbIcon
          class="remote-btn"
          type="close"
          @click.stop="handleRemove(item)" />
      </div>
    </div>
    <div
      class="clear-btn"
      @click="handleClear">
      <DbIcon
        style="color: #979BA5"
        type="delete" />
      <span class="ml-4">{{ t('清空') }}</span>
    </div>
  </div>
  <div
    v-else
    style="padding-top: 145px">
    <BkException
      :description="t('请先输入关键词搜索')"
      scene="part"
      type="empty" />
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { shallowRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import { systemSearchCache } from '@common/cache';

  const { t } = useI18n();

  const modelValue = defineModel<string>({
    default: '',
    local: true,
  });

  const historyKeyWordList = shallowRef(systemSearchCache.getItem());

  const handleSelect = (str: string) => {
    modelValue.value = str;
  };

  const handleRemove = (str: string) => {
    historyKeyWordList.value = _.filter(historyKeyWordList.value, (item: string) => item !== str);
    systemSearchCache.setItem(historyKeyWordList.value);
  };

  const handleClear = () => {
    historyKeyWordList.value = [];
    systemSearchCache.setItem(historyKeyWordList.value);
  };
</script>
<style lang="less">
.system-search-history {
  position: relative;
  padding: 8px 16px;

  .title{
    padding-bottom: 7px;
    line-height: 16px;
    color: #313238;
    border-bottom: 1px solid #EAEBF0;
  }

  .wrapper{
    display: flex;
    padding-right: 80px;
    margin-top: 12px;
    flex-wrap: wrap;
  }

  .keyword-item{
    display: flex;
    height: 22px;
    padding: 0 8px;
    margin-bottom: 10px;
    color: #63656E;
    cursor: pointer;
    background: #F0F1F5;
    border-radius: 2px;
    align-items: center;
    justify-content: center;

    &:hover{
      background: #DCDEE5;
    }

    &:nth-child(n+1){
      margin-right: 8px;
    }

    .remote-btn{
      margin-left: 4px;
      font-size: 14px;

      &:hover{
        color: #3a84ff;
      }
    }
  }

  .clear-btn{
    position: absolute;
    top: 10px;
    right: 12px;
    font-size: 12px;
    color: #63656E;
    cursor: pointer;
  }
}
</style>
