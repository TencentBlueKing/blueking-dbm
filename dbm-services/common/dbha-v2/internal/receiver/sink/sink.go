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

package sink

import (
	"context"
	"strings"
	"time"

	"dbm-services/common/dbha-v2/internal/receiver/config"
	"dbm-services/common/dbha-v2/pkg/constant"
	"dbm-services/common/dbha-v2/pkg/gerrors"
)

// Sinker Define the interface for storing data.
type Sinker interface {
	Save(ctx context.Context, msg *Message) error
	Close()
}

type Saver struct {
	Sinker      Sinker
	SaveTimeout time.Duration
}

// NewSinker create a new saver
func NewSinker(cfg config.SinkConfig) (Saver, error) {
	switch strings.ToLower(cfg.Name) {
	case strings.ToLower(mySQLName):
		mysql, err := newMySql(cfg.Endpoints, cfg.User, cfg.Password)
		if err != nil {
			return Saver{}, err
		}

		saveTimeout := cfg.SaveTimeout
		if saveTimeout <= 0 {
			saveTimeout = constant.DefaultSaveTimeout
		}

		return Saver{
			Sinker:      mysql,
			SaveTimeout: saveTimeout,
		}, nil

	default:
		return Saver{}, gerrors.Newf(gerrors.Unsupported, "unsupported storage(%s)", cfg.Name)
	}
}
