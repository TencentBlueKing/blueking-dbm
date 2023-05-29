package constvar

const (
	// Environment TODO
	Environment = "enviroment"
	// Test TODO
	Test = "test"
)

// RequestType
const (
	MethodSaveOnly       = "SaveOnly"       // save only
	MethodSaveAndPublish = "SaveAndPublish" // snapshot version
)
const (
	// OPTypeAdd TODO
	OPTypeAdd = "add"
	// OPTypeUpdate TODO
	OPTypeUpdate = "update"
	// OPTypeRemove TODO
	OPTypeRemove = "remove"
	// OPTypeRemoveRef TODO
	OPTypeRemoveRef = "remove_ref" // 非用户操作的直接删除，而是用户操作需要级联删除

	// OPTypeLocked TODO
	OPTypeLocked = "locked"
	// OPTypeNotified TODO
	OPTypeNotified = "notify"
)

// config file version generate method
const (
	MethodGenerateOnly  = "GenerateOnly"       // generate only
	MethodGenAndSave    = "GenerateAndSave"    // snapshot
	MethodGenAndPublish = "GenerateAndPublish" // release
	MethodSave          = "Save"               // 只用于保存 无版本概念 的配置类型 no-versioned
)

// BKBizIDForPlat TODO
const BKBizIDForPlat = "0"
const (
	// LevelPlat TODO
	LevelPlat = "plat" // 平台级配置
	// LevelApp TODO
	LevelApp = "app" // 业务级配置
	// LevelModule TODO
	LevelModule = "module" // 模块级配置
	// LevelCluster TODO
	LevelCluster = "cluster" // 集群级配置
	// LevelHost TODO
	LevelHost = "host" // 主机级配置
	// LevelInstance TODO
	LevelInstance = "instance" // 实例级配置
)

// conf_type
const (
	ConfTypeMycnf  = "dbconf" // 数据库参数配置
	ConfTypeBackup = "backup" // 数据库备份配置
	ConfTypeDeploy = "deploy" // 部署类配置
)

const (
	// FormatMap TODO
	FormatMap = "map"
	// FormatList TODO
	FormatList = "list"
	// ViewRaw TODO
	ViewRaw = "raw"
	// ViewMerge TODO
	ViewMerge = "merge"
)

// BKApiAuthorization bkapigw
const BKApiAuthorization = "X-Bkapi-Authorization"

// DraftVersion TODO
const DraftVersion = "v_draft"

// EncryptEnableZip TODO
const EncryptEnableZip = false
