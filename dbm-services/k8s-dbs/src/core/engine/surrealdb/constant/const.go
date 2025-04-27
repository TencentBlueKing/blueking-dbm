package constant

const (
	ClusterName             = "cluster"
	ClusterDefinitionName   = "surreal"
	ComponentDefinitionName = "surreal"
	ComponentVersionName    = "surreal"
	ComponentServiceName    = "surreal-src"
	App                     = "app"
	AppLables               = "surreal"
	Description             = "description"
	AnnoDescrip             = "A surreal cluster"
	ClusterTopologyName     = "surreal"

	VolumeName            = "surreal-volume"
	PVCName               = "pvc-manual"
	Image                 = "docker.io/surrealdb/surrealdb:v2.1.3"
	ContainerName         = "surreal"
	ReleasesName          = "surreal"
	CompTopoNameBySurreal = "surreal"

	MountPath        = "/var/lib"
	SurrealPath      = "rocksdb:" + MountPath + "/surrealdb"
	BackupPolicyName = "surreal-bp"
	BackupName       = "surreal-bk"
	BackupMethodName = "surreal-backupMetGod"
	ServiceKind      = "surreal"
)

// cluster default params
const (
	DefaultVersion        = "2.1.3"
	DefalutReplicas       = 1
	DefaultPort           = 8000
	DefaultServiceVersion = "surreal"
	DefaultUserName       = "root"
	DefaultPassword       = "surreal"
	DefaultCPU            = "1"
	DefaultMem            = "2Gi"
	DefaultStorage        = "20Gi"
)
