<template>
  <DbMenuGroup
    class="module-menu-group"
    :name="dbInfo.name">
    <template #name>
      <span class="text-overflow">{{ displayName }}</span>
      <DbIcon
        v-if="!isError && !collapse"
        v-bk-tooltips="disabled ? t('当前数据库已置顶') : t('置顶当前数据库')"
        class="top-button"
        :class="{ 'top-button-disabled': disabled }"
        type="zhiding"
        @click="handleClick" />
    </template>
    <slot />
  </DbMenuGroup>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useUserProfile } from '@stores';

  import { DBTypeInfos, DBTypes, UserPersonalSettings } from '@common/const';

  import { messageSuccess } from '@utils';

  import { useMenuContext } from '../../../../menu/common/context';
  import DbMenuGroup from '../../../../menu/Group.vue';

  interface Props {
    dbType: DBTypes;
    isError: boolean;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const userProfileStore = useUserProfile();

  // 收起态轨道只有 60px，DB 名统一用缩写展示
  const foldNameMap: Record<DBTypes, string> = {
    [DBTypes.DORIS]: 'Doris',
    [DBTypes.ES]: 'ES',
    [DBTypes.HDFS]: 'HDFS',
    [DBTypes.INFLUXDB]: 'Influx',
    [DBTypes.K8S_QRRANT]: 'Qdrant',
    [DBTypes.K8S_SURREALDB]: 'SurrealDB',
    [DBTypes.KAFKA]: 'Kafka',
    [DBTypes.MONGODB]: 'Mongo',
    [DBTypes.MYSQL]: 'MySQL',
    [DBTypes.ORACLE]: 'Oracle',
    [DBTypes.PULSAR]: 'Pulsar',
    [DBTypes.REDIS]: 'Redis',
    [DBTypes.RIAK]: 'Riak',
    [DBTypes.SQLSERVER]: 'MSSQL',
    [DBTypes.TENDBCLUSTER]: 'TenDB',
  };

  const dbInfo = DBTypeInfos[props.dbType];

  const { collapse } = useMenuContext();

  const topDbTypes = computed<string[]>(() => userProfileStore.profile[UserPersonalSettings.TOP_DB_TYPES] || []);

  const displayName = computed(() => (collapse.value ? foldNameMap[props.dbType] : dbInfo.name));

  const disabled = computed(() => {
    if (topDbTypes.value.length > 0) {
      return props.dbType === topDbTypes.value[0];
    }
    return false;
  });

  const handleClick = () => {
    if (disabled.value) {
      return;
    }
    userProfileStore
      .updateProfile({
        label: UserPersonalSettings.TOP_DB_TYPES,
        values: [props.dbType, ...topDbTypes.value.filter((item) => item !== props.dbType)],
      })
      .then(() => {
        messageSuccess(t('「n」已全局置顶，所有业务导航将优先展示该类型', { n: dbInfo.name }));
      });
  };
</script>

<style lang="less">
  .db-menu {
    .module-menu-group {
      .db-menu-group-name {
        padding: 0 18px;
        margin: 0;

        &:hover {
          background-color: #2b313f;

          .top-button {
            display: inline-block;
          }
        }
      }

      .top-button {
        display: none;
        margin-left: auto;
        font-size: 18px;
        color: #c4c6cc;

        &:hover {
          display: inline-block;
          color: #fff;
        }
      }

      .top-button-disabled {
        color: #dcdee5;
        cursor: not-allowed;

        &:hover {
          color: #dcdee5;
        }
      }
    }

    &.is-collapse {
      .module-menu-group .db-menu-group-name {
        padding: 0 4px;
      }
    }
  }
</style>
