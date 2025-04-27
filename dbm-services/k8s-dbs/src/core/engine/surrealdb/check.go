package surrealdb

import (
	"fmt"
	"k8s-dbs/src/core/engine/surrealdb/constant"
	"k8s-dbs/src/core/entity"
	"strings"

	"github.com/gin-gonic/gin"
)

// InitRequestParams Init Request Params for SurrealDB
func (s *Surreal) InitRequestParams(ctx *gin.Context, request *entity.Request) error {
	// check Metadata
	metadata := request.Metadata
	path := ctx.Request.URL.Path
	if strings.Contains(path, "/:engineType") {
		if request.Metadata.ClusterName == "" {
			return fmt.Errorf("clusterName parameter is required")
		}
	} else if strings.Contains(path, "/opsRequest") {
		// 关于 ops 的请求
		if strings.Contains(path, "/describe") || strings.Contains(path, "/status") {
			// /describe 和 /status 只需要 opsRequestName
			if request.Metadata.OpsRequestName == "" {
				return fmt.Errorf("opsRequestName parameter is required")
			}
		} else {
			if request.Metadata.ClusterName == "" {
				return fmt.Errorf("clusterName parameter is required")
			}
			if request.Metadata.OpsRequestName == "" {
				return fmt.Errorf("opsRequestName parameter is required")
			}
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
	surrealComponent, exists := request.Spec.ComponentMap["surreal"]
	if !exists {
		surrealComponent = entity.ComponentResource{}
	}
	if surrealComponent.Replicas == 0 {
		surrealComponent.Replicas = int32(constant.DefalutReplicas)
	}
	if surrealComponent.Connect.Host == "" {
		surrealComponent.Connect.Host = request.Metadata.ClusterName + "-" + constant.DefaultServiceVersion + "." + request.Metadata.Namespace + ".svc.cluster.local"
	}
	if surrealComponent.Connect.Port == 0 {
		surrealComponent.Connect.Port = int32(constant.DefaultPort)
	}
	if surrealComponent.Connect.User == "" {
		surrealComponent.Connect.User = constant.DefaultUserName
	}
	if surrealComponent.Connect.Password == "" {
		surrealComponent.Connect.Password = constant.DefaultPassword
	}
	if surrealComponent.Request.Cpu == "" {
		surrealComponent.Request.Cpu = constant.DefaultCPU
	}
	if surrealComponent.Request.Memory == "" {
		surrealComponent.Request.Memory = constant.DefaultMem
	}
	if surrealComponent.Limit.Cpu == "" {
		surrealComponent.Limit.Cpu = constant.DefaultCPU
	}
	if surrealComponent.Limit.Memory == "" {
		surrealComponent.Limit.Memory = constant.DefaultMem
	}
	if surrealComponent.Storage == "" {
		surrealComponent.Storage = constant.DefaultStorage
	}
	s.surreal = &surrealComponent
	return nil
}
