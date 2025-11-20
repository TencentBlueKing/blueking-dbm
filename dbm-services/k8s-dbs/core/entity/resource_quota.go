package entity

import "k8s.io/apimachinery/pkg/api/resource"

// ResourceQuota 定义资源配额结构
type ResourceQuota struct {
	Request Resource `json:"request,omitempty"`
	Limit   Resource `json:"limit,omitempty"`
}

// Resource defines the CPU and memory requests and limits for a Kubernetes component.
type Resource struct {
	CPU    resource.Quantity `json:"cpu,omitempty" binding:"omitempty,cpuQuantity" msg:"cpu 配置有误，范围 1Core～48Core"`
	Memory resource.Quantity `json:"memory,omitempty" binding:"omitempty,memoryQuantity" msg:"memory 配置有误，范围 1GB～128GB"`
}
