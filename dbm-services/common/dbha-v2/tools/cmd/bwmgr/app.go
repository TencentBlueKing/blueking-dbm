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
	"dbm-services/common/dbha-v2/pkg/gerrors"
	"dbm-services/common/dbha-v2/tools/internal/bwmgr/config"
	"dbm-services/common/dbha-v2/tools/internal/bwmgr/handler"

	"github.com/spf13/cobra"
)

type app struct {
	configFilePath   string
	apiEndpointFlag  string
	apiBkCloudIDFlag int
	apiTokenFlag     string
	apiTimeoutFlag   string
}

func newApp() *app {
	return &app{}
}

func (a *app) execute() error {
	return a.newRootCmd().Execute()
}

func (a *app) newRootCmd() *cobra.Command {
	rootCmd := &cobra.Command{
		Use:          cmdUseRoot,
		Short:        cmdShortRoot,
		Long:         cmdLongRoot,
		SilenceUsage: true,
	}
	rootCmd.CompletionOptions.DisableDefaultCmd = true

	a.bindPersistentFlags(rootCmd)
	a.registerCommands(rootCmd)

	return rootCmd
}

func (a *app) bindPersistentFlags(rootCmd *cobra.Command) {
	flags := rootCmd.PersistentFlags()

	flags.StringVarP(&a.configFilePath, flagConfig, flagConfigShort, defaultConfigFilePath, flagUsageConfig)

	flags.StringVar(&a.apiEndpointFlag, flagAPIEndpoint, defaultStringValue, flagUsageAPIEndpoint)
	flags.IntVar(&a.apiBkCloudIDFlag, flagAPIBkCloudID, defaultIntValue, flagUsageAPIBkCloudID)
	flags.StringVar(&a.apiTokenFlag, flagAPIToken, defaultStringValue, flagUsageAPIToken)
	flags.StringVar(&a.apiTimeoutFlag, flagAPITimeout, defaultStringValue, flagUsageAPITimeout)
}

func (a *app) registerCommands(rootCmd *cobra.Command) {
	for _, factory := range commandFactories() {
		rootCmd.AddCommand(factory(a))
	}
}

func (a *app) buildCmdFlags() map[string]interface{} {
	flags := make(map[string]interface{})
	if a.apiEndpointFlag != "" {
		flags[flagAPIEndpoint] = a.apiEndpointFlag
	}

	if a.apiBkCloudIDFlag >= 0 {
		flags[flagAPIBkCloudID] = a.apiBkCloudIDFlag
	}

	if a.apiTokenFlag != "" {
		flags[flagAPIToken] = a.apiTokenFlag
	}

	if a.apiTimeoutFlag != "" {
		flags[flagAPITimeout] = a.apiTimeoutFlag
	}

	return flags
}

func (a *app) newHandler() (*handler.Handler, error) {
	cfg, err := config.LoadConfig(a.configFilePath, a.buildCmdFlags())
	if err != nil {
		return nil, gerrors.Newf(gerrors.Failure, errLoadConfigFormat, err)
	}

	return handler.NewHandler(cfg), nil
}

func (a *app) withHandler(run func(*handler.Handler) error) error {
	h, err := a.newHandler()
	if err != nil {
		return err
	}

	return run(h)
}
