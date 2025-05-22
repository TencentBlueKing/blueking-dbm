package resp

import (
	kbv1 "github.com/apecloud/kubeblocks/apis/apps/v1alpha1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// ClusterStatusRespVo cluster status response
type ClusterStatusRespVo struct {
	Phase      kbv1.ClusterPhase `json:"phase,omitempty"`
	CreateTime metav1.Time       `json:"createTime,omitempty"`
	UpdateTime metav1.Time       `json:"updateTime,omitempty"`
}
