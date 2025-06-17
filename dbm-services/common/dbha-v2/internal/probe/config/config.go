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

package config

var Cfg Configuration

// LogConfig log configuration
type LogConfig struct {
	Path      string `yaml:"path"`
	Level     string `yaml:"level"`
	FileCount int    `yaml:"fileCount"`
	FileSize  int    `yaml:"fileSize"`
}

// AdminService admin service configuration
type AdminService struct {
	Endpoints    string `yaml:"endpoints"`
	SyncInterval int    `yaml:"syncInterval"`
}

// ReceiverService receiver service configuration
type ReceiverService struct {
	Endpoints    string `yaml:"endpoints"`
	SyncInterval int    `yaml:"syncInterval"`
}

// Configuration receiver's configuration
type Configuration struct {
	Name     string          `yaml:"name"`
	Version  string          `yaml:"version"`
	Receiver ReceiverService `yaml:"receiver"`
	Admin    AdminService    `yaml:"admin"`
	Log      LogConfig       `yaml:"log"`
}
