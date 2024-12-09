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
      style="display: inline-block">
      <AuthOption
        v-for="item in moduleList"
        :id="item.db_module_id"
        :key="item.db_module_id"
        action-id="dbconfig_view"
        :biz-id="bizId"
        :name="item.alias_name"
        :permission="item.permission.dbconfig_view"
        :resource="dbType">
        <div class="apply-module-item-moudle-option">
          <span class="moudle-option-label">
            <BkOverflowTitle type="tips">{{ item.alias_name }}</BkOverflowTitle>
          </span>
          <span class="moudle-opiton-info ml-4">
            {{ getBaseInfo(item) }}
          </span>
        </div>
      </AuthOption>
      <template
        v-if="bizId && clusterType !== ClusterTypes.RIAK"
        #extension>
        <div
          :key="bizId"
          v-bk-tooltips.top="{
            content: t('请先选择所属业务'),
            disabled: !!bizId,
          }"
          style="padding: 0 12px">
          <AuthButton
            action-id="dbconfig_edit"
            :biz-id="bizId"
            class="create-module"
            :disabled="!bizId"
            :resource="dbType"
            text
            @click="handleCreateModule">
            <DbIcon
              class="mr-4"
              type="plus-circle" />
            {{ t('新建模块') }}
          </AuthButton>
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
            <span class="config-detail-label">{{ item.label }}:</span>
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
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getModules } from '@services/source/cmdb';
  import { getLevelConfig } from '@services/source/configs';

  import { clusterTypeInfos, ClusterTypes, DBTypes, TicketTypes } from '@common/const';

  interface Props {
    clusterType: ClusterTypes;
    bizId: number | '';
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

  const rules = [
    {
      message: t('请先选择所属业务'),
      trigger: 'blur',
      validator: () => props.bizId,
    },
    {
      message: t('DB模块名不能为空'),
      trigger: 'blur',
      validator: (value: number) => value,
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
            label: labelMap[key],
            value: configMap[key],
          }),
        );
      }
    }
    return confItems.map((confItem) => ({
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
      cluster_type: props.clusterType,
      bk_biz_id: Number(props.bizId),
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
    modelValue,
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

    if (confItems.length) {
      confItems.forEach((confItem) => {
        if (confItem.conf_name === 'db_version') {
          dbVersion = confItem.conf_value;
        } else if (confItem.conf_name === 'charset') {
          charset = confItem.conf_value;
        }
      });
    }
    return [dbVersion, charset].join('，');
  };

  const handleCreateModule = () => {
    const routeNameMap: Record<string, string> = {
      [DBTypes.MYSQL]: 'SelfServiceCreateDbModule',
      [DBTypes.TENDBCLUSTER]: 'createSpiderModule',
      [DBTypes.SQLSERVER]: 'SqlServerCreateDbModule',
    };

    const getParams = () => {
      if (dbType === DBTypes.MYSQL) {
        return {
          type:
            props.clusterType === ClusterTypes.TENDBSINGLE
              ? TicketTypes.MYSQL_SINGLE_APPLY
              : TicketTypes.MYSQL_HA_APPLY,
          bk_biz_id: props.bizId,
        };
      }
      if (dbType === DBTypes.TENDBCLUSTER) {
        return {
          bizId: props.bizId,
        };
      }
      return {
        ticketType:
          props.clusterType === ClusterTypes.SQLSERVER_SINGLE
            ? TicketTypes.SQLSERVER_SINGLE_APPLY
            : TicketTypes.SQLSERVER_HA_APPLY,
        bizId: props.bizId,
      };
    };

    const url = router.resolve({
      name: routeNameMap[dbType],
      params: getParams(),
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
      [ClusterTypes.TENDBSINGLE]: TicketTypes.MYSQL_SINGLE_APPLY,
      [ClusterTypes.TENDBHA]: TicketTypes.MYSQL_HA_APPLY,
      [ClusterTypes.SQLSERVER_SINGLE]: TicketTypes.SQLSERVER_SINGLE_APPLY,
      [ClusterTypes.SQLSERVER_HA]: TicketTypes.SQLSERVER_HA_APPLY,
    };

    isBindModule.value = true;
    const url = router.resolve({
      name: 'SelfServiceBindDbModule',
      params: {
        type: typeMap[props.clusterType],
        bk_biz_id: props.bizId,
        db_module_id: modelValue.value,
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
        min-width: 112px;
        padding-right: 8px;
        text-align: right;
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
