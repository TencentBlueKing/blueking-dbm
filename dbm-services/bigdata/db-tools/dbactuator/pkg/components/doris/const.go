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
	}
	return nil
}

// config item const define

const (
	PriorityNetworks = "priority_networks"
	StorageRootPath  = "storage_root_path"
	JavaOpts         = "JAVA_OPTS"
)

const (
	JavaOptsDefault = "-Djavax.security.auth.useSubjectCredsOnly=false -Xss4m -Xmx%dm -XX:+UseMembar -XX:SurvivorRatio=8 -XX:MaxTenuringThreshold=7 -XX:+PrintGCDateStamps -XX:+PrintGCDetails -XX:+UseConcMarkSweepGC -XX:+UseParNewGC -XX:+CMSClassUnloadingEnabled -XX:-CMSParallelRemarkEnabled -XX:CMSInitiatingOccupancyFraction=80 -XX:SoftRefLRUPolicyMSPerMB=0 -Xloggc:$DORIS_HOME/log/fe.gc.log.$CUR_DATE"
)

const (
	BootstrapStatusOK = 0
)
