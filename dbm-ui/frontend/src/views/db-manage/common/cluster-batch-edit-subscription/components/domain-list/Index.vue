<template>
  <div class="result-preview-main">
    <div class="title-main">
      <div class="title">{{ t('已选集群') }}</div>
      <BkDropdown>
        <DbIcon
          class="more-trigger"
          type="more" />
        <template #content>
          <BkDropdownMenu>
            <BkDropdownItem @click="handleClearAll">
              {{ t('清空所有') }}
            </BkDropdownItem>
            <BkDropdownItem @click="handleCopyAll">
              {{ t('复制所有集群') }}
            </BkDropdownItem>
          </BkDropdownMenu>
        </template>
      </BkDropdown>
    </div>
    <BkException
      v-if="isEmpty"
      class="mt-50"
      :description="t('暂无数据，请先添加对象')"
      scene="part"
      type="empty" />
    <div
      v-else
      class="list-main">
      <template
        v-for="[key, list] in Object.entries(selectedMap)"
        :key="key">
        <CollapseMini
          v-if="list.length > 0"
          collapse
          :count-info="getCoountInfo(list)"
          :show-update="showUpdate"
          :title="key">
          <div
            v-for="(item, index) in list"
            :key="item.clusterDomian"
            class="result-item">
            <div
              v-overflow-tips
              class="domain-display text-overflow">
              {{ item.clusterDomian }}
            </div>
            <BkTag
              v-if="showUpdate"
              class="status-tag"
              :class="{ 'is-ignore': item.isIgnore }"
              size="small"
              :theme="getTheme(item)">
              {{ getTagText(item) }}
            </BkTag>
            <DbIcon
              class="copy-icon"
              type="copy"
              @click="() => execCopy(item.clusterDomian)" />
            <DbIcon
              class="remove-icon"
              type="close"
              @click="() => handleDeleteItem(key, index)" />
          </div>
        </CollapseMini>
      </template>
    </div>
  </div>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import { execCopy } from '@utils';

  import CollapseMini from './components/CollapseMini.vue';

  export interface DomainInfo {
    clusterDomian: string;
    clusterType: string;
    isIgnore?: boolean;
    isNew?: boolean;
  }

  interface Props {
    showUpdate?: boolean;
  }

  type Emits = (e: 'delete', domain: string) => void;

  withDefaults(defineProps<Props>(), {
    showUpdate: true,
  });

  const emits = defineEmits<Emits>();

  const selectedMap = defineModel<Record<string, DomainInfo[]>>({
    default: () => ({}),
  });

  const { t } = useI18n();

  // 选中结果是否为空
  const isEmpty = computed(() => _.every(Object.values(selectedMap.value), (item) => item.length === 0));

  const getTheme = (item: DomainInfo) => {
    if (item.isIgnore) {
      return '';
    }

    return item.isNew ? 'success' : 'warning';
  };

  const getTagText = (item: DomainInfo) => {
    if (item.isIgnore) {
      return t('忽略');
    }

    return item.isNew ? t('新增') : t('更新');
  };

  const getCoountInfo = (list: DomainInfo[]) => {
    const total = list.length;
    let isNewCount = 0;
    let isIgnoreCount = 0;
    list.forEach((item) => {
      if (item.isNew) {
        isNewCount++;
      }
      if (item.isIgnore) {
        isIgnoreCount++;
      }
    });
    return {
      add: isNewCount,
      ignore: isIgnoreCount,
      total,
      update: total - isNewCount - isIgnoreCount,
    };
  };

  const handleDeleteItem = (key: string, index: number) => {
    const domain = selectedMap.value[key][index].clusterDomian;
    selectedMap.value[key].splice(index, 1);
    emits('delete', domain);
  };

  const handleClearAll = () => {
    selectedMap.value = {};
    emits('delete', '');
  };

  const handleCopyAll = () => {
    const domains = Object.values(selectedMap.value).flat();
    execCopy(domains.join('\n'));
  };
</script>

<style lang="less" scoped>
  .result-preview-main {
    display: flex;
    height: 600px;
    overflow: hidden;
    font-family: MicrosoftYaHei, Arial, sans-serif;
    background-color: #f5f6fa;
    flex-direction: column;

    .title-main {
      display: flex;
      height: 40px;
      padding: 0 10px 0 24px;
      background: #fff;
      border-bottom: 1px solid #dcdee5;
      align-items: center;
      justify-content: space-between;

      .title {
        font-size: 12px;
        font-weight: 700;
        color: #313238;
      }

      .more-trigger {
        font-size: 16px;
        color: #979ba5;
        cursor: pointer;
      }
    }

    .list-main {
      padding: 0 16px;
      overflow-y: auto;
      font-family: ArialMT, Arial, sans-serif;
      color: #4d4f56;
      flex: 1;

      .result-item {
        display: flex;
        height: 32px;
        padding: 0 8px 0 12px;
        margin-bottom: 2px;
        cursor: pointer;
        background-color: #fff;
        border-radius: 2px;
        align-items: center;

        .domain-display {
          flex: 1;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
          user-select: none;
        }

        .is-ignore {
          color: #75a646;
          background-color: #ecf6d0;
        }

        .remove-icon,
        .copy-icon {
          display: none;
          font-size: 18px;
          color: #1768ef;
          cursor: pointer;
        }

        .copy-icon {
          margin-right: 6px;
          font-size: 12px;
        }

        &:hover {
          background-color: #e1ecff;

          .status-tag {
            display: none;
          }

          .remove-icon,
          .copy-icon {
            display: block;
          }
        }
      }
    }
  }
</style>
