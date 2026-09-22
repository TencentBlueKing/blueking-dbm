/**
 * MIT License
 *
 * Copyright (c) 2023 腾讯蓝鲸
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

package handler

import (
	"errors"
	"fmt"
	"sort"

	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/tools/internal/cluster/config"
	"dbm-services/common/dbha-v2/tools/internal/cluster/dbm"
)

// baseHandler holds the DBM client and the name-service helpers shared by every db type.
type baseHandler struct {
	dbmClient *dbm.Client
}

func newBaseHandler() baseHandler {
	return baseHandler{dbmClient: &dbm.Client{}}
}

const (
	resetClustersStartFmt = "=== Start to Reset %s Clusters, total: %d ==="
	resetClustersDoneFmt  = "=== Resetting %s Clusters Done, total: %d, failed: %d, success: %d ==="

	resetClusterKindMySQL        = "MySQL"
	resetClusterKindTenDBCluster = "TenDBCluster"
	resetClusterKindRedis        = "Redis"
)

func logResetf(format string, args ...any) {
	fmt.Printf(format+"\n", args...)
}

func logResetClustersStart(clusterKind string, total int) {
	logResetf(resetClustersStartFmt, clusterKind, total)
}

func logResetClustersDone(clusterKind string, total, failed, success int) {
	logResetf(resetClustersDoneFmt, clusterKind, total, failed, success)
}

func logResetStep(step int, format string, args ...any) {
	fmt.Printf("reset step %d: "+format+"\n", append([]any{step}, args...)...)
}

// ClusterHandler is the command surface of one cluster kind.
// baseHandler supplies a default "not implemented" for every command;
// each concrete handler overrides the commands it supports.
//
// Show* methods only collect data. The command layer merges every handler's
// result and prints a single JSON document.
type ClusterHandler interface {
	Reset() error
	ShowDomain() ([]ClusterDomainInfo, error)
	ShowNodes() ([]ClusterNodeInfo, error)
	ShowReplication() (any, error)
	ShowRouting() (any, error)
	ShowClb() ([]ClusterClbInfo, error)
	ShowSession(where string) ([]ClusterSessionInfo, error)
}

type notImplementedError struct {
	command string
}

func (e notImplementedError) Error() string {
	return e.command + " is not implemented"
}

func unimplemented(command string) error {
	return notImplementedError{command: command}
}

func isNotImplemented(err error) bool {
	var target notImplementedError
	return errors.As(err, &target)
}

func (hdl *baseHandler) unimplemented(command string) error {
	return unimplemented(command)
}

// Reset is the default implementation. Concrete handlers override it.
func (hdl *baseHandler) Reset() error {
	return hdl.unimplemented("reset")
}

// ShowDomain is the default implementation. Concrete handlers override it.
func (hdl *baseHandler) ShowDomain() ([]ClusterDomainInfo, error) {
	return nil, hdl.unimplemented("show domain")
}

// ShowNodes is the default implementation. Concrete handlers override it.
func (hdl *baseHandler) ShowNodes() ([]ClusterNodeInfo, error) {
	return nil, hdl.unimplemented("show nodes")
}

// ShowReplication is the default implementation. Concrete handlers override it.
func (hdl *baseHandler) ShowReplication() (any, error) {
	return nil, hdl.unimplemented("show replication")
}

// ShowRouting is the default implementation. Concrete handlers override it.
func (hdl *baseHandler) ShowRouting() (any, error) {
	return nil, hdl.unimplemented("show routing")
}

// ShowClb is the default implementation. Concrete handlers override it.
func (hdl *baseHandler) ShowClb() ([]ClusterClbInfo, error) {
	return nil, hdl.unimplemented("show clb")
}

// ShowSession is the default implementation. Concrete handlers override it.
func (hdl *baseHandler) ShowSession(where string) ([]ClusterSessionInfo, error) {
	return nil, hdl.unimplemented("show session")
}

func clbInstanceToIPPort(host string, port int) string {
	return fmt.Sprintf("%s:%d", host, port)
}

func clbInstancesToIPPorts(instances []config.InstanceAddress) []string {
	ips := make([]string, 0, len(instances))
	for _, inst := range instances {
		ips = append(ips, clbInstanceToIPPort(inst.Host, inst.Port))
	}
	return ips
}

func diffClbIPPortSets(desired, current []string) (missing, extra []string) {
	desiredSet := make(map[string]struct{}, len(desired))
	currentSet := make(map[string]struct{}, len(current))

	for _, ip := range desired {
		desiredSet[ip] = struct{}{}
	}
	for _, ip := range current {
		currentSet[ip] = struct{}{}
	}

	for ip := range desiredSet {
		if _, ok := currentSet[ip]; !ok {
			missing = append(missing, ip)
		}
	}
	for ip := range currentSet {
		if _, ok := desiredSet[ip]; !ok {
			extra = append(extra, ip)
		}
	}

	sort.Strings(missing)
	sort.Strings(extra)
	return missing, extra
}

func validateClbConfig(clb *config.ClbConfig) error {
	if clb.Region == "" {
		return gerrors.New(gerrors.InvalidParameter, "clb.region is empty, please configure it in cluster.yaml")
	}
	if clb.ListenerID == "" {
		return gerrors.New(gerrors.InvalidParameter, "clb.listenerId is empty, please configure it in cluster.yaml")
	}
	if clb.LoadBalancerID == "" {
		return gerrors.New(gerrors.InvalidParameter,
			"clb.loadbalancerId is empty, please configure it in cluster.yaml")
	}
	return nil
}

func (hdl *baseHandler) syncClbBinding(clb *config.ClbConfig) error {
	if err := validateClbConfig(clb); err != nil {
		return err
	}

	currentIPs, err := hdl.dbmClient.GetClbTargetPrivateIps(clb)
	if err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to get clb target private ips (region=%s, listenerId=%s), errmsg: %s",
			clb.Region, clb.ListenerID, err.Error())
	}

	desiredIPs := clbInstancesToIPPorts(clb.Instances)
	missing, extra := diffClbIPPortSets(desiredIPs, currentIPs)

	if err := hdl.dbmClient.RegisterClbPartTarget(clb, missing); err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to register clb targets (region=%s, listenerId=%s), errmsg: %s",
			clb.Region, clb.ListenerID, err.Error())
	}

	if err := hdl.dbmClient.DeregisterClbPartTarget(clb, extra); err != nil {
		return gerrors.Newf(gerrors.Failure,
			"failed to deregister clb targets (region=%s, listenerId=%s), errmsg: %s",
			clb.Region, clb.ListenerID, err.Error())
	}

	return nil
}

func (hdl *baseHandler) resetAllClbBindings(clbList []config.ClbConfig) error {
	for i := range clbList {
		if err := hdl.syncClbBinding(&clbList[i]); err != nil {
			return err
		}
	}
	return nil
}

func (hdl *baseHandler) queryClbBinding(clb *config.ClbConfig) (ClbBindingInfo, error) {
	if err := validateClbConfig(clb); err != nil {
		return ClbBindingInfo{}, err
	}

	instanceList, err := hdl.dbmClient.GetClbTargetPrivateIps(clb)
	if err != nil {
		return ClbBindingInfo{}, err
	}
	if instanceList == nil {
		instanceList = make([]string, 0)
	}

	return ClbBindingInfo{
		ClbID:        clb.LoadBalancerID,
		ListenerID:   clb.ListenerID,
		Region:       clb.Region,
		InstanceList: instanceList,
	}, nil
}

func (hdl *baseHandler) buildClusterClbInfo(domain string, clbConfigs []config.ClbConfig) (ClusterClbInfo, error) {
	clbList := make([]ClbBindingInfo, 0, len(clbConfigs))
	for i := range clbConfigs {
		binding, err := hdl.queryClbBinding(&clbConfigs[i])
		if err != nil {
			return ClusterClbInfo{}, gerrors.Newf(gerrors.Failure,
				"failed to get clb info for cluster(%s), errmsg: %s", domain, err.Error())
		}
		clbList = append(clbList, binding)
	}

	return ClusterClbInfo{
		Cluster: domain,
		ClbList: clbList,
	}, nil
}

// addNodesToDomain adds the instances missing from the domain, leaving the bound ones untouched.
func (hdl *baseHandler) addNodesToDomain(instList []config.InstanceAddress, domain string, bkBizId int) error {
	return hdl.addNodesToDomainInCloud(0, instList, domain, bkBizId)
}

// addNodesToDomainInCloud is addNodesToDomain scoped to a cloud area.
func (hdl *baseHandler) addNodesToDomainInCloud(bkCloudId int, instList []config.InstanceAddress,
	domain string, bkBizId int) error {
	instInfoList, err := hdl.dbmClient.GetAllInstancesOfDomainInCloud(bkCloudId, domain)
	if err != nil {
		return gerrors.Newf(gerrors.Failure, "failed to get all instances of domain %s, errmsg: %s", domain, err.Error())
	}

	isInDomain := func(ip string, port int) bool {
		for _, inst := range instInfoList {
			if inst.Ip == ip && inst.Port == port {
				return true
			}
		}
		return false
	}

	for _, inst := range instList {
		instHost := inst.Host
		instPort := inst.Port
		if isInDomain(instHost, instPort) {
			continue
		}
		if err := hdl.dbmClient.AddInstanceToDomainInCloud(bkCloudId, instHost, instPort, domain, bkBizId); err != nil {
			return gerrors.Newf(gerrors.Failure, "failed to add instance(%s:%d) to domain %s, errmsg: %s",
				instHost, instPort, domain, err.Error())
		}
	}

	return nil
}
