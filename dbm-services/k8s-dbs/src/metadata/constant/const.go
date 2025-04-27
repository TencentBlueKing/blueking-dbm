package constant

const (
	TB_K8S_CRD_STORAGEADDON        = "tb_k8s_crd_storageaddon"
	TB_K8S_CRD_CLUSTERDEFINITION   = "tb_k8s_crd_clusterdefinition"
	TB_K8S_CRD_COMPONENTDEFINITION = "tb_k8s_crd_componentdefinition"
	TB_K8S_CRD_COMPONENTVERSION    = "tb_k8s_crd_componentversion"
	TB_K8S_CRD_CLUSTER             = "tb_k8s_crd_cluster"
	TB_K8S_CRD_COMPONENT           = "tb_k8s_crd_component"
	TB_K8S_CRD_OPSREQUEST          = "tb_k8s_crd_opsrequest"
	TB_K8S_CLUSTER_CONFIG          = "tb_k8s_cluster_config"
	TB_CLUSTER_REQUEST_RECORD      = "tb_cluster_request_record"
	TB_K8S_CLUSTER_SERVICE         = "tb_k8s_cluster_service"
)

// mysql connection credentials for test
const (
	MYSQL_URL = "test_user:teat_pwd@tcp(127.0.0.1:3306)/bkbase_dbs?charset=utf8mb4&parseTime=True&loc=Local"
)
