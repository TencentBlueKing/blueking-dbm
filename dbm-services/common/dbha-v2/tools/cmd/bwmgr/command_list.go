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

func newListCmd(a *app) *cobra.Command {
	listCmd := &cobra.Command{
		Use:   cmdUseList,
		Short: cmdShortList,
		Long:  cmdLongList,
		RunE: func(cmd *cobra.Command, args []string) error {
			opts, err := newListOptions(cmd)
			if err != nil {
				return err
			}

			return a.withHandler(func(h *handler.Handler) error {
				return h.List(opts)
			})
		},
	}

	listCmd.Flags().Int(flagBkBizID, defaultIntValue, flagUsageListBizID)
	listCmd.Flags().Int(flagBkCloudID, defaultIntValue, flagUsageListCloudID)
	listCmd.Flags().Int(flagClusterID, defaultIntValue, flagUsageListClusterID)
	listCmd.Flags().String(flagClusterName, defaultStringValue, flagUsageListCluster)
	listCmd.Flags().String(flagSwitchVersion, defaultStringValue, flagUsageListSwitch)
	listCmd.Flags().String(flagStatus, defaultStringValue, flagUsageListStatus)

	return listCmd
}

func newListOptions(cmd *cobra.Command) (handler.ListOptions, error) {
	bkBizID, err := cmd.Flags().GetInt(flagBkBizID)
	if err != nil {
		return handler.ListOptions{}, err
	}

	bkCloudID, err := cmd.Flags().GetInt(flagBkCloudID)
	if err != nil {
		return handler.ListOptions{}, err
	}

	clusterID, err := cmd.Flags().GetInt(flagClusterID)
	if err != nil {
		return handler.ListOptions{}, err
	}

	clusterName, err := cmd.Flags().GetString(flagClusterName)
	if err != nil {
		return handler.ListOptions{}, err
	}

	switchVersion, err := cmd.Flags().GetString(flagSwitchVersion)
	if err != nil {
		return handler.ListOptions{}, err
	}

	status, err := cmd.Flags().GetString(flagStatus)
	if err != nil {
		return handler.ListOptions{}, err
	}

	return handler.ListOptions{
		BkBizID:       bkBizID,
		BkCloudID:     bkCloudID,
		ClusterID:     clusterID,
		ClusterName:   clusterName,
		SwitchVersion: switchVersion,
		Status:        status,
	}, nil
}
