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

package switchcore

import (
	"context"
	"errors"
	"strings"

	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
	"dbm-services/common/dbha-v2/pkg/gerrors"
)

// errIfCtxDoneInClusterSwitch returns the error if ctx is non-nil
// and the context is canceled or expired, otherwise nil.
func errIfCtxDoneInClusterSwitch(ctx context.Context, swCluster SwitchableCluster) error {
	if ctx == nil {
		return nil
	}

	if err := ctx.Err(); err != nil {
		if errors.Is(err, context.DeadlineExceeded) {
			swCluster.ReportClusterLogf(switchlogger.SwitchError, "switching timeout: %s", err.Error())
			return err
		}

		swCluster.ReportClusterLogf(switchlogger.SwitchError, "switching context done: %s", err.Error())
		return err
	}

	return nil
}

// checkStatusForClusterSwitch checks the status of instances in the cluster
func checkStatusForClusterSwitch(ctx context.Context, swCluster SwitchableCluster) error {
	if err := errIfCtxDoneInClusterSwitch(ctx, swCluster); err != nil {
		return err
	}

	insts := swCluster.GetSwitchInstances()
	wrongStatusInsts := []string{}

	for instKey, instMeta := range insts {
		if (instMeta.Status != dbm.Running) && (instMeta.Status != dbm.Available) {
			wrongStatusInsts = append(wrongStatusInsts, string(instKey))
			swCluster.ReportLogf(instKey, switchlogger.SwitchError,
				"pre-status check unpass for wrong status: %s", instMeta.Status)
		}

		swCluster.ReportLogf(instKey, switchlogger.SwitchInfo, "pre-status check pass with status: %s", instMeta.Status)
	}

	if len(wrongStatusInsts) > 0 {
		return gerrors.Newf(gerrors.Failure, "found wrong status instances: %s", strings.Join(wrongStatusInsts, ", "))
	}

	swCluster.ReportClusterLogf(switchlogger.SwitchInfo, "pre-status check pass with %d instances", len(insts))

	return nil
}

// setStatusForClusterSwitch sets the status of instances in the cluster to unavailable.
func setStatusForClusterSwitch(ctx context.Context, swCluster SwitchableCluster) error {
	if err := errIfCtxDoneInClusterSwitch(ctx, swCluster); err != nil {
		return err
	}

	if err := swCluster.SetInstanceUnavailable(); err != nil {
		return err
	}

	return nil
}

// doCheckBeforeClusterSwitch checks if the cluster is required to be switched.
func doCheckBeforeClusterSwitch(ctx context.Context, swCluster SwitchableCluster) (SwitchCheckCode, error) {
	if err := errIfCtxDoneInClusterSwitch(ctx, swCluster); err != nil {
		return SwitchCheckUnpass, err
	}

	return swCluster.CheckBeforeSwitch()
}

// doSwitchInClusterSwitch calls the DoSwitch method of the switchable cluster and returns the error.
func doSwitchInClusterSwitch(ctx context.Context, swCluster SwitchableCluster) error {
	if err := errIfCtxDoneInClusterSwitch(ctx, swCluster); err != nil {
		return err
	}

	if err := swCluster.DoSwitch(); err != nil {
		retErr := gerrors.Newf(gerrors.Failure, "failed to do switch: %s", err.Error())
		swCluster.ReportClusterLogf(switchlogger.SwitchError, "%s", retErr.Error())
		return retErr
	}

	swCluster.ReportClusterLogf(switchlogger.SwitchInfo, "successfully do switch")
	return nil
}

// doUpdateMetaInfoInClusterSwitch calls UpdateMetaInfo on the switchable cluster.
func doUpdateMetaInfoInClusterSwitch(ctx context.Context, swCluster SwitchableCluster) error {
	if err := errIfCtxDoneInClusterSwitch(ctx, swCluster); err != nil {
		return err
	}

	if err := swCluster.UpdateMetaInfo(); err != nil {
		retErr := gerrors.Newf(gerrors.Failure, "failed to update meta info: %s", err.Error())
		swCluster.ReportClusterLogf(switchlogger.SwitchError, "%s", retErr.Error())
		return retErr
	}

	swCluster.ReportClusterLogf(switchlogger.SwitchInfo, "successfully update meta info")
	return nil
}

// doFinalInClusterSwitch calls DoFinal on the switchable cluster.
func doFinalInClusterSwitch(ctx context.Context, swCluster SwitchableCluster) error {
	if err := errIfCtxDoneInClusterSwitch(ctx, swCluster); err != nil {
		return err
	}

	if err := swCluster.DoFinal(); err != nil {
		retErr := gerrors.Newf(gerrors.Failure, "failed to do final step: %s", err.Error())
		swCluster.ReportClusterLogf(switchlogger.SwitchError, "%s", retErr.Error())
		return retErr
	}

	swCluster.ReportClusterLogf(switchlogger.SwitchInfo, "successfully do final step")
	return nil
}

// SwitchSameClusterInstances switches instances in the same cluster.
// It returns true if all instances are switched successfully, otherwise returns false.
func SwitchSameClusterInstances(ctx context.Context, swCluster SwitchableCluster) (switchSuccess bool, retErr error) {
	// rollback when error occurs
	defer func() {
		if switchSuccess {
			swCluster.ReportClusterLogf(switchlogger.SwitchInfo,
				"successfully switch cluster: %s", swCluster.GetClusterInfo())
			return
		}

		if retErr == nil {
			retErr = gerrors.New(gerrors.Failure, "unknown error occurred")
		}

		swCluster.ReportClusterLogf(switchlogger.SwitchError,
			"failed to switch cluster: %s", swCluster.GetClusterInfo())

		if rollbackErr := swCluster.RollBack(); rollbackErr != nil {
			swCluster.ReportClusterLogf(switchlogger.SwitchError, "failed to rollback switch: %s", rollbackErr.Error())
			retErr = gerrors.Newf(gerrors.Failure, "switch errmsg: %s, rollback errmsg: %s",
				retErr.Error(), rollbackErr.Error())
		}
	}()

	swCluster.ReportClusterLogf(switchlogger.SwitchInfo, "start to switch cluster: %s", swCluster.GetClusterInfo())

	if err := checkStatusForClusterSwitch(ctx, swCluster); err != nil {
		return false, err
	}

	if err := setStatusForClusterSwitch(ctx, swCluster); err != nil {
		return false, err
	}

	if err := errIfCtxDoneInClusterSwitch(ctx, swCluster); err != nil {
		return false, err
	}

	clusterLogFunc := func(level switchlogger.SwitchLogLevel, format string, args ...any) bool {
		return swCluster.ReportClusterLogf(level, format, args...)
	}

	// lock current cluster
	clusterKey := GenerateClusterKey(swCluster.GetBkCloudID(), swCluster.GetClusterID())
	unlock, lockErr := LockClusterWithTimeout(clusterLogFunc, clusterKey, ClusterLockTimeout())
	if lockErr != nil {
		return false, lockErr
	}
	defer unlock()

	checkRes, checkErr := doCheckBeforeClusterSwitch(ctx, swCluster)
	if checkRes == SwitchCheckUnpass {
		return false, checkErr
	}

	if checkRes == SwitchNotNeeded {
		return true, checkErr
	}

	if err := doSwitchInClusterSwitch(ctx, swCluster); err != nil {
		return false, err
	}

	if err := doUpdateMetaInfoInClusterSwitch(ctx, swCluster); err != nil {
		return false, err
	}

	if err := doFinalInClusterSwitch(ctx, swCluster); err != nil {
		return false, err
	}

	return true, nil
}
