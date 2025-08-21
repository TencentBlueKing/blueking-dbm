package metric

import (
	coreconst "k8s-dbs/core/constant"
	"os"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestCreateAddon(t *testing.T) {
	_ = os.Setenv("VM_METRIC_SERVER_HOST", "localhost")
	_ = os.Setenv("VM_METRIC_SERVER_PORT", "80")
	var k8sClusterName = "BCS-K8S-0000"
	var job = "monitor-dbm4-vmstorage-headless"
	var namespace = "vm-dbm-0000"
	var podName = "monitor-test-vmstorage-0"
	var params = ClusterMetricQueryParams{
		AddonType:      coreconst.VM,
		Namespace:      namespace,
		JobName:        job,
		PodName:        podName,
		K8sClusterName: k8sClusterName,
	}
	storageUsage, err := FetcherFactory.GetStorageUsage(&params)
	if err != nil {
		panic(err)
	}
	assert.NotNil(t, storageUsage)
}
