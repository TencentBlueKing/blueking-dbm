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

package switcher

import (
	"context"

	"dbm-services/common/dbha-v2/internal/analysis/apm"
	"dbm-services/common/dbha-v2/internal/analysis/dbm"
	rsw "dbm-services/common/dbha-v2/internal/analysis/switcher/redis"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchcore"
	"dbm-services/common/dbha-v2/internal/analysis/switcher/switchlogger"
	"dbm-services/common/dbha-v2/pkg/logger"
	"dbm-services/common/dbha-v2/pkg/storage/haprobe"
)

var _ Switcher = (*Redis)(nil)

// Redis implements dormant redis switch flow in v2.
type Redis struct{}

// DbTypeName returns redis db type.
func (r *Redis) DbTypeName() haprobe.DbType {
	return haprobe.DbTypeRedis
}

// AlarmEvents returns redis switch success/failure event names.
func (r *Redis) AlarmEvents() AlarmEvents {
	return AlarmEvents{
		Success: haprobe.DbEventNameRedisSwitchSuccessV1,
		Failure: haprobe.DbEventNameRedisSwitchFailureV1,
	}
}

// NewSwitchLogger creates redis switch loggers.
func (r *Redis) NewSwitchLogger() ([]switchlogger.DbSwitchLogger, error) {
	loggers := []switchlogger.DbSwitchLogger{
		switchlogger.NewLogToStdHandler(),
	}

	dbHdl, err := switchlogger.NewLogToDbHandlerFromConfig()
	if err != nil {
		return loggers, err
	}

	if err = dbHdl.Open(); err != nil {
		return loggers, err
	}

	loggers = append(loggers, dbHdl)
	return loggers, nil
}

func (r *Redis) reportMetrics(req *Request, rsp *Response) {
	if err := apm.RedisSwitchingSuccessTotal.AddWithLabels(
		map[string]string{
			apm.MetricLabelActionScope: string(req.ActionScope),
			apm.MetricLabelDbType:      string(r.DbTypeName()),
		},
		float64(len(req.MySqlInstData)-len(rsp.MySqlFailureInsts)),
	); err != nil {
		logger.Warn("failed to update redis switching success metric, errmsg: %s", err)
	}

	if err := apm.RedisSwitchingErrorTotal.AddWithLabels(
		map[string]string{
			apm.MetricLabelActionScope: string(req.ActionScope),
			apm.MetricLabelDbType:      string(r.DbTypeName()),
		},
		float64(len(rsp.MySqlFailureInsts)),
	); err != nil {
		logger.Warn("failed to update redis switching error metric, errmsg: %s", err)
	}

}

// Switch runs redis instance switch flow through switchcore.
func (r *Redis) Switch(ctx context.Context, req *Request) *Response {
	rsp := &Response{
		MySqlFailureInsts: map[switchcore.MetadataKey]*dbm.DbInstMetadata{},
	}
	if req == nil {
		rsp.Err = ErrSwitchPartialSuccess
		return rsp
	}

	switchLoggers, err := r.NewSwitchLogger()
	if err != nil {
		logger.Warn("failed to create redis switch db logger, errmsg: %s", err)
	}
	defer func() {
		for _, swlogger := range switchLoggers {
			swlogger.Close()
		}
	}()

	for _, meta := range req.MySqlInstData {
		if meta == nil {
			continue
		}

		instKey := switchcore.GenerateMetadataKey(meta.BkCloudID, meta.IP, meta.Port)
		swInst, newErr := rsw.NewSwitchInstance(meta)
		if newErr != nil {
			logger.Warn("failed to construct redis switch instance, inst: %s, errmsg: %s", instKey, newErr)
			rsp.AddFailureInst(instKey, meta)
			continue
		}

		swInst.SetSwitchID(req.SwitchID)
		swInst.SetActionScope(req.ActionScope)
		swInst.SetSwitchLogger(switchLoggers)

		ok, swErr := switchcore.SwitchSingleInstance(ctx, swInst)
		if ok {
			continue
		}

		if swErr != nil {
			logger.Warn("redis switching failed, inst: %s, errmsg: %s", instKey, swErr)
		}
		rsp.AddFailureInst(instKey, meta)
	}

	if len(rsp.MySqlFailureInsts) > 0 {
		rsp.Err = ErrSwitchPartialSuccess
	}
	r.reportMetrics(req, rsp)
	return rsp
}
