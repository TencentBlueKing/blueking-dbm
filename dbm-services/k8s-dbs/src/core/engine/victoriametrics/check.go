package victoriametrics

import (
	"fmt"
	"k8s-dbs/src/core/engine/victoriametrics/constant"
	"k8s-dbs/src/core/entity"
	"strings"

	"github.com/gin-gonic/gin"
)

func (v *Victoriametrics) InitRequestParams(ctx *gin.Context, request *entity.Request) error {
	// check Metadata
	metadata := request.Metadata
	path := ctx.Request.URL.Path
	if strings.Contains(path, "/:engineType") {
		metadata := request.Metadata
		if metadata.ClusterName == "" {
			return fmt.Errorf("clusterName parameter is required")
		}
	} else if strings.Contains(path, "/:opsType") {
		metadata := request.Metadata
		if metadata.OpsRequestName == "" {
			return fmt.Errorf("opsRequestName parameter is required")
		}
	}
	if request.Metadata.Namespace == "" {
		return fmt.Errorf("namespace parameter is required")
	}
	if metadata.Labels == nil {
		metadata.Labels = make(map[string]string)
	}
	if metadata.Labels[constant.App] == "" {
		metadata.Labels[constant.App] = constant.AppLables
	}
	if metadata.Annotations == nil {
		metadata.Annotations = make(map[string]string)
	}
	if metadata.Annotations[constant.Description] == "" {
		metadata.Annotations[constant.Description] = constant.AnnoDescrip
	}

	// check spec
	spec := request.Spec
	if spec.Version == "" {
		spec.Version = constant.DefaultVersion
	}

	// check surreal component
	if request.Spec.ComponentMap == nil {
		request.Spec.ComponentMap = map[string]entity.ComponentResource{}
	}
	vminsert, exists := request.Spec.ComponentMap["vminsert"]
	if !exists {
		vminsert = entity.ComponentResource{}
	}
	if vminsert.Replicas == 0 {
		vminsert.Replicas = int32(constant.DefaultReplicasByInsert)
	}
	if vminsert.Connect.Host == "" {
		vminsert.Connect.Host = request.Metadata.ClusterName + "-" + constant.DefaultServiceVersionByInsert + "." + request.Metadata.Namespace + ".svc.cluster.local"
	}
	if vminsert.Connect.Port == 0 {
		vminsert.Connect.Port = int32(constant.DefaultPortByInsert)
	}
	if vminsert.Request.Cpu == "" {
		vminsert.Request.Cpu = constant.DefaultCpuByInsert
	}
	if vminsert.Request.Memory == "" {
		vminsert.Request.Memory = constant.DefaultMemByInsert
	}
	if vminsert.Limit.Cpu == "" {
		vminsert.Limit.Cpu = constant.DefaultCpuByInsert
	}
	if vminsert.Limit.Memory == "" {
		vminsert.Limit.Memory = constant.DefaultMemByInsert
	}
	if vminsert.Storage == "" {
		vminsert.Storage = constant.DefaultStorageByInsert
	}

	vmselect, exists := request.Spec.ComponentMap["vmselect"]
	if !exists {
		vmselect = entity.ComponentResource{}
	}
	if vmselect.Replicas == 0 {
		vmselect.Replicas = int32(constant.DefaultReplicasBySelect)
	}
	if vmselect.Connect.Host == "" {
		vmselect.Connect.Host = request.Metadata.ClusterName + "-" + constant.DefaultServiceVersionBySelect + "." + request.Metadata.Namespace + ".svc.cluster.local"
	}
	if vmselect.Connect.Port == 0 {
		vmselect.Connect.Port = int32(constant.DefaultPortBySelect)
	}
	if vmselect.Request.Cpu == "" {
		vmselect.Request.Cpu = constant.DefaultCpuBySelect
	}
	if vmselect.Request.Memory == "" {
		vmselect.Request.Memory = constant.DefaultMemBySelect
	}
	if vmselect.Limit.Cpu == "" {
		vmselect.Limit.Cpu = constant.DefaultCpuBySelect
	}
	if vmselect.Limit.Memory == "" {
		vmselect.Limit.Memory = constant.DefaultMemBySelect
	}
	if vmselect.Storage == "" {
		vmselect.Storage = constant.DefaultStorageBySelect
	}

	vmstorage, exists := request.Spec.ComponentMap["vmstorage"]
	if !exists {
		vmstorage = entity.ComponentResource{}
	}
	if vmstorage.Replicas == 0 {
		vmstorage.Replicas = int32(constant.DefaultReplicasByStorage)
	}
	if vmstorage.Connect.Host == "" {
		vmstorage.Connect.Host = request.Metadata.ClusterName + "-" + constant.DefaultServiceVersionByStorage + "." + request.Metadata.Namespace + ".svc.cluster.local"
	}
	if vmstorage.Connect.Port == 0 {
		vmstorage.Connect.Port = int32(constant.DefaultPortByStorage)
	}
	if vmstorage.Request.Cpu == "" {
		vmstorage.Request.Cpu = constant.DefaultCpuByStorage
	}
	if vmstorage.Request.Memory == "" {
		vmstorage.Request.Memory = constant.DefaultMemByStorage
	}
	if vmstorage.Limit.Cpu == "" {
		vmstorage.Limit.Cpu = constant.DefaultCpuByStorage
	}
	if vmstorage.Limit.Memory == "" {
		vmstorage.Limit.Memory = constant.DefaultMemByStorage
	}
	if vmstorage.Storage == "" {
		vmstorage.Storage = constant.DefaultStorageByStorage
	}

	v.vminsert = &vminsert
	v.vmselect = &vmselect
	v.vmstorage = &vmstorage
	return nil
}
