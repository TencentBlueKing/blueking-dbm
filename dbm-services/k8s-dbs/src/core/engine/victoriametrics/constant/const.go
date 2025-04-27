package constant

const (
	ClusterName           = "victoria-metrics-cluster"
	ClusterDefinitionName = "victoria-metrics"
	CmpdNameByInsert      = "vm-insert"
	CmpdNameBySelect      = "vm-select"
	CmpdNameByStorage     = "vm-storage"

	SvcNameByInsert  = "vminsert"
	SvcNameBySelect  = "vmselect"
	SvcNameByStorage = "vmstorage"

	SvcKindByInsert  = "vminsert"
	SvcKindBySelect  = "vmselect"
	SvcKindByStorage = "vmstorage"

	InsertContainerName  = "vminsert"
	SelectContainerName  = "vmselect"
	StorageContainerName = "vmstorage"

	ComponentVersionName = "victoria-metrics"
	App                  = "app"
	AppLables            = "victoria-metrics"
	Description          = "description"
	AnnoDescrip          = "A victoriametrics cluster"
	ClusterTopologyName  = "vm-cluster-topo"
	Version              = "v1.93.1"
	VolumeName           = "surrealdb-volume"
	PVCName              = "pvc-manual"

	ImageForInsert  = "victoriametrics/vminsert:v1.93.1-cluster"
	ImageForSelect  = "victoriametrics/vmselect:v1.93.1-cluster"
	ImageForStorage = "victoriametrics/vmstorage:v1.93.1-cluster"

	ReleasesNameByInsert  = "vminsert-v1.93.1"
	ReleasesNameBySelect  = "vmselect-v1.93.1"
	ReleasesNameByStorage = "vmstorage-v1.93.1"

	CompTopoNameByInsert  = "vminsert"
	CompTopoNameBySelect  = "vmselect"
	CompTopoNameByStorage = "vmstorage"

	VolumeMountNameByStorage = "data"

	SurrealPath = "rocksdb:/usr/local/surrealdb/etc/demo/rocksdb154"

	BackupPolicyName = "surrealdb-bp"
	BackupName       = "surrealdb-bk"
	BackupMethodName = "surrealdb-backupmetgod"
)

// cluster default params
const (
	DefaultVersion = "1.93.1"

	DefaultReplicasByInsert       = 1
	DefaultPortByInsert           = 8480
	DefaultServiceVersionByInsert = "insert"
	DefaultCpuByInsert            = "1"
	DefaultMemByInsert            = "2Gi"
	DefaultStorageByInsert        = "20Gi"

	DefaultReplicasBySelect       = 1
	DefaultPortBySelect           = 8481
	DefaultServiceVersionBySelect = "select"
	DefaultCpuBySelect            = "1"
	DefaultMemBySelect            = "2Gi"
	DefaultStorageBySelect        = "20Gi"

	DefaultReplicasByStorage       = 1
	DefaultPortByStorage           = 8482
	DefaultServiceVersionByStorage = "storage"
	DefaultCpuByStorage            = "1"
	DefaultMemByStorage            = "2Gi"
	DefaultStorageByStorage        = "20Gi"
)
