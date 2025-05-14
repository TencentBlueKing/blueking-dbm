<template>
  <div class="tag-search-main">
    <div
      v-if="!isButtonMode"
      class="prefix-title">
      {{ t('标签') }}
    </div>
    <BkCascader
      v-model="searchValue"
      check-any-level
      filterable
      float-mode
      :list="dataList"
      multiple
      :placeholder="t('请选择或输入关键字搜索')"
      :scroll-height="392"
      separator=" : "
      :style="{ width: isButtonMode ? '108px' : '400px' }"
      trigger="click"
      @change="handleValueChange"
      @toggle="handlePanelToggle">
      <template
        v-if="isButtonMode"
        #trigger>
        <BkButton>
          <DbIcon type="tag-3" />
          <span class="ml-6">{{ t('标签搜索') }}</span>
        </BkButton>
      </template>
    </BkCascader>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { listTag } from '@services/source/tag';

  export interface TagSearchValue {
    tag_ids?: string;
    tag_keys?: string;
  }

  interface DataTye {
    children?: DataTye[];
    id: string | number;
    name: string;
  }

  interface Props {
    mode?: 'button' | 'select';
  }
  type Emits = (e: 'search', value: TagSearchValue) => void;

  const props = withDefaults(defineProps<Props>(), {
    mode: 'select',
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const isButtonMode = computed(() => props.mode === 'button');

  const dataList = ref<DataTye[]>([]);
  const searchValue = ref<[string, number][]>([]);

  let localSearchValue: [string, number][] = [];
  let keyValueMap: Record<string, DataTye[]> = {};

  const { run: fetchTagList } = useRequest(listTag, {
    manual: true,
    onSuccess(data) {
      keyValueMap = data.results.reduce<Record<string, DataTye[]>>((results, item) => {
        const keyInfo = {
          id: item.id,
          name: item.value,
        };
        if (results[item.key]) {
          results[item.key].push(keyInfo);
        } else {
          Object.assign(results, {
            [item.key]: [keyInfo],
          });
        }
        return results;
      }, {});

      dataList.value = Object.entries(keyValueMap).reduce<DataTye[]>((results, [key, children]) => {
        const keyItem = {
          children,
          id: key,
          name: key,
        };
        results.push(keyItem);
        return results;
      }, []);
    },
  });

  const handleFetchTagList = () => {
    fetchTagList({
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
      limit: -1,
      offset: 0,
      type: 'cluster',
    });
  };

  const handleSearch = () => {
    if (!localSearchValue.length && !searchValue.value.length) {
      return;
    }
    const keySet = new Set<string>();
    const tagsIds: number[] = [];
    searchValue.value.forEach((item) => {
      const [key, value] = item;
      if (key && value === undefined) {
        keySet.add(key);
        return;
      }

      if (!keySet.has(key)) {
        tagsIds.push(value);
      }
    });
    const queryObj = {};
    if (tagsIds.length) {
      Object.assign(queryObj, {
        tag_ids: tagsIds.join(','),
      });
    }
    if (keySet.size) {
      Object.assign(queryObj, {
        tag_keys: Array.from(keySet).join(','),
      });
    }
    emits('search', queryObj);
    localSearchValue = searchValue.value;
  };

  const handlePanelToggle = (isCollapse: boolean) => {
    if (isButtonMode.value && !isCollapse) {
      handleSearch();
    }
    if (isCollapse) {
      handleFetchTagList();
    }
  };

  const handleValueChange = () => {
    if (isButtonMode.value) {
      return;
    }

    handleSearch();
  };
</script>
<style lang="less" scoped>
  .tag-search-main {
    display: flex;

    .prefix-title {
      display: flex;
      width: 40px;
      height: 32px;
      font-size: 12px;
      color: #4d4f56;
      background: #fafbfd;
      border: 1px solid #c4c6cc;
      border-right: none;
      border-radius: 2px 0 0 2px;
      align-items: center;
      justify-content: center;
    }

    :deep(.bk-cascader) {
      border-bottom-left-radius: 0;
      border-top-left-radius: 0;

      &.is-focus {
        z-index: 99999;
      }
    }
  }
</style>
