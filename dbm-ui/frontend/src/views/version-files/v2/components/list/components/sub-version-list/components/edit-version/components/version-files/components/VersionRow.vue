<template>
  <tr>
    <td>
      <div
        v-overflow-tips
        class="text-overflow">
        {{ data.name }}
      </div>
    </td>
    <td>
      <BkSelect
        v-model="localData.permit_os_type"
        :clearable="false"
        @change="(value)=> handleSystemChange(value)">
        <BkOption
          v-for="system in systemList"
          :disabled="selectedAllSystems.has(system.value) && selectedAllVersions[system.value]?.has('all')"
          :key="system.value"
          :label="system.label"
          :value="system.value" />
      </BkSelect>
    </td>
    <td>
      <BkSelect
        v-model="localData.permit_os"
        all-option-id="all"
        class="version-permit-os-select"
        filterable
        multiple
        multiple-mode="tag"
        show-all
        @change="handleVersionChange"
        @toggle="handleVersionToggle">
        <template #trigger>
          <div
            class="version-display-trigger"
            :class="{ 'is-active': isShowVersionPanel }">
            <div class="display-main">
              <template v-if="existVersionList.length > 0 || localData.permit_os.length > 0">
                <div
                  v-for="version in existVersionList"
                  :key="version"
                  class="fixed-tag-main">
                  <div class="text-content">{{ version }}</div>
                  <DbIcon
                    v-bk-tooltips="t('该版本已被应用，无法删除')"
                    class="close-icon"
                    type="close" />
                </div>
                <div
                  v-for="(version, index) in localData.permit_os"
                  :key="version"
                  class="closable-tag-main">
                  <div class="text-content">
                    <DbIcon
                      v-if="version === 'all'"
                      class="mr-4"
                      type="quanbu-xuanzhong" />
                    <span>{{ version === 'all' ? t('全部') : version }}</span>
                  </div>
                  <DbIcon
                    class="close-icon"
                    type="close"
                    @click.stop="handleVersionDelete(index)" />
                </div>
              </template>
              <div
                v-else
                class="placeholder">
                {{ t('请选择版本') }}
              </div>
            </div>
            <div class="icon-main">
              <DbIcon
                class="trigger-icon"
                type="down-big" />
            </div>
          </div>
        </template>
        <BkOption
          v-for="version in versionList"
          :disabled="selectedAllVersions[localData.permit_os_type]?.has(version.value)"
          :key="version.value"
          :label="version.label"
          :value="version.value" />
      </BkSelect>
    </td>
    <td>
      <DbIcon
        v-bk-tooltips="{
          content: !ableToDelete ? t('至少保留1个版本文件') : t('该版本已被应用，无法删除'),
          disabled: ableToDelete && !isApplied,
        }"
        class="version-row-delete-icon"
        :class="{ 'is-disabled': !ableToDelete || isApplied }"
        type="delete"
        @click="handleDelete" />
    </td>
  </tr>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { listSupportSystems } from '@services/source/package';

  interface Props {
    ableToDelete?: boolean;
    data: {
      id?: number;
      md5: string;
      name: string;
      path: string;
      permit_os?: string[];
      permit_os_type?: string;
      size: number;
    };
    isApplied?: boolean;
    selectedSystems: Set<string>;
    selectedVersions: Record<string, Set<string>>;
  }

  interface Emits {
    (e: 'delete'): void;
    (e: 'systemVersionChange'): void;
  }

  interface Exposes {
    getSelectedSystem: () => string;
    getSelectedVersions: () => string[];
    getValue: () => Props['data'] & typeof localData.value;
  }

  const props = withDefaults(defineProps<Props>(), {
    ableToDelete: true,
    isApplied: false,
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const localData = ref({
    permit_os: [] as string[],
    permit_os_type: '',
  });
  const isShowVersionPanel = ref(false);
  const existVersionList = ref<string[]>([]);
  const systemList = ref<{ label: string; value: string }[]>([]);
  const versionList = ref<typeof systemList.value>([]);
  const selectedAllSystems = ref<Set<string>>(new Set());
  const selectedAllVersions = ref<Record<string, Set<string>>>({});

  let supportSystems: Record<string, string[]> = {};

  useRequest(listSupportSystems, {
    onSuccess(data) {
      supportSystems = data;
      systemList.value = Object.keys(data).map((item) => ({
        label: item,
        value: item,
      }));
    },
  });

  watch(
    () => [props.data, systemList.value, props.isApplied],
    () => {
      if (props.data && props.isApplied && systemList.value.length > 0) {
        localData.value.permit_os = [];
        existVersionList.value = props.data.permit_os!.slice();
      } else {
        existVersionList.value = [];
      }

      if (props.data) {
        if (!props.data.permit_os) {
          localData.value.permit_os = [];
        } else {
          localData.value.permit_os = props.data.permit_os.length ? props.data.permit_os : ['all'];
        }
        localData.value.permit_os_type = props.data.permit_os_type || '';
        if (localData.value.permit_os_type) {
          setTimeout(() => {
            handleSystemChange(localData.value.permit_os_type, true);
          });
        }
      }
    },
    {
      immediate: true,
    },
  );

  watch(
    () => [props.selectedSystems, props.selectedVersions],
    () => {
      nextTick(() => {
        selectedAllSystems.value = props.selectedSystems;
        selectedAllVersions.value = props.selectedVersions;
        if (localData.value.permit_os.length > 0) {
          if (props.selectedVersions[localData.value.permit_os_type]?.has('all') && !localData.value.permit_os.includes('all')) {
            localData.value.permit_os_type = '';
            localData.value.permit_os = [];
            versionList.value = [];
            emits('systemVersionChange');
            return;
          }

          const localSelectedVersions = _.cloneDeep(props.selectedVersions);
          if (localSelectedVersions[localData.value.permit_os_type]?.size > 0) {
            localData.value.permit_os.forEach(item => {
              localSelectedVersions[localData.value.permit_os_type].delete(item);
            })
          }
          selectedAllVersions.value = localSelectedVersions;
        }
      });
    },
    {
      immediate: true,
    },
  );

  const handleSystemChange = (value: string, isInit = false) => {
    nextTick(() => {
      emits('systemVersionChange');
    });
    if (existVersionList.value.length > 0) {
      const exisetVersionSet = new Set(existVersionList.value);
      versionList.value = supportSystems[value].reduce<{ label: string; value: string }[]>((result, item) => {
        if (!exisetVersionSet.has(item)) {
          result.push({
            label: item,
            value: item,
          });
        }
        return result;
      }, []);
      return;
    }
    versionList.value = supportSystems[value]?.map((item) => ({
      label: item,
      value: item,
    }));
    if (!isInit) {
      localData.value.permit_os = [];
    }
  };

  const handleVersionChange = () => {
    nextTick(() => {
      emits('systemVersionChange');
    });
  };

  const handleDelete = () => {
    if (props.ableToDelete && !props.isApplied) {
      emits('delete');
    }
  };

  const handleVersionToggle = (isShow: boolean) => {
    isShowVersionPanel.value = isShow;
  };

  const handleVersionDelete = (index: number) => {
    localData.value.permit_os.splice(index, 1);
    nextTick(() => {
      emits('systemVersionChange');
    });
  };

  defineExpose<Exposes>({
    getSelectedSystem() {
      return localData.value.permit_os_type;
    },
    getSelectedVersions() {
      return [...localData.value.permit_os, ...existVersionList.value];
    },
    getValue() {
      return {
        ...props.data,
        ...localData.value,
        permit_os: [...localData.value.permit_os, ...existVersionList.value],
      };
    },
  });
</script>
<style lang="less">
  .version-display-trigger {
    display: flex;
    height: 32px;
    padding-left: 8px;
    cursor: pointer;
    background: #fff;
    border: 1px solid #c4c6cc;
    border-radius: 2px;
    align-items: center;

    &:hover {
      border-color: #979ba5;
    }

    &.is-active {
      border-color: #3a84ff;

      .icon-main {
        .trigger-icon {
          transform: rotate(180deg);
          transition: transform 0.4s;
        }
      }
    }

    &.is-disabled {
      cursor: not-allowed;
      background-color: #fafbfd;
      border-color: #dcdee5;
    }

    .display-main {
      flex: 1;
      display: flex;
      flex-wrap: wrap;
      padding: 4px 0;
      gap: 4px;

      .placeholder {
        height: 20px;
        font-size: 12px;
        line-height: 20px;
        color: #c4c6cc;
      }

      .fixed-tag-main,
      .closable-tag-main {
        display: flex;
        height: 22px;
        padding: 0 3px 0 8px;
        background: #f0f1f5;
        border-radius: 2px;
        align-items: center;

        .text-content {
          flex: 1;
          max-width: 200px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .close-icon {
          margin-left: 2px;
          font-size: 16px;
          color: #dcdee5;
          cursor: not-allowed;
        }
      }

      .closable-tag-main {
        .close-icon {
          color: #979ba5;
          cursor: pointer;
        }
      }
    }

    .icon-main {
      padding-right: 8px;
      font-size: 13px;
      color: #979ba5;

      .trigger-icon {
        display: inline-block;
      }
    }
  }

  .version-row-delete-icon {
    font-size: 13px;
    color: #979ba5;
    cursor: pointer;

    &.is-disabled {
      color: #c4c6cc;
      cursor: not-allowed;
    }
  }

  .bk-form-item {
    &.is-error {
      .version-display-trigger {
        border-color: #ea3636;
      }
    }
  }
</style>
