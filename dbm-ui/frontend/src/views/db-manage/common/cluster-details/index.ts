import ActionPanel from './ActionPanel.vue';
import BaseInfo, {
  ClbInfo,
  ColdResourceInfo,
  K8SClusterName,
  K8SSpec,
  // InfoItem as BaseInfoItem,
  // InfoList as BaseInfoList,
  ModuleNameInfo,
  PolarisInfo,
} from './base-info/Index.vue';
import BigDataInstanceList from './components/BigDataInstanceList.vue';
import K8SInstanceList from './components/k8s-instance-list/Index.vue';
import DisplayBox from './DisplayBox.vue';
import HostListFieldColumn from './HostListFieldColumn.vue';
import InstanceListFieldColumn from './InstanceListFieldColumn.vue';
import RoleSpec from './RoleSpec.vue';
import SlaveDomain from './SlaveDomain.vue';

const BaseInfoField = { ClbInfo, ModuleNameInfo, PolarisInfo };

export {
  ActionPanel,
  BaseInfo,
  BaseInfoField,
  // BaseInfoList,
  BigDataInstanceList,
  // BaseInfoItem,
  ColdResourceInfo,
  DisplayBox,
  HostListFieldColumn,
  InstanceListFieldColumn,
  K8SClusterName,
  K8SInstanceList,
  K8SSpec,
  RoleSpec,
  SlaveDomain,
};

export * from './constants';
export * from './hooks/index';
