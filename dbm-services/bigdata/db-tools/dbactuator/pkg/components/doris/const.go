package doris

const (

	// DefaultInstallDir TODO
	DefaultInstallDir = "/data"
	// DefaultPkgDir TODO
	DefaultPkgDir = "/data/install" // 介质存放目录
	// DefaultDorisDataDir TODO
	DefaultDorisDataDir = "/data/dorisdata" // doris安装包存放目录
	// DefaultDorisEnv TODO
	DefaultDorisEnv = "/data/dorisenv" // doris安装包存放目录
	// DefaultDorisExecUser TODO
	DefaultDorisExecUser = "mysql"
	// ConfDirTmpl TODO
	ConfDirTmpl = "/data/dorisenv/%s/conf"
	// DefaultSupervisorConfDir TODO
	DefaultSupervisorConfDir = "/data/dorisenv/supervisor/conf"
)

type Role string
type Group string
type MetaOperation string
type DiskType string

const (
	Add          MetaOperation = "ADD"
	Drop         MetaOperation = "DROP"
	Decommission MetaOperation = "DECOMMISSION"
	ForceDrop    MetaOperation = "DROPP"
)

const (
	Follower Role = "follower"
	Observer Role = "observer"
	Hot      Role = "hot"
	Cold     Role = "cold"
	Warm     Role = "warm"
)

const (
	Fronted Group = "fe"
	Backend Group = "be"
)

const (
	HDD DiskType = "HDD"
	SSD DiskType = "SSD"
)

const (
	FeEditLogPort   int = 9010
	BeHeartBeatPort int = 9050
)

// FollowerEnum Follower 枚举类
type FollowerEnum struct {
}

// ObserverEnum Observer 枚举类
type ObserverEnum struct {
}

// HotEnum 热节点 枚举类
type HotEnum struct {
}

// ColdEnum 冷节点 枚举类
type ColdEnum struct {
}

// WarmEnum 温节点 枚举类
type WarmEnum struct {
}

// RoleImp Doris角色方法接口
type RoleImp interface {
	Value() Role
	Group() Group
	InnerPort() int
}

// Value 返回角色的值
func (r *FollowerEnum) Value() Role {
	return Follower
}

// Group 返回角色所属的组
func (r *FollowerEnum) Group() Group {
	return Fronted
}

// InnerPort 返回角色的内部端口
func (r *FollowerEnum) InnerPort() int {
	return FeEditLogPort
}

// Value 返回角色的值
func (r *ObserverEnum) Value() Role {
	return Observer
}

// Group 返回角色所属的组
func (r *ObserverEnum) Group() Group {
	return Fronted
}

// InnerPort 返回角色的内部端口
func (r *ObserverEnum) InnerPort() int {
	return FeEditLogPort
}

// Value 返回角色的值
func (r *HotEnum) Value() Role {
	return Hot
}

// Group 返回角色所属的组
func (r *HotEnum) Group() Group {
	return Backend
}

// InnerPort 返回角色的内部端口
func (r *HotEnum) InnerPort() int {
	return BeHeartBeatPort
}

// Value 返回角色的值
func (r *ColdEnum) Value() Role {
	return Cold
}

// Group 返回角色所属的组
func (r *ColdEnum) Group() Group {
	return Backend
}

// InnerPort 返回角色的内部端口
func (r *ColdEnum) InnerPort() int {
	return BeHeartBeatPort
}

// Value 返回角色的值
func (r *WarmEnum) Value() Role {
	return Warm
}

// Group 返回角色所属的组
func (r *WarmEnum) Group() Group {
	return Backend
}

// InnerPort 返回角色的内部端口
func (r *WarmEnum) InnerPort() int {
	return BeHeartBeatPort
}

// RoleEnum 通过角色名string返回 Doris角色 枚举类
func RoleEnum(roleName string) RoleImp {
	switch roleName {
	case string(Follower):
		return &FollowerEnum{}
	case string(Observer):
		return &ObserverEnum{}
	case string(Hot):
		return &HotEnum{}
	case string(Cold):
		return &ColdEnum{}
	case string(Warm):
		return &WarmEnum{}
	}
	return nil
}

// RoleEnumByRole 通过Role 返回Doris角色 枚举类
func RoleEnumByRole(role Role) RoleImp {
	switch role {
	case Follower:
		return &FollowerEnum{}
	case Observer:
		return &ObserverEnum{}
	case Hot:
		return &HotEnum{}
	case Cold:
		return &ColdEnum{}
	case Warm:
		return &WarmEnum{}
	}
	return nil
}

// config item const define

const (
	PriorityNetworks = "priority_networks"
	StorageRootPath  = "storage_root_path"
	JavaOpts         = "JAVA_OPTS"
	JavaOpts17       = "JAVA_OPTS_FOR_JDK_17"
)

const (
	JavaOptsDefault   = "-Dfile.encoding=UTF-8 -Djavax.security.auth.useSubjectCredsOnly=false -Xss4m -Xmx%dm -XX:+UnlockExperimentalVMOptions -XX:+UseG1GC -XX:MaxGCPauseMillis=200 -XX:+PrintGCDateStamps -XX:+PrintGCDetails -XX:+PrintClassHistogramAfterFullGC -Xloggc:$LOG_DIR/log/fe.gc.log.$CUR_DATE -XX:+UseGCLogFileRotation -XX:NumberOfGCLogFiles=10 -XX:GCLogFileSize=50M -Dlog4j2.formatMsgNoLookups=true"
	JavaOpts17Default = "-Dfile.encoding=UTF-8 -Djavax.security.auth.useSubjectCredsOnly=false -Xmx%dm -XX:+HeapDumpOnOutOfMemoryError -XX:HeapDumpPath=$LOG_DIR -Xlog:gc*,classhisto*=trace:$LOG_DIR/fe.gc.log.$CUR_DATE:time,uptime:filecount=10,filesize=50M --add-opens=java.base/java.nio=ALL-UNNAMED --add-opens java.base/jdk.internal.ref=ALL-UNNAMED"
)

const (
	BootstrapStatusOK = 0
)

const (
	// DefaultCosEndpoint 默认的COS地址，内网，需要拼接上地域
	DefaultCosEndpoint = "cos-internal.%s.tencentcos.cn"
)
