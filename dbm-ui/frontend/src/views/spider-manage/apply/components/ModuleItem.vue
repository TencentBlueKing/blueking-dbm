<template>
  <BkFormItem
    :label="$t('DB模块')"
    property="details.db_module_id"
    required>
    <BkSelect
      v-model="moduleId"
      class="item-input"
      :clearable="false"
      filterable
      :input-search="false"
      :loading="isLoading"
      style="display: inline-block;"
      @change="fetchLevelConfig">
      <BkOption
        v-for="(item) in moduleList"
        :key="item.db_module_id"
        :label="item.name"
        :value="item.db_module_id" />
      <template #extension>
        <p
          v-bk-tooltips.top="{
            content: $t('请先选择所属业务'),
            disabled: hasBizId
          }">
          <BkButton
            class="create-module"
            :disabled="!hasBizId"
            text
            @click="handleToCreate">
            <i class="db-icon-plus-circle" />
            {{ $t('新建模块') }}
          </BkButton>
        </p>
      </template>
    </BkSelect>
    <span
      v-if="hasBizId"
      v-bk-tooltips.top="$t('刷新获取最新DB模块名')"
      class="refresh-module"
      @click="fetchModuleList">
      <i class="db-icon-refresh" />
    </span>
    <div
      v-if="moduleId"
      class="module-info">
      <BkLoading :loading="isLoadConfig">
        <div v-if="configItems.length">
          <div
            v-for="(item, index) in configItems"
            :key="index"
            class="module-info-item">
            <span class="module-info-label">{{ item.description || item.conf_name }}:</span>
            <span class="module-info-value">{{ item.conf_value }}</span>
          </div>
        </div>
        <!-- <div
          v-else
          class="no-items">
          {{ $t('该模块暂未绑定数据库相关配置') }}
          <span
            class="bind-module"
            @click="handleBindConfig">{{ isBindModule ? $t('已完成') : $t('去绑定') }}</span>
        </div> -->
        <div
          v-if="configItems.length === 0"
          class="bk-form-error mt-10">
          {{ $t('需要绑定数据库相关配置') }}
        </div>
      </BkLoading>
    </div>
  </BkFormItem>
</template>

<script setup lang="ts">
  import { useRequest } from 'vue-request';

  import { getModules } from '@services/source/cmdb';
  import { getLevelConfig } from '@services/source/configs';
  import type { ParameterConfigItem } from '@services/types/configs';

  interface Props {
    bizId: number | string,
  }

  const props = defineProps<Props>();
  const moduleId = defineModel({ required: true });

  const router = useRouter();

  const isLoadConfig = ref(false);
  const configItems = shallowRef<ParameterConfigItem[]>([]);
  const hasBizId = computed(() => Boolean(props.bizId));

  const {
    data: moduleList,
    loading: isLoading,
    run: fetchModules,
  } = useRequest(getModules, {
    manual: true,
  });

  watch(() => props.bizId, (bizId) => {
    bizId && fetchModuleList();
  }, { immediate: true });

  // 获取模块列表
  const fetchModuleList = () => {
    fetchModules({
      bk_biz_id: Number(props.bizId),
      cluster_type: 'tendbcluster',
    });
  };

  // 获取配置详情
  const fetchLevelConfig = (moduleId: number) => {
    const params = {
      bk_biz_id: Number(props.bizId),
      conf_type: 'deploy',
      level_name: 'module',
      level_value: moduleId,
      meta_cluster_type: 'tendbcluster',
      version: 'deploy_info',
    };
    isLoadConfig.value = true;
    getLevelConfig(params)
      .then((res) => {
        configItems.value = res.conf_items;
      })
      .finally(() => {
        isLoadConfig.value = false;
      });
  };

  // 创建模块
  const handleToCreate = () => {
    const routeLocation = router.resolve({
      name: 'createSpiderModule',
      params: {
        bizId: props.bizId,
      },
    });
    window.open(routeLocation.href, '__blank');
  };

  // // 绑定模块
  // const handleBindConfig = () => {
  //   if (isBindModule.value) {
  //     fetchLevelConfig(formdata.details.db_module_id as number);
  //     return;
  //   }
  //   const moduleInfo = fetchState.moduleList.find(item => item.db_module_id ===  formdata.details.db_module_id);
  //   const moduleName = moduleInfo?.name ?? '';
  //   const moduleNameQuery = moduleName ? { module_name: moduleName } : {};
  //   isBindModule.value = true;
  //   const url = router.resolve({
  //     name: 'SelfServiceBindDbModule',
  //     params: {
  //       type: props.type,
  //       bk_biz_id: formdata.bk_biz_id,
  //       db_module_id: formdata.details.db_module_id,
  //     },
  //     query: { ...moduleNameQuery },
  //   });
  //   window.open(url.href, '_blank');
  // };
</script>

<style lang="less" scoped>
.module-info {
  width: 398px;
  padding: 8px 12px;
  margin-top: 16px;
  font-size: @font-size-mini;
  line-height: 20px;
  background-color: @bg-gray;
  border-radius: 2px;

  .no-items {
    text-align: center;

    .bind-module {
      color: @primary-color;
      cursor: pointer;
    }
  }

  .module-info-label {
    display: inline-block;
    min-width: 100px;
    padding-right: 8px;
    text-align: right;
  }

  .module-info-value {
    color: @title-color;
  }
}

.create-module {
  display: block;
  width: 100%;
  padding: 0 8px;
  text-align: left;

  .db-icon-plus-circle {
    margin-right: 4px;
  }

  &:hover:not(.is-disabled) {
    color: @primary-color;
  }
}

.refresh-module {
  margin-left: 8px;
  font-size: @font-size-normal;
  color: @primary-color;
  vertical-align: middle;
  cursor: pointer;
}
</style>
