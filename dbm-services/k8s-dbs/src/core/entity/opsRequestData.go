package entity

import (
	opv1 "github.com/apecloud/kubeblocks/apis/operations/v1alpha1"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime"
)

// OpsRequestData  the data parameter of the operation
type OpsRequestData struct {
	Metadata         Metadata          `json:"metadata,omitempty"`
	Spec             interface{}       `json:"spec,omitempty"`
	OpsRequestStatus *OpsRequestStatus `json:"status,omitempty"`
}

// OpsRequestStatus  the status parameter of the operation
type OpsRequestStatus struct {
	Phase        opv1.OpsPhase      `json:"phase,omitempty"`
	StartTime    metav1.Time        `json:"startTime,omitempty"`
	CompleteTime metav1.Time        `json:"completeTime,omitempty"`
	Messages     []metav1.Condition `json:"messages,omitempty"`
}

// GetOpsRequestData returns the data parameter of the operation
func GetOpsRequestData(opsRequest *unstructured.Unstructured) (*OpsRequestData, error) {
	var data *opv1.OpsRequest
	err := runtime.DefaultUnstructuredConverter.FromUnstructured(opsRequest.Object, &data)
	if err != nil {
		return nil, err
	}
	opsRequestData := &OpsRequestData{
		Metadata: Metadata{
			OpsRequestName: data.Name,
			Namespace:      data.Namespace,
			Kind:           data.Kind,
			Labels:         data.Labels,
			Annotations:    data.Annotations,
		},
		Spec: data.Spec,
		OpsRequestStatus: &OpsRequestStatus{
			Phase:        data.Status.Phase,
			StartTime:    data.Status.StartTimestamp,
			CompleteTime: data.Status.CompletionTimestamp,
			Messages:     data.Status.Conditions,
		},
	}
	return opsRequestData, nil
}
