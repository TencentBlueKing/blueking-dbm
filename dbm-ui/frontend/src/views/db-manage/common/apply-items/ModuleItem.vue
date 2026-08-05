<template>
  <BkFormItem
    ref="moduleRef"
    class="apply-module-item"
    :description="t('DB 参数模块是一个管理单元，用于标识一组使用了相同数据库配置（版本、字符集等）的集群')"
    :label="t('DB参数模块')"
    property="details.db_module_id"
    required
    :rules="rules">
    <BkSelect
      v-model="modelValue"
      class="item-input"
      :clearable="false"
      filterable
      :input-search="false"
      :loading="moduleLoading"
      :no-data-text="t('当前业务下暂无可用模块，请联系 DBA 创建')"
      style="display: inline-block">
      <BkOption
        v-for="item in sortedModuleList"
        :id="item.db_module_id"
        :key="item.db_module_id"
        :name="item.alias_name">
        <div class="apply-module-item-moudle-option">
          <span class="moudle-option-label">
            <BkOverflowTitle type="tips">{{ item.alias_name }}</BkOverflowTitle>
          </span>
          <span class="moudle-opiton-info ml-4">
            {{ getBaseInfo(item) }}
          </span>
        </div>
      </BkOption>
      <template
        v-if="hasEditPermission && bizId && clusterType !== ClusterTypes.RIAK"
        #extension>
        <div
          :key="bizId"
          v-bk-tooltips.top="{
            content: t('请先选择所属业务'),
            disabled: !!bizId,
          }"
          style="padding: 0 12px">
          <BkButton
            class="create-module"
            :disabled="!bizId"
            text
            @click="handleCreateModule">
            <DbIcon
              class="mr-4"
              type="plus-circle" />
            {{ t('新建模块') }}
          </BkButton>
        </div>
      </template>
    </BkSelect>
    <BkButton
      v-if="bizId"
      v-bk-tooltips.top="t('刷新获取最新DB模块名')"
      class="ml-8"
      text
      @click="fetchModuleList">
      <DbIcon type="refresh" />
    </BkButton>
    <div
      v-if="modelValue && dbType !== DBTypes.RIAK"
      class="config-detail">
      <BkLoading :loading="levelConfigLoading">
        <div v-if="configItemList.length">
          <div
            v-for="(item, index) in configItemList"
            :key="index"
            class="config-detail-item">
            <span
              class="config-detail-label"
              :class="{ 'has-description': item.hasDescription }">
              {{ item.label }}:
            </span>
            <span class="config-detail-value">{{ item.value }}</span>
          </div>
        </div>
        <template v-else-if="dbType !== DBTypes.TENDBCLUSTER">
          <div class="no-items">
            {{ t('该模块暂未绑定数据库相关配置') }}
            <span
              class="bind-module"
              @click="handleBindConfig">
              {{ isBindModule ? t('已完成') : t('去绑定') }}
            </span>
          </div>
          <!-- <div class="bk-form-error mt-10">
            {{ t('需要绑定数据库相关配置') }}
          </div> -->
        </template>
      </BkLoading>
    </div>
  </BkFormItem>
</template>

<script setup lang="ts">
  import { Form } from 'bkui-vue';
  import { computed, type UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getModules } from '@services/source/cmdb';
  import { getLevelConfig } from '@services/source/configs';

  import { clusterTypeInfos, ClusterTypes, DBTypes, TicketTypes } from '@common/const';

  import useBase from '@components/auth-component/use-base';

  interface Props {
    bizId: number | '';
    clusterType: ClusterTypes;
  }

  const props = defineProps<Props>();

  const modelValue = defineModel<number | null>({
    required: true,
  });
  const moduleAliasName = defineModel<string>('moduleAliasName');
  const moduleLevelConfig = defineModel<{
    charset: string;
    dbVersion: string;
    systemVersionList: string[];
  }>('moduleLevelConfig');

  const route = useRoute();
  const router = useRouter();
  const { t } = useI18n();

  const { dbType } = clusterTypeInfos[props.clusterType];

  // 判断是否有 dbconfig_edit 权限（使用与 AuthButton 相同的逻辑）
  const { isShowRaw: hasEditPermission } = useBase({
    actionId: 'dbconfig_edit',
    permission: 'normal',
    resource: dbType,
  });

  const rules = [
    {
      message: t('请先选择所属业务'),
      trigger: 'blur',
      validator: () => Boolean(props.bizId),
    },
    {
      message: t('DB模块名不能为空'),
      trigger: 'blur',
      validator: (value: number) => Boolean(value),
    },
    {
      message: t('需要绑定数据库相关配置'),
      trigger: 'blur',
      validator: () => {
        if ([DBTypes.MYSQL, DBTypes.SQLSERVER].includes(dbType)) {
          return isBindModule.value;
        }
        return true;
      },
    },
  ];

  const moduleRef = ref<InstanceType<typeof Form.FormItem>>();
  const isBindModule = ref(false);

  /**
   * 自然序排序比较函数（将字符串中的数字按数值比较）
   */
  const naturalSort = (a: string, b: string) => a.localeCompare(b, undefined, { numeric: true });

  const sortedModuleList = computed(() => {
    const list = moduleList.value || [];
    return [...list].sort((a, b) => naturalSort(a.alias_name, b.alias_name));
  });

  const configItemList = computed(() => {
    const confItems = levelConfigData.value?.conf_items || [];
    if (!confItems.length) {
      return [];
    }

    if (dbType === DBTypes.SQLSERVER) {
      const labelMap: Record<string, string> = {
        buffer_percent: t('实例内存分配比例'),
        charset: t('字符集'),
        db_version: t('数据库版本'),
        max_remain_mem_gb: t('最大系统保留内存'),
        sync_type: t('主从方式'),
        system_version: t('操作系统版本'),
      };

      if (confItems) {
        const configMap: Record<string, string | undefined> = {};
        confItems.forEach((configItemList) => {
          const { conf_name: configName, conf_value: confValue } = configItemList;
          switch (configName) {
            case 'buffer_percent':
              configMap[configName] = `${confValue}%`;
              break;
            case 'charset':
              configMap[configName] = confValue;
              break;
            case 'db_version':
              configMap[configName] = confValue;
              break;
            case 'max_remain_mem_gb':
              configMap[configName] = `${confValue}GB`;
              break;
            case 'sync_type':
              configMap[configName] = confValue === 'mirroring' ? t('镜像') : 'always on';
              break;
            case 'system_version':
              configMap[configName] = confValue;
              break;
          }
        });

        return ['db_version', 'charset', 'system_version', 'buffer_percent', 'max_remain_mem_gb', 'sync_type'].map(
          (key) => ({
            hasDescription: !!configMap[key],
            label: labelMap[key],
            value: configMap[key],
          }),
        );
      }
    }
    return confItems.map((confItem) => ({
      hasDescription: !!confItem.description,
      label: confItem.description || confItem.conf_name,
      value: confItem.conf_value,
    }));
  });

  const {
    data: moduleList,
    loading: moduleLoading,
    run: runGetModules,
  } = useRequest(getModules, {
    manual: true,
  });

  const {
    data: levelConfigData,
    loading: levelConfigLoading,
    run: runGetLevelConfig,
  } = useRequest(getLevelConfig, {
    manual: true,
    onSuccess(levelConfigResult) {
      isBindModule.value = levelConfigResult.conf_items.length > 0;
      moduleRef.value!.clearValidate();
    },
  });

  const fetchModuleList = () => {
    runGetModules({
      bk_biz_id: Number(props.bizId),
      cluster_type: props.clusterType,
    });
  };

  const fetchLevelConfig = () => {
    if (modelValue.value && props.bizId) {
      const params = {
        bk_biz_id: props.bizId,
        conf_type: 'deploy',
        level_name: 'module',
        level_value: modelValue.value,
        meta_cluster_type: props.clusterType,
        version: 'deploy_info',
      };
      runGetLevelConfig(params);
    }
  };

  watch(
    () => props.bizId,
    () => {
      if (props.bizId) {
        fetchModuleList();
      }
    },
    { immediate: true },
  );

  watch(
    [modelValue, moduleList],
    () => {
      const item = (moduleList.value || []).find((item) => item.db_module_id === modelValue.value);
      moduleAliasName.value = item?.alias_name ?? '';

      fetchLevelConfig();
    },
    {
      immediate: true,
    },
  );

  watch(levelConfigData, () => {
    const confItems = levelConfigData.value?.conf_items || [];
    const confInfo = {
      charset: '',
      dbVersion: '',
      systemVersionList: [] as string[],
    };
    confItems.forEach((confItem) => {
      const { conf_name: confName, conf_value: confValue = '' } = confItem;

      if (confName === 'charset') {
        confInfo.charset = confValue;
      } else if (confName === 'db_version') {
        confInfo.dbVersion = confValue;
      } else if (confName === 'system_version') {
        confInfo.systemVersionList = confValue.split(',');
      }
    });

    moduleLevelConfig.value = confInfo;
  });

  const getBaseInfo = (moduleItem: NonNullable<UnwrapRef<typeof moduleList>>[number]) => {
    const confItems = moduleItem.db_module_info.conf_items;
    if (dbType === DBTypes.RIAK || !confItems.length) {
      return '';
    }
    let dbVersion = '';
    let charset = '';
    let spiderVersion = '';

    if (confItems.length) {
      confItems.forEach((confItem) => {
        if (confItem.conf_name === 'db_version') {
          dbVersion = confItem.conf_value;
        } else if (confItem.conf_name === 'charset') {
          charset = confItem.conf_value;
        } else if (dbType === DBTypes.TENDBCLUSTER && confItem.conf_name === 'spider_version') {
          spiderVersion = confItem.conf_value;
        }
      });
    }

    if (dbType === DBTypes.TENDBCLUSTER) {
      return [spiderVersion, dbVersion, charset].join('，');
    }
    return [dbVersion, charset].join('，');
  };

  const handleCreateModule = () => {
    const url = router.resolve({
      name: 'DbConfigureCreateModule',
      params: {
        clusterType: props.clusterType,
      },
      query: {
        from: route.name as string,
      },
    });
    window.open(url.href, '_blank');
  };

  const handleBindConfig = () => {
    if (isBindModule.value) {
      fetchLevelConfig();
      return;
    }

    const typeMap: Record<string, string> = {
      [ClusterTypes.SQLSERVER_HA]: TicketTypes.SQLSERVER_HA_APPLY,
      [ClusterTypes.SQLSERVER_SINGLE]: TicketTypes.SQLSERVER_SINGLE_APPLY,
      [ClusterTypes.TENDBHA]: TicketTypes.MYSQL_HA_APPLY,
      [ClusterTypes.TENDBSINGLE]: TicketTypes.MYSQL_SINGLE_APPLY,
    };

    isBindModule.value = true;
    const url = router.resolve({
      name: 'SelfServiceBindDbModule',
      params: {
        bk_biz_id: props.bizId,
        db_module_id: modelValue.value,
        type: typeMap[props.clusterType],
      },
      query: dbType === DBTypes.MYSQL ? { alias_name: moduleAliasName.value } : {},
    });
    window.open(url.href, '_blank');
  };
</script>

<style lang="less">
  .apply-module-item-moudle-option {
    display: flex;
    width: 100%;

    .moudle-option-label {
      flex: 1;
      width: 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .moudle-opiton-info {
      margin-left: auto;
      color: #979ba5;
    }
  }
</style>
<style lang="less" scoped>
  .apply-module-item {
    .config-detail {
      width: 435px;
      padding: 8px 12px;
      margin-top: 16px;
      font-size: @font-size-mini;
      line-height: 20px;
      background-color: @bg-gray;
      border-radius: 2px;

      .config-detail-label {
        display: inline-block;
        min-width: 172px;
        padding-right: 8px;
        text-align: right;
      }

      .has-description {
        text-align: left;
      }

      .config-detail-value {
        color: @title-color;
      }

      .no-items {
        text-align: center;

        .bind-module {
          color: @primary-color;
          cursor: pointer;
        }
      }
    }
  }
</style>
