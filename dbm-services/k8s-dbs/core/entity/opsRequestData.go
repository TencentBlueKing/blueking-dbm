/*
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.

Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.

Licensed under the MIT License (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
https://opensource.org/licenses/MIT

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

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
