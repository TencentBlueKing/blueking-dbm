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

package main

import (
	"dbm-services/common/dbha-v2/tools/internal/bwmgr/handler"

	"github.com/spf13/cobra"
)

func newAddCmd(a *app) *cobra.Command {
	addCmd := &cobra.Command{
		Use:   cmdUseAdd,
		Short: cmdShortAdd,
		Long:  cmdLongAdd,
		RunE: func(cmd *cobra.Command, args []string) error {
			opts, err := newAddOptions(cmd)
			if err != nil {
				return err
			}

			return a.withHandler(func(h *handler.Handler) error {
				return h.Add(opts)
			})
		},
	}

	addCmd.Flags().Int(flagBkBizID, defaultIntValue, flagUsageBizIDRequired)
	addCmd.Flags().Int(flagBkCloudID, defaultIntValue, flagUsageCloudDefault)
	addCmd.Flags().Int(flagClusterID, defaultIntValue, flagUsageClusterIDReq)
	addCmd.Flags().String(flagClusterName, defaultStringValue, flagUsageClusterNameReq)
	addCmd.Flags().String(flagSwitchVersion, defaultSwitchVersion, flagUsageSwitchDefault)
	addCmd.Flags().String(flagStatus, defaultStatus, flagUsageStatusDefault)
	addCmd.Flags().Bool(flagUpsert, defaultFalseValue, flagUsageUpsert)
	addCmd.Flags().Bool(flagYes, defaultFalseValue, flagUsageYesRisky)

	return addCmd
}

func newAddOptions(cmd *cobra.Command) (handler.AddOptions, error) {
	bkBizID, err := cmd.Flags().GetInt(flagBkBizID)
	if err != nil {
		return handler.AddOptions{}, err
	}

	bkCloudID, err := cmd.Flags().GetInt(flagBkCloudID)
	if err != nil {
		return handler.AddOptions{}, err
	}

	clusterID, err := cmd.Flags().GetInt(flagClusterID)
	if err != nil {
		return handler.AddOptions{}, err
	}

	clusterName, err := cmd.Flags().GetString(flagClusterName)
	if err != nil {
		return handler.AddOptions{}, err
	}

	switchVersion, err := cmd.Flags().GetString(flagSwitchVersion)
	if err != nil {
		return handler.AddOptions{}, err
	}

	status, err := cmd.Flags().GetString(flagStatus)
	if err != nil {
		return handler.AddOptions{}, err
	}

	upsert, err := cmd.Flags().GetBool(flagUpsert)
	if err != nil {
		return handler.AddOptions{}, err
	}

	yes, err := cmd.Flags().GetBool(flagYes)
	if err != nil {
		return handler.AddOptions{}, err
	}

	return handler.AddOptions{
		BkBizID:          bkBizID,
		BkCloudID:        bkCloudID,
		ClusterID:        clusterID,
		ClusterName:      clusterName,
		SwitchVersion:    switchVersion,
		Status:           status,
		Upsert:           upsert,
		Yes:              yes,
		Confirm:          confirm,
		ClusterNameSet:   cmd.Flags().Changed(flagClusterName),
		SwitchVersionSet: cmd.Flags().Changed(flagSwitchVersion),
		StatusSet:        cmd.Flags().Changed(flagStatus),
	}, nil
}
