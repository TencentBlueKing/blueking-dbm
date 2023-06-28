package cc

import (
	"encoding/json"
	"fmt"
)

// SecretMeta 定义了SetSecret接口
// 每个请求CC接口的struct都包括了BaseSecret信息
// 所以这里在调用时统一设置
type SecretMeta interface {
	SetSecret(secret Secret)
}

// Accessor 统一处理Secret信息
func Accessor(obj interface{}) (SecretMeta, error) {
	switch t := obj.(type) {
	case SecretMeta:
		return t, nil
	default:
		return nil, fmt.Errorf("TypeErr: %v", t)
	}
}

// BaseSecret TODO
// CC接口验证信息
type BaseSecret struct {
	BKAppCode         string `json:"bk_app_code" url:"bk_app_code"`
	BKAppSecret       string `json:"bk_app_secret" url:"bk_app_secret"`
	BKUsername        string `json:"bk_username" url:"bk_username"`
	BKSupplierAccount string `json:"bk_supplier_account" url:"bk_supplier_account"`
}

// SetSecret 设置Secret信息
func (s *BaseSecret) SetSecret(secret Secret) {
	s.BKAppCode = secret.BKAppCode
	s.BKAppSecret = secret.BKAppSecret
	s.BKUsername = secret.BKUsername
	s.BKSupplierAccount = "tencent"
}

// Host TODO
// CC主机属性
// 字段名与CCDeviceInfo的一致，主要方便做映射
type Host struct {
	AssetID            string      `json:"bk_asset_id,omitempty"`
	HostID             int         `json:"svr_id,omitempty"`
	BKHostId           int         `json:"bk_host_id,omitempty"`
	SN                 string      `json:"bk_sn,omitempty"`
	InnerIP            string      `json:"bk_host_innerip,omitempty"`
	OuterIP            string      `json:"bk_host_outerip,omitempty"`
	InnerSegmentName   string      `json:"inner_network_segment,omitempty"`
	OuterSegmentName   string      `json:"outer_network_segment,omitempty"`
	Dep                string      `json:"dept_name,omitempty"`
	HostName           string      `json:"bk_host_name,omitempty"`
	GroupName          string      `json:"group_name,omitempty"`
	DeviceTypeName     string      `json:"svr_device_type_name,omitempty"`
	DeviceClass        string      `json:"svr_device_class,omitempty"`
	Raid               string      `json:"raid_name,omitempty"`
	OSName             string      `json:"bk_os_name,omitempty"`
	OSVersion          string      `json:"bk_os_version,omitempty"`
	HardMemo           string      `json:"hard_memo,omitempty"`
	InputTime          string      `json:"svr_input_time,omitempty"`
	Operator           string      `json:"operator,omitempty"`
	BakOperator        string      `json:"bk_bak_operator,omitempty"`
	ClassifyLevelName  string      `json:"classify_level_name,omitempty"`
	Alarmlevel         string      `json:"bk_sla,omitempty"`
	ImportantLevel     string      `json:"srv_important_level,omitempty"`
	ZoneName           string      `json:"bk_zone_name,omitempty"`
	SZone              string      `json:"sub_zone,omitempty"`
	SZoneID            string      `json:"sub_zone_id,omitempty"`
	ModuleName         string      `json:"module_name,omitempty"`
	IdcArea            string      `json:"bk_idc_area,omitempty"`
	IDC                string      `json:"idc_name,omitempty"`
	IDCID              int         `json:"idc_id,omitempty"`
	IDCUnit            string      `json:"idc_unit_name,omitempty"`
	IDCUnitID          int         `json:"idc_unit_id,omitempty"`
	IdcOperationName   string      `json:"bk_isp_name,omitempty"`
	IdcLogicArea       string      `json:"logic_domain,omitempty"`
	LogicZone          string      `json:"bk_logic_zone,omitempty"`
	LogicZoneID        string      `json:"bk_logic_zone_id,omitempty"`
	State              string      `json:"srv_status,omitempty"`
	ServerRack         string      `json:"rack,omitempty"`
	Equipment          string      `json:"rack_id,omitempty"`
	LinkNetdeviceId    string      `json:"net_device_id,omitempty"`
	InnerSwitchPort    string      `json:"inner_switch_port,omitempty"`
	OuterSwitchPort    string      `json:"outer_switch_port,omitempty"`
	InnerSwitchIp      string      `json:"bk_inner_switch_ip,omitempty"`
	OuterSwitchIp      string      `json:"bk_outer_switch_ip,omitempty"`
	NetStructVer       interface{} `json:"net_struct_id,omitempty"`
	NetStructVerName   string      `json:"net_struct_name,omitempty"`
	IdcAreaId          int         `json:"bk_idc_area_id,omitempty"`
	IPOperName         string      `json:"bk_ip_oper_name,omitempty"`
	SvrDeviceClassName string      `json:"bk_svr_device_cls_name,omitempty"`
	StrVersion         string      `json:"bk_str_version,omitempty"`
	IdcCityName        string      `json:"idc_city_name,omitempty"`
	IdcCityId          string      `json:"idc_city_id,omitempty"`
	BkCpu              int         `json:"bk_cpu,omitempty"`
	BkMem              int         `json:"bk_mem,omitempty"`
	BkDisk             int         `json:"bk_disk"`
	BkAgentId          string      `json:"bk_agent_id,omitempty"`
	SvrTypeName        string      `json:"svr_type_name"`
	BKBSInfos          []*CMDBInfo `json:"bk_bs_info"`
}

// CMDBInfo 公司CMDB对应的业务模块信息
type CMDBInfo struct {
	// CMDB业务集ID
	Bs1NameId int `json:"bs1_name_id"`
	// CMDB业务ID
	Bs2NameId int `json:"bs2_name_id"`
	// CMDB模块ID
	Bs3NameId int `json:"bs3_name_id"`
	// CMDB业务集名称
	Bs1Name string `json:"bs1_name"`
	// CMDB业务名称
	Bs2Name string `json:"bs2_name"`
	// CMDB模块名称
	Bs3Name string `json:"bs3_name"`
}

// Set 集群(Set)信息
type Set struct {
	BKSetId   int    `json:"bk_set_id"`
	BKSetName string `json:"bk_set_name"`
}

// Module 业务模块信息
type Module struct {
	BKModuleId   int    `json:"bk_module_id"`
	BKModuleName string `json:"bk_module_name"`
	// 模块类型
	// 1:普通，2：数据库
	ModuleCategory string `json:"bk_module_type"`
	// default值
	// 0. 普通的模块;	1. 空闲机;	2. 故障机;	3. 待回收;	>3 其它
	Default int `json:"default"`
}

// Relation 集群与模块映射关系
type Relation struct {
	BKSetId   int    `json:"bk_set_id"`
	BKSetName string `json:"bk_set_name"`
	// 对应原来的TopoModuleID
	BKModuleId int `json:"bk_module_id"`
	// 对应原来的TopoModule
	BKModuleName string   `json:"bk_module_name"`
	BKBSInfo     CMDBInfo `json:"bk_bs_info"`
	// 对应原来的AppModuleId
	ServiceTemplateId int `json:"service_template_id"`
	// 对应原来的AppModule
	ServiceTemplateName string `json:"service_template_name"`
}

// HostBizModule 主机与业务模块的关联信息
type HostBizModule struct {
	BKHostId   int `json:"bk_host_id"`
	BKBizId    int `json:"bk_biz_id"`
	BKSetId    int `json:"bk_set_id"`
	BKModuleId int `json:"bk_module_id"`
}

// ResourceWatchType 事件监听的资源类型
type ResourceWatchType string

// cc系统支持的监听事件类型
const (
	HostResource         ResourceWatchType = "host"
	HostRelationResource ResourceWatchType = "host_relation"
	BizResource          ResourceWatchType = "biz"
	SetResource          ResourceWatchType = "set"
	ModuleResource       ResourceWatchType = "module"
)

// ResourceWatchParam 资源监听输入参数
type ResourceWatchParam struct {
	BaseSecret `json:",inline"`
	// 事件类型: create(新增)/update(更新)/delete(删除)
	BKEventTypes []string `json:"bk_event_types"`
	// 返回的事件中需要返回的字段列表, 不能置空
	BKFields []string `json:"bk_fields"`
	// 监听事件的起始时间，该值为unix time的秒数，
	// 即为从UTC1970年1月1日0时0分0秒起至你要watch的时间点的总秒数。
	BKStartFrom int64 `json:"bk_start_from"`
	// 监听事件的游标，代表了要开始或者继续watch(监听)的事件地址，
	// 系统会返回这个游标的下一个、或一批事件。
	BKCursor string `json:"bk_cursor,omitempty"`
	// 要监听的资源类型，枚举值为：host, host_relation, biz, set, module
	BKResource ResourceWatchType `json:"bk_resource"`
}

// ResourceWatchResponse 资源监听事件返回参数
type ResourceWatchResponse struct {
	// RequestId只是为了记录日志，方便定位问题
	RequestId string    `json:"-"`
	BKEvents  []BKEvent `json:"bk_events"`
	BKWatched bool      `json:"bk_watched"`
}

// BKEvent 监听事件明细
type BKEvent struct {
	BKEventType string            `json:"bk_event_type"`
	BKResource  ResourceWatchType `json:"bk_resource"`
	BKCursor    string            `json:"bk_cursor"`
	BKDetail    json.RawMessage   `json:"bk_detail"`
}

// ListHostRelationParam 主机拓扑信息查询输入参数
type ListHostRelationParam struct {
	BaseSecret `json:",inline"`
	// 要查询的主机列表，最大长度为500，若不为空，则page字段不生效
	BKHostIds []int `json:"bk_host_ids"`
	// 要返回的主机字段列表，不能为空
	BKHostFields []string `json:"bk_host_fields"`
	// 要返回的业务字段列表，不能为空
	BKBizFields []string `json:"bk_biz_fields"`
	// 要返回的集群字段列表，不能为空
	BKSetFields []string `json:"bk_set_fields"`
	// 要返回的模块字段列表，不能为空
	BKModuleFields []string `json:"bk_module_fields"`
	// 分页信息
	Page BKPage `json:"page"`
}

// FindHostBizRelationParam 接口主机拓扑信息查询输入参数, BKHostIds的json为单数
type FindHostBizRelationParam struct {
	BaseSecret `json:",inline"`
	// 要查询的主机列表，最大长度为500，若不为空，则page字段不生效
	BKHostIds []int `json:"bk_host_id"`
	// 要返回的主机字段列表，不能为空
	BKHostFields []string `json:"bk_host_fields"`
	// 要返回的业务字段列表，不能为空
	BKBizFields []string `json:"bk_biz_fields"`
	// 要返回的集群字段列表，不能为空
	BKSetFields []string `json:"bk_set_fields"`
	// 要返回的模块字段列表，不能为空
	BKModuleFields []string `json:"bk_module_fields"`
	// 分页信息
	Page BKPage `json:"page"`
}

// FindHostBizRelationResp 接口返回结构
type FindHostBizRelationResp struct {
	BkBizID           int    `json:"bk_biz_id"`
	BkHostID          int    `json:"bk_host_id"`
	BkModuleID        int    `json:"bk_module_id"`
	BkSetID           int    `json:"bk_set_id"`
	BkSupplierAccount string `json:"bk_supplier_account"`
}

// GetHostBaseInfoParam TODO
type GetHostBaseInfoParam struct {
	BaseSecret        `json:",inline"`
	BkHostID          int    `json:"bk_host_id" url:"bk_host_id"`
	BkSupplierAccount string `json:"bk_supplier_account" url:"bk_supplier_account"`
}

// HostPropertyInfo TODO
type HostPropertyInfo struct {
	BkPropertyId    string      `json:"bk_property_id"`
	BkPropertyName  string      `json:"bk_property_name"`
	BkpropertyValue interface{} `json:"bk_property_value"`
}

// HostMetaData 标识一台主机设备的信息
type HostMetaData struct {
	// 主机IP
	InnerIPs []string
	// 主机固定号
	AssetIds []string
	// 主机的id
	BKHostIds []int
}

// BKPage 查询分页参数
type BKPage struct {
	// 记录开始位置
	Start int `json:"start"`
	// 每页限制条数,最大500
	Limit int `json:"limit"`
}

// ListHostRelationResponse 主机拓扑信息查询返回参数
type ListHostRelationResponse struct {
	Count int                 `json:"count"`
	Info  []*HostRelationInfo `json:"info"`
}

// HostRelationInfo 主机与业务模块关联信息
type HostRelationInfo struct {
	Host      Host       `json:"host"`
	Biz       Biz        `json:"biz"`
	Sets      []Set      `json:"set"`
	Modules   []Module   `json:"module"`
	Relations []Relation `json:"relations"`
}

// BizSetParam 业务与Set信息查询输入参数
type BizSetParam struct {
	BaseSecret `json:",inline"`
	BKBizId    int      `json:"bk_biz_id"`
	Fields     []string `json:"fields"`
	// 分页信息
	Page BKPage `json:"page"`
}

// BizSetResponse 业务与Set信息查询返回值
type BizSetResponse struct {
	Count int    `json:"count"`
	Info  []*Set `json:"info"`
}

// BizModuleParam 业务与模块信息查询输入参数
type BizModuleParam struct {
	BaseSecret `json:",inline"`
	BKBizId    int `json:"bk_biz_id"`
	BKSetId    int `json:"bk_set_id"`
	// 模块属性列表，控制返回结果的模块信息里有哪些字段
	Fields []string `json:"fields"`
	// 分页信息
	Page BKPage `json:"page"`
}

// BizModuleResponse 业务与模块信息查询返回值
type BizModuleResponse struct {
	Count int       `json:"count"`
	Info  []*Module `json:"info"`
}

// Biz 业务信息
type Biz struct {
	// 业务唯一标识ID
	ApplicationID int `json:"bk_biz_id"`
	// 产品名称
	DisplayName string `json:"bk_biz_name"`
	// 运维小组名称
	GroupName string `json:"bk_oper_grp_name"`
	// 英文缩写
	Abbreviation string `json:"bk_app_abbr"`
	// 部门名称
	DeptName string `json:"bk_dept_name_id"`
	IsBip    string `json:"bk_is_bip"`
	// 业务运维
	Maintainers string `json:"bk_biz_maintainer"`
	// 运管PM
	OperationPlanning string `json:"bk_oper_plan"`
	// DBA主
	PmpDBAMajor string `json:"bk_pmp_dba_major"`
	// 	DBA备
	PmpDBABackup string `json:"bk_dba_bak"`
	// 产品负责人
	AppDirector string `json:"bk_app_director"`
	// 产品URL
	AppUrl string `json:"bk_app_url"`
	// 开发团队
	AppDevTeam string `json:"bk_app_devteam"`
	// 开发人员
	AppDevMan string `json:"bk_biz_developer"`
	// 开发备份人员
	AppDevBackup string `json:"bk_app_dev_bak"`
	// 架构文档链接
	AppDoc string `json:"bk_arc_doc"`
	// 用户文档链接
	AppUserManual string `json:"bk_app_user_manual"`
	// 运维手册链接
	AppOpeManual string `json:"bk_app_oper_manual"`
	// 产品英文名
	BipID string `json:"bk_bip_id"`
	// SA
	PmpSA string `json:"bk_pmp_sa"`
	// PMP相关信息
	PmpSafeMan    string `json:"bk_pmp_safe_man"`
	PmpOpeDevMan  string `json:"bk_pmp_oper_dev_man"`
	PmpOssMan     string `json:"bk_pmp_oss_man"`
	PmpCmMan      string `json:"bk_pmp_cm_man"`
	PmpPortalMan  string `json:"bk_pmp_potl_man"`
	PmpIdipMan    string `json:"bk_pmp_idip_man"`
	PmpTlogMan    string `json:"bk_tlog_man"`
	PmpServicePM  string `json:"bk_pmp_svc_pm"`
	PmpCmReqMan   string `json:"bk_pmp_cmreqman"`
	PmpComPlot    string `json:"bk_pmp_com_plot"`
	PmpProductMan string `json:"bk_biz_productor"`
	PmpQA         string `json:"bk_pmp_qa"`
	PmpQC         string `json:"bk_pmp_qc"`
	// CC只有ID的字段
	AppGameTypeID string `json:"bk_app_game_typeid"`
	OperState     string `json:"life_cycle"`
	AppType       string `json:"bk_app_type"`
	SourceID      string `json:"bk_source_id"`
	// OBS产品ID
	ProductId int `json:"bk_product_id"`
	// 业务部门ID，3为IEG
	BusinessDeptId int `json:"bk_business_dept_id"`
	// 初始运维部门ID，3为IEG
	OperateDeptId int `json:"bk_operate_dept_id"`
}

// BizParam 查询业务入参
type BizParam struct {
	BaseSecret `json:",inline"`
	Fields     []string `json:"fields"`
	// 分页信息
	Page      BKPage                 `json:"page"`
	Condition map[string]interface{} `json:"condition"`
}

// HostOri TODO
type HostOri struct {
	BkIspName      string `json:"bk_isp_name"`      // 0:其它；1:电信；2:联通；3:移动
	BkSn           string `json:"bk_sn"`            // 设备SN
	Operator       string `json:"operator"`         // 主要维护人
	BkOuterMac     string `json:"bk_outer_mac"`     // 外网MAC
	BkStateName    string `json:"bk_state_name"`    // 所在国家	CN:中国，详细值，请参考CMDB页面
	BkProvinceName string `json:"bk_province_name"` // 所在省份
	ImportFrom     string `json:"import_from"`      // 录入方式	1:excel;2:agent;3:api
	BkSla          string `json:"bk_sla"`           // SLA级别	1:L1;2:L2;3:L3
	BkServiceTerm  int    `json:"bk_service_term"`  // 质保年限	1-10
	BkOsType       string `json:"bk_os_type"`       // 操作系统类型	1:Linux;2:Windows;3:AIX
	BkOsVersion    string `json:"bk_os_version"`    // 操作系统版本
	BkOsBit        int    `json:"bk_os_bit"`        // 操作系统位数
	BkMem          string `json:"bk_mem"`           // 内存容量
	BkMac          string `json:"bk_mac"`           // 内网MAC地址
	BkHostOuterip  string `json:"bk_host_outerip"`  // 外网IP
	BkHostName     string `json:"bk_host_name"`     // 主机名称
	BkHostInnerip  string `json:"bk_host_innerip"`  // 内网IP
	BkHosId        int    `json:"bk_host_id"`       // 主机ID
	BkDisk         int    `json:"bk_disk"`          // 磁盘容量
	BkCpuModule    string `json:"bk_cpu_module"`    // CPU型号
	BkCpuMhz       int    `json:"bk_cpu_mhz"`       // CPU频率
	BkCpu          int    `json:"bk_cpu"`           // CPU逻辑核心数	1-1000000
	BkComment      string `json:"bk_comment"`       // 备注
	BkCloudId      int    `json:"bk_cloud_id"`      // 云区域
	BkBakOperator  string `json:"bk_bak_operator"`  // 备份维护人
	BkAssetId      string `json:"bk_asset_id"`      // 固资编号
}

// ListBizHostsParam TODO
type ListBizHostsParam struct {
	BaseSecret         `json:",inline"`
	Page               BKPage             `json:"page"`
	BkBizId            int                `json:"bk_biz_id"`
	BkSetIds           []int              `json:"bk_set_ids"`
	HostPropertyFilter HostPropertyFilter `json:"host_property_filter"`
	Fileds             []string           `json:"fields"`
}

// ListBizHostsResponse TODO
type ListBizHostsResponse struct {
	Count int     `json:"count"`
	Info  []*Host `json:"info"`
}

// BizResponse 查询业务返回信息
type BizResponse struct {
	Count int    `json:"count"`
	Info  []*Biz `json:"info"`
}

// TransferHostParam 转移主机模块输入参数
type TransferHostParam struct {
	BaseSecret `json:",inline"`
	From       BKFrom `json:"bk_from"`
	To         BKTo   `json:"bk_to"`
}

// TransferHostModuleParam 同业务下转移模块，支持转移到多个模块
type TransferHostModuleParam struct {
	BaseSecret  `json:",inline"`
	BkBizID     int   `json:"bk_biz_id"`
	BkHostID    []int `json:"bk_host_id"`
	BkModuleID  []int `json:"bk_module_id"`
	IsIncrement bool  `json:"is_increment"`
}

// CloneHostPropertyParam 克隆主机属性输入参数
type CloneHostPropertyParam struct {
	BaseSecret  `json:",inline"`
	BkBizId     int `json:"bk_biz_id"`
	BkOrgHostId int `json:"bk_org_id"`
	BkDstHostId int `json:"bk_dst_id"`
}

// CloneHostSvcInsParam 克隆实例信息输入参数
type CloneHostSvcInsParam struct {
	BaseSecret  `json:",inline"`
	BkBizId     int   `json:"bk_biz_id"`
	BkModuleIds []int `json:"bk_module_ids"`
	SrcHostId   int   `json:"src_host_id"`
	DstHostId   int   `json:"dst_host_id"`
}

// BKFrom 转移主机模块入参中的源主机（业务）信息
type BKFrom struct {
	// 源业务ID
	BKBizId int `json:"bk_biz_id"`
	// 主机IP
	InnerIPs []string `json:"-"`
	// 主机固定号
	AssetIds []string `json:"-"`
	// 主机的id
	BKHostIds []int `json:"bk_host_ids"`
}

// BKTo 移主机模块入参中的目标业务信息
type BKTo struct {
	// 目标业务ID
	BKBizId int `json:"bk_biz_id"`
	// 主机要转移到的模块ID，如果不传，则将主机转移到该业务的空闲机模块下
	BKModuleId int `json:"bk_module_id,omitempty"`
}

// UpdateHostParam 修改主机属性输入参数(例如主备负责人)
type UpdateHostParam struct {
	BaseSecret `json:",inline"`
	// 主机IP
	InnerIPs []string `json:"-"`
	// 主机固定号
	AssetIds []string `json:"-"`
	// 主机ID，多个以逗号分隔
	BKHostId string `json:"bk_host_id"`
	// 主机数据
	Data Host `json:"data"`
}

// HostsWithoutBizListParam 根据过滤条件查询主机信息
type HostsWithoutBizListParam struct {
	BaseSecret `json:",inline"`
	// 查询条件
	HostPropertyFilter HostPropertyFilter `json:"host_property_filter"`
	// 分页
	Page BKPage `json:"page"`
}

// HostPropertyFilter 查询规则组合
type HostPropertyFilter struct {
	// 条件逻辑AND | OR
	Condition string `json:"condition"`
	// 规则
	Rules []Rule `json:"rules"`
}

// Rule 查询的运算规则
type Rule struct {
	// 字段名
	Field string `json:"field"`
	// 操作符
	// 可选值 equal,not_equal,in,not_in,less,less_or_equal,greater,greater_or_equal,between,not_between
	Operator string `json:"operator"`
	// 操作数值
	Value interface{} `json:"value"`
}

// HostsWithoutBizListResponse 主机（不带业务信息）查询返回信息
type HostsWithoutBizListResponse struct {
	Count int     `json:"count"`
	Info  []*Host `json:"info"`
}

const (
	// Limit 分页，每页的最大记录数
	Limit int = 500
)

// BizInternalModulesParam 查询业务的内置模块入参
type BizInternalModulesParam struct {
	BaseSecret `json:",inline" url:",inline"`
	BKBizId    int `json:"bk_biz_id" url:"bk_biz_id"`
}

// BizInternalModuleResponse 查询业务的内置模块返回值
type BizInternalModuleResponse struct {
	BkSetID int `json:"bk_set_id"`
	Module  []struct {
		Default          int    `json:"default"`
		BkModuleName     string `json:"bk_module_name"`
		BkModuleID       int    `json:"bk_module_id"`
		HostApplyEnabled bool   `json:"host_apply_enabled"`
	} `json:"module"`
	BkSetName string `json:"bk_set_name"`
}

// BizTopoTreeParam 查询业务拓扑信息入参
type BizTopoTreeParam struct {
	BaseSecret `json:",inline" url:",inline"`
	BKBizId    int `json:"bk_biz_id" url:"bk_biz_id"`
}

// TopoTreeNode TODO
// CC topo tree
type TopoTreeNode struct {
	HostCount  int            `json:"host_count,omitempty"`
	Default    int            `json:"default,omitempty"`
	BkObjName  string         `json:"bk_obj_name,omitempty"`
	BkObjID    string         `json:"bk_obj_id,omitempty"`
	Child      []TopoTreeNode `json:"child,omitempty"`
	BkInstID   int            `json:"bk_inst_id"`
	BkInstName string         `json:"bk_inst_name"`
}

// BizLocationParam TODO
type BizLocationParam struct {
	BaseSecret `json:",inline" url:",inline"`
	BKBizIds   []int `json:"bk_biz_ids" url:"bk_biz_ids"`
}

// HostLocationParam TODO
type HostLocationParam struct {
	BaseSecret `json:",inline" url:",inline"`
	BkHostList []BkHostList `json:"bk_host_list"`
}

// BkHostList TODO
type BkHostList struct {
	BkHostInnerip string `json:"bk_host_innerip"`
	BkCloudID     int    `json:"bk_cloud_id"`
}

// HostLocationInfo TODO
// HostLocationParam
type HostLocationInfo struct {
	BkHostInnerip string `json:"bk_host_innerip"`
	BkCloudID     int    `json:"bk_cloud_id"`
	BkLocation    string `json:"bk_location"`
}

// BizLocationInfo TODO
// CC biz location
type BizLocationInfo struct {
	BkBizID    int    `json:"bk_biz_id"`
	BkLocation string `json:"bk_location"`
}

// FindHostBizRelationResponse 查询主机与业务关联信息返回值
type FindHostBizRelationResponse struct {
	Result  bool   `json:"result"`
	Code    int    `json:"code"`
	Message string `json:"message"`
	Data    []struct {
		BkBizID           int    `json:"bk_biz_id"`
		BkHostID          int    `json:"bk_host_id"`
		BkModuleID        int    `json:"bk_module_id"`
		BkSetID           int    `json:"bk_set_id"`
		BkSupplierAccount string `json:"bk_supplier_account"`
	} `json:"data"`
}

// DeptParam 部门信息
type DeptParam struct {
	BaseSecret `json:",inline"`
	// 部门ID
	DeptId string `json:"dept_id"`
}

// DeptResponse 查询部分返回信息
type DeptResponse struct {
	// 部门ID
	ID string `json:"ID"`
	// 部门名称
	Name string `json:"Name"`
	// 上级ID
	ParentId string `json:"ParentId"`
}

// BizCreateSetParam TODO
type BizCreateSetParam struct {
	BaseSecret `json:",inline"`
	BkBizID    int `json:"bk_biz_id"`

	Data struct {
		BkParentID    int    `json:"bk_parent_id"`
		BkSetName     string `json:"bk_set_name"`
		SetTemplateID int    `json:"set_template_id"`
	} `json:"data"`
}

// BizDeleteSetParam TODO
type BizDeleteSetParam struct {
	BaseSecret `json:",inline"`
	BkBizID    int `json:"bk_biz_id"`
	BkBizSetID int `json:"bk_set_id"`
}

// BizCreateSetResponse TODO
type BizCreateSetResponse struct {
	BkSetName string `json:"bk_set_name"`
	BkSetId   int    `json:"bk_set_id"`
}

// BizSensitive 业务敏感信息
type BizSensitive struct {
	BKBizId     int `json:"bk_biz_id"`
	BkProductId int `json:"bk_product_id"`
}

// BizSensitiveParam 查询业务敏感信息入参
type BizSensitiveParam struct {
	BaseSecret `json:",inline"`
	Fields     []string `json:"fields"`
	// 分页信息
	Page     BKPage `json:"page"`
	BkBizIds []int  `json:"bk_biz_ids"`
}

// BizSensitiveResponse 查询Obs产品信息返回信息
type BizSensitiveResponse struct {
	Count int             `json:"count"`
	Info  []*BizSensitive `json:"info"`
}

// SyncHostInfoFromCmpyParam 同步公司cmdb更新信息入参
type SyncHostInfoFromCmpyParam struct {
	BaseSecret `json:",inline"`
	BkHostIds  []int `json:"bk_host_ids"`
}

// AddHostInfoFromCmpyParam 同步公司cmdb新增信息入参
type AddHostInfoFromCmpyParam struct {
	BaseSecret `json:",inline"`
	SvrIds     []int `json:"svr_ids"`
}

// CreateModuleParam 参数
type CreateModuleParam struct {
	BKBizId int `json:"bk_biz_id"`
	BkSetId int `json:"bk_set_id"`
	Data    struct {
		BkParentID   int    `json:"bk_parent_id"`
		BkModuleName string `json:"bk_module_name"`
	} `json:"data"`
}
